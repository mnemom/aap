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
from pathlib import Path
from typing import Any

import pytest

from aap import detect_drift, verify_trace
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
            v for v in result.violations
            if v.type == ViolationType.FORBIDDEN_ACTION
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
            alert.analysis.drift_direction.value in ["value_drift", "unknown"]
            for alert in alerts
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
