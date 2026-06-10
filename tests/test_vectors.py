"""Tests using test vectors — machine-readable reference cases.

These tests load the JSON test vectors and verify that the AAP SDK
produces expected results. Test vectors serve as:
1. Regression tests — changes that break vectors need justification
2. Documentation — vectors show exactly what pass/fail looks like
3. Interoperability — other implementations can use the same vectors

Design principles:
- One test per vector file
- Clear pass/fail based on _expected_result field
- Vectors are authoritative — if behavior differs, investigate why
"""

from __future__ import annotations

import json
from datetime import timezone
from pathlib import Path
from typing import Any

import pytest

from aap import detect_drift, verify_trace
from aap.verification.features import FeatureExtractor, cosine_similarity
from aap.verification.models import ViolationType

VECTORS_DIR = Path(__file__).parent / "vectors"


def load_vector(path: Path) -> dict[str, Any]:
    """Load a test vector JSON file."""
    with open(path) as f:
        return json.load(f)


# ===========================================================================
# Valid Trace Vectors
# ===========================================================================


class TestValidTraceVectors:
    """Tests using valid trace vectors — all should pass verification."""

    @pytest.fixture
    def valid_traces_dir(self) -> Path:
        return VECTORS_DIR / "valid_traces"

    def test_compliant_recommendation(self, valid_traces_dir: Path):
        """Compliant recommendation should pass verification."""
        vector = load_vector(valid_traces_dir / "compliant_recommendation.json")

        result = verify_trace(vector["trace"], vector["card"])

        expected = vector["_expected_result"]
        assert result.verified is expected["verified"]
        assert len(result.violations) == len(expected["violations"])
        assert len(result.warnings) == len(expected["warnings"])

    def test_approved_escalation(self, valid_traces_dir: Path):
        """Properly escalated and approved trace should pass."""
        vector = load_vector(valid_traces_dir / "approved_escalation.json")

        result = verify_trace(vector["trace"], vector["card"])

        expected = vector["_expected_result"]
        assert result.verified is expected["verified"]
        assert len(result.violations) == 0


# ===========================================================================
# Invalid Trace Vectors
# ===========================================================================


class TestInvalidTraceVectors:
    """Tests using invalid trace vectors — all should fail verification."""

    @pytest.fixture
    def invalid_traces_dir(self) -> Path:
        return VECTORS_DIR / "invalid_traces"

    def test_forbidden_action(self, invalid_traces_dir: Path):
        """Forbidden action should fail with CRITICAL violation."""
        vector = load_vector(invalid_traces_dir / "forbidden_action.json")

        result = verify_trace(vector["trace"], vector["card"])

        expected = vector["_expected_result"]
        assert result.verified is False

        # Check for expected violation type
        violation_types = [v.type for v in result.violations]
        assert ViolationType.FORBIDDEN_ACTION in violation_types

        # Check description contains expected text
        forbidden_violations = [
            v for v in result.violations if v.type == ViolationType.FORBIDDEN_ACTION
        ]
        assert any(
            expected["violations"][0]["description_contains"] in v.description
            for v in forbidden_violations
        )

    def test_undeclared_value(self, invalid_traces_dir: Path):
        """Undeclared value should fail with MEDIUM violation."""
        vector = load_vector(invalid_traces_dir / "undeclared_value.json")

        result = verify_trace(vector["trace"], vector["card"])

        assert result.verified is False

        # Check for expected violation type
        violation_types = [v.type for v in result.violations]
        assert ViolationType.UNDECLARED_VALUE in violation_types

    def test_missed_escalation(self, invalid_traces_dir: Path):
        """Missed escalation should fail with HIGH violation."""
        vector = load_vector(invalid_traces_dir / "missed_escalation.json")

        result = verify_trace(vector["trace"], vector["card"])

        # Should fail verification
        assert result.verified is False

        # Should have missed escalation violation
        violation_types = [v.type for v in result.violations]
        assert ViolationType.MISSED_ESCALATION in violation_types


# ===========================================================================
# Drift Case Vectors
# ===========================================================================


class TestDriftCaseVectors:
    """Tests using drift case vectors — sequences that should trigger alerts."""

    @pytest.fixture
    def drift_cases_dir(self) -> Path:
        return VECTORS_DIR / "drift_cases"

    def test_value_drift_sequence(self, drift_cases_dir: Path):
        """Value drift sequence should trigger drift alert."""
        vector = load_vector(drift_cases_dir / "value_drift_sequence.json")

        alerts = detect_drift(vector["card"], vector["traces"])

        expected = vector["_expected_result"]
        assert expected["drift_detected"] is True
        assert len(alerts) >= 1

        # Check that drift was detected
        # The exact alert index may vary based on thresholds
        assert any(
            alert.analysis.drift_direction.value in ["value_drift", "unknown"] for alert in alerts
        )

    def test_autonomy_expansion_sequence(self, drift_cases_dir: Path):
        """Autonomy expansion sequence should trigger drift alert."""
        vector = load_vector(drift_cases_dir / "autonomy_expansion_sequence.json")

        alerts = detect_drift(vector["card"], vector["traces"])

        expected = vector["_expected_result"]
        assert expected["drift_detected"] is True
        assert len(alerts) >= 1

        # Check that drift was detected with appropriate direction
        directions = [alert.analysis.drift_direction.value for alert in alerts]
        assert any(d in ["autonomy_expansion", "value_drift", "unknown"] for d in directions)


# ===========================================================================
# Vector Discovery Tests
# ===========================================================================


class TestVectorDiscovery:
    """Tests to ensure all vectors are valid and loadable."""

    def test_all_valid_traces_loadable(self):
        """All valid trace vectors should be loadable."""
        valid_dir = VECTORS_DIR / "valid_traces"
        if valid_dir.exists():
            for path in valid_dir.glob("*.json"):
                vector = load_vector(path)
                assert "card" in vector
                assert "trace" in vector
                assert "_expected_result" in vector

    def test_all_invalid_traces_loadable(self):
        """All invalid trace vectors should be loadable."""
        invalid_dir = VECTORS_DIR / "invalid_traces"
        if invalid_dir.exists():
            for path in invalid_dir.glob("*.json"):
                vector = load_vector(path)
                assert "card" in vector
                assert "trace" in vector
                assert "_expected_result" in vector

    def test_all_drift_cases_loadable(self):
        """All drift case vectors should be loadable."""
        drift_dir = VECTORS_DIR / "drift_cases"
        if drift_dir.exists():
            for path in drift_dir.glob("*.json"):
                vector = load_vector(path)
                assert "card" in vector
                assert "traces" in vector
                assert "_expected_result" in vector


# ===========================================================================
# Golden Parity Tests (Python↔TS cross-language conformance)
# ===========================================================================


class TestGoldenParitySDK:
    """Verify that the Python SDK produces results consistent with the TypeScript SDK.

    Both SDKs must:
    - Agree on the verify_trace result schema (same fields present)
    - Produce the same similarity_score for identical inputs (deterministic)
    - Produce UTC-aware timestamps
    - Not include flag:* features in trace feature vectors
    - Detect the same drift events on shared drift sequences
    """

    def test_verify_trace_similarity_score_present_and_bounded(self):
        """verify_trace must return a similarity_score in [0, 1]."""
        vector = load_vector(VECTORS_DIR / "valid_traces" / "compliant_recommendation.json")
        result = verify_trace(vector["trace"], vector["card"])

        assert hasattr(result, "similarity_score")
        assert 0.0 <= result.similarity_score <= 1.0

    def test_verify_trace_similarity_score_matches_cosine(self):
        """verify_trace similarity_score must equal cosine(trace_features, card_features).

        Both Python and TypeScript SDKs now use the same formula, so the score
        must be deterministic and identical across languages for the same input.
        """
        vector = load_vector(VECTORS_DIR / "valid_traces" / "compliant_recommendation.json")

        extractor = FeatureExtractor()
        trace_vec = extractor.extract_trace_features(vector["trace"])
        card_vec = extractor.extract_card_features(vector["card"])
        expected = round(cosine_similarity(trace_vec, card_vec), 4)

        result = verify_trace(vector["trace"], vector["card"])
        assert result.similarity_score == expected

    def test_verify_trace_similarity_score_matches_fixture(self):
        """verify_trace similarity_score must equal the language-independent fixture constant.

        Both Python and TypeScript assert against this same stored value (AC3),
        so any cross-language extractor divergence becomes CI-visible.
        """
        vector = load_vector(VECTORS_DIR / "valid_traces" / "compliant_recommendation.json")
        expected = vector["_expected_result"]["expected_similarity_score"]
        result = verify_trace(vector["trace"], vector["card"])
        assert abs(result.similarity_score - expected) <= 1e-9, (
            f"similarity_score {result.similarity_score} != fixture expected {expected}"
        )

    @pytest.mark.parametrize(
        "fixture_path",
        [
            "valid_traces/compliant_recommendation.json",
            "valid_traces/approved_escalation.json",
            "invalid_traces/forbidden_action.json",
            "invalid_traces/missed_escalation.json",
            "invalid_traces/undeclared_value.json",
        ],
    )
    def test_all_fixtures_similarity_score_matches_stored(self, fixture_path: str):
        """Every fixture with expected_similarity_score must match in both SDKs (AC3 full coverage).

        Any cross-language extractor divergence on any fixture becomes CI-visible.
        """
        vector = load_vector(VECTORS_DIR / fixture_path)
        stored = vector.get("_expected_result", {}).get("expected_similarity_score")
        if stored is None:
            pytest.skip(f"{fixture_path} has no expected_similarity_score")
        result = verify_trace(vector["trace"], vector["card"])
        assert abs(result.similarity_score - stored) <= 1e-9, (
            f"{fixture_path}: similarity_score {result.similarity_score} != stored {stored}"
        )

    def test_verify_trace_timestamp_is_utc_aware(self):
        """verify_trace timestamp must be timezone-aware UTC."""
        vector = load_vector(VECTORS_DIR / "valid_traces" / "compliant_recommendation.json")
        result = verify_trace(vector["trace"], vector["card"])

        assert result.timestamp.tzinfo is not None
        assert (
            result.timestamp.tzinfo == timezone.utc
            or result.timestamp.utcoffset().total_seconds() == 0
        )

    def test_verify_trace_behavioral_similarity_in_checks(self):
        """behavioral_similarity must appear in checks_performed."""
        vector = load_vector(VECTORS_DIR / "valid_traces" / "compliant_recommendation.json")
        result = verify_trace(vector["trace"], vector["card"])

        assert "behavioral_similarity" in result.verification_metadata.checks_performed

    def test_verify_trace_low_behavioral_similarity_warning(self):
        """Compliant trace should still emit low_behavioral_similarity warning (fixture-documented)."""
        vector = load_vector(VECTORS_DIR / "valid_traces" / "compliant_recommendation.json")
        result = verify_trace(vector["trace"], vector["card"])

        # The fixture documents this warning is expected for structurally-valid traces
        # because trace-to-card cosine similarity is depressed by asymmetric feature spaces.
        assert result.verified is True
        warning_types = [w.type for w in result.warnings]
        assert "low_behavioral_similarity" in warning_types

    def test_verify_trace_recommended_action_present_and_correct(self):
        """verify_trace must return recommended_action matching violations/warnings state."""
        vector = load_vector(VECTORS_DIR / "valid_traces" / "compliant_recommendation.json")
        result = verify_trace(vector["trace"], vector["card"])

        assert hasattr(result, "recommended_action")
        assert result.recommended_action in ("proceed", "review", "deny")
        if result.violations:
            assert result.recommended_action == "deny"
        elif result.warnings:
            assert result.recommended_action == "review"
        else:
            assert result.recommended_action == "proceed"

    def test_feature_extractor_no_flag_features(self):
        """Python trace feature extractor must not produce flag:* features.

        The compliant_recommendation trace has flags on one alternative. This test
        asserts Python's extractor ignores them, matching the TS SDK's revised behavior.
        """
        vector = load_vector(VECTORS_DIR / "valid_traces" / "compliant_recommendation.json")

        extractor = FeatureExtractor()
        features = extractor.extract_trace_features(vector["trace"])

        flag_keys = [k for k in features if k.startswith("flag:")]
        assert flag_keys == [], f"Unexpected flag features: {flag_keys}"

    def test_detect_drift_scores_are_bounded(self):
        """detect_drift similarity scores must be in [0, 1] (value_drift sequence)."""
        vector = load_vector(VECTORS_DIR / "drift_cases" / "value_drift_sequence.json")
        alerts = detect_drift(vector["card"], vector["traces"])

        assert len(alerts) >= 1
        for alert in alerts:
            assert 0.0 <= alert.analysis.similarity_score <= 1.0

    def test_detect_drift_similarity_score_parity(self):
        """detect_drift alert similarity_score must match first-principles cosine (AC3).

        Replicates DivergenceDetector's baseline computation so any extractor
        regression is caught before it can cause threshold-straddling divergence
        between Python and TS.
        """
        from aap.verification.constants import (
            DEFAULT_SIMILARITY_THRESHOLD,
            DEFAULT_SUSTAINED_TURNS_THRESHOLD,
        )
        from aap.verification.features import compute_centroid

        vector = load_vector(VECTORS_DIR / "drift_cases" / "value_drift_sequence.json")
        traces = sorted(vector["traces"], key=lambda t: t.get("timestamp", ""))
        n = len(traces)
        s = DEFAULT_SUSTAINED_TURNS_THRESHOLD
        baseline_size = max(s, min(10, n // 4))

        extractor = FeatureExtractor()
        centroid = compute_centroid(
            [extractor.extract_trace_features(t) for t in traces[:baseline_size]]
        )

        streak, expected_score = [], None
        for trace in traces[baseline_size:]:
            sim = cosine_similarity(extractor.extract_trace_features(trace), centroid)
            if sim < DEFAULT_SIMILARITY_THRESHOLD:
                streak.append(sim)
                if len(streak) == s:
                    expected_score = round(sim, 4)
                    break
            else:
                streak = []

        assert expected_score is not None, "Fixture produced no alert-triggering trace"

        # detect_drift must produce the same score (exact — same extractor, same formula)
        alerts = detect_drift(vector["card"], vector["traces"])
        assert len(alerts) >= 1
        assert alerts[0].analysis.similarity_score == expected_score

        # Cross-language fixture constant must also match within ±0.005
        fixture_expected = vector["_expected_result"].get("expected_alert_similarity_score")
        assert fixture_expected is not None, (
            "expected_alert_similarity_score missing from fixture _expected_result"
        )
        assert abs(expected_score - fixture_expected) <= 0.005, (
            f"Python computed {expected_score} but fixture records {fixture_expected}; "
            "update fixture constant or fix extractor parity"
        )

    def test_detect_drift_timestamp_is_utc_aware(self):
        """DriftAlert.detection_timestamp must be timezone-aware UTC."""
        vector = load_vector(VECTORS_DIR / "drift_cases" / "value_drift_sequence.json")
        alerts = detect_drift(vector["card"], vector["traces"])

        for alert in alerts:
            assert alert.detection_timestamp.tzinfo is not None


# ===========================================================================
# Vector Schema Validation
# ===========================================================================


class TestVectorSchemaValidation:
    """Tests that vectors conform to AAP schemas."""

    def test_valid_trace_cards_validate(self):
        """Cards in valid trace vectors should validate against schema."""
        from aap import AlignmentCard

        valid_dir = VECTORS_DIR / "valid_traces"
        if valid_dir.exists():
            for path in valid_dir.glob("*.json"):
                vector = load_vector(path)
                # Should not raise
                card = AlignmentCard.model_validate(vector["card"])
                assert card.card_id is not None

    def test_valid_trace_traces_validate(self):
        """Traces in valid trace vectors should validate against schema."""
        from aap import APTrace

        valid_dir = VECTORS_DIR / "valid_traces"
        if valid_dir.exists():
            for path in valid_dir.glob("*.json"):
                vector = load_vector(path)
                # Should not raise
                trace = APTrace.model_validate(vector["trace"])
                assert trace.trace_id is not None
