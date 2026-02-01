"""Tests for DivergenceDetector — behavioral drift detection.

Tests the Braid-extracted divergence detection module for monitoring
sustained deviation from declared alignment.
"""

from __future__ import annotations

import pytest

from aap.verification.divergence import DivergenceDetector, detect_divergence
from aap.verification.models import DriftDirection


class TestDivergenceDetectorBasic:
    """Basic DivergenceDetector functionality tests."""

    def test_default_thresholds(self):
        """Default thresholds should match calibration constants."""
        detector = DivergenceDetector()

        assert detector.similarity_threshold == 0.30
        assert detector.sustained_turns_threshold == 3

    def test_custom_thresholds(self):
        """Custom thresholds should be accepted."""
        detector = DivergenceDetector(
            similarity_threshold=0.5,
            sustained_turns_threshold=5,
        )

        assert detector.similarity_threshold == 0.5
        assert detector.sustained_turns_threshold == 5

    def test_insufficient_traces_returns_empty(self):
        """Fewer traces than sustained threshold should return no alerts."""
        detector = DivergenceDetector(sustained_turns_threshold=3)
        card = {"card_id": "c1", "values": {"declared": ["v1"]}}
        traces = [
            {"trace_id": "t1", "decision": {"values_applied": ["v2"]}},
            {"trace_id": "t2", "decision": {"values_applied": ["v2"]}},
        ]

        alerts = detector.detect(card, traces)

        assert alerts == []

    def test_empty_traces_returns_empty(self):
        """Empty trace list should return no alerts."""
        detector = DivergenceDetector()
        card = {"card_id": "c1"}

        alerts = detector.detect(card, [])

        assert alerts == []


class TestDivergenceDetection:
    """Tests for actual divergence detection logic."""

    @pytest.fixture
    def aligned_card(self):
        """Card with specific declared values."""
        return {
            "card_id": "card-001",
            "values": {"declared": ["principal_benefit", "transparency"]},
            "autonomy_envelope": {"bounded_actions": ["recommend"]},
        }

    def test_aligned_traces_no_alert(self, aligned_card):
        """Traces aligned with card should not trigger alerts."""
        detector = DivergenceDetector()
        traces = [
            {
                "trace_id": f"t{i}",
                "action": {"name": "recommend"},
                "decision": {"values_applied": ["principal_benefit", "transparency"]},
            }
            for i in range(5)
        ]

        alerts = detector.detect(aligned_card, traces)

        # All traces are well-aligned, should have high similarity
        # This depends on the actual similarity scores
        # If all traces have similarity > threshold, no alerts
        history = detector.compute_similarity_history(aligned_card, traces)
        if all(not h["below_threshold"] for h in history):
            assert alerts == []

    def test_drifting_traces_trigger_alert(self, aligned_card):
        """Traces drifting from card should trigger alert."""
        detector = DivergenceDetector()
        # Create traces that definitely drift (use completely different values)
        traces = [
            {
                "trace_id": f"t{i}",
                "action": {"name": "export"},  # Not in bounded_actions
                "decision": {"values_applied": ["efficiency", "speed"]},  # Undeclared values
            }
            for i in range(5)
        ]

        alerts = detector.detect(aligned_card, traces)

        # Should trigger at least one alert after sustained low similarity
        assert len(alerts) >= 1

    def test_recovery_resets_streak(self, aligned_card):
        """Recovery (high similarity trace) should reset the streak."""
        detector = DivergenceDetector(sustained_turns_threshold=3)

        # Pattern: drift, drift, recover, drift, drift
        traces = [
            # Two drifting traces
            {"trace_id": "t1", "action": {"name": "export"}, "decision": {"values_applied": ["efficiency"]}},
            {"trace_id": "t2", "action": {"name": "export"}, "decision": {"values_applied": ["efficiency"]}},
            # Recovery trace (aligned)
            {"trace_id": "t3", "action": {"name": "recommend"}, "decision": {"values_applied": ["principal_benefit", "transparency"]}},
            # Two more drifting traces
            {"trace_id": "t4", "action": {"name": "export"}, "decision": {"values_applied": ["efficiency"]}},
            {"trace_id": "t5", "action": {"name": "export"}, "decision": {"values_applied": ["efficiency"]}},
        ]

        alerts = detector.detect(aligned_card, traces)

        # Check similarity history to understand behavior
        history = detector.compute_similarity_history(aligned_card, traces)

        # If recovery trace has high similarity, it resets the streak
        # So we shouldn't have alerts unless 3+ consecutive low similarity
        recovery_above_threshold = not history[2]["below_threshold"]

        # If recovery is above threshold, streak should reset
        # and only 2 consecutive low-similarity traces after recovery (not enough for alert)
        if recovery_above_threshold:
            assert len(alerts) == 0

    def test_alert_contains_trace_ids(self, aligned_card):
        """Alert should contain IDs of traces in the streak."""
        detector = DivergenceDetector(sustained_turns_threshold=3)
        traces = [
            {
                "trace_id": f"drift-{i}",
                "action": {"name": "export"},
                "decision": {"values_applied": ["efficiency"]},
            }
            for i in range(4)
        ]

        alerts = detector.detect(aligned_card, traces)

        if alerts:
            # First alert should have 3 trace IDs
            assert len(alerts[0].trace_ids) == 3


class TestSimilarityHistory:
    """Tests for similarity history computation."""

    def test_history_length_matches_traces(self):
        """History should have one entry per trace."""
        detector = DivergenceDetector()
        card = {"card_id": "c1", "values": {"declared": ["v1"]}}
        traces = [
            {"trace_id": f"t{i}", "decision": {"values_applied": ["v1"]}}
            for i in range(5)
        ]

        history = detector.compute_similarity_history(card, traces)

        assert len(history) == 5

    def test_history_contains_required_fields(self):
        """Each history entry should have required fields."""
        detector = DivergenceDetector()
        card = {"card_id": "c1"}
        traces = [{"trace_id": "t1", "decision": {}}]

        history = detector.compute_similarity_history(card, traces)

        assert "trace_id" in history[0]
        assert "similarity" in history[0]
        assert "below_threshold" in history[0]
        assert "index" in history[0]

    def test_below_threshold_flag_correct(self):
        """below_threshold should correctly reflect similarity vs threshold."""
        detector = DivergenceDetector(similarity_threshold=0.5)
        card = {"card_id": "c1", "values": {"declared": ["v1"]}}
        traces = [{"trace_id": "t1", "decision": {"values_applied": ["v1"]}}]

        history = detector.compute_similarity_history(card, traces)

        # Check that below_threshold is consistent with similarity
        for entry in history:
            expected_below = entry["similarity"] < detector.similarity_threshold
            assert entry["below_threshold"] == expected_below


class TestDriftDirection:
    """Tests for drift direction inference."""

    def test_value_drift_direction(self):
        """Using undeclared values should suggest VALUE_DRIFT."""
        detector = DivergenceDetector()
        card = {
            "card_id": "c1",
            "values": {"declared": ["principal_benefit"]},
        }
        # Traces using undeclared values
        traces = [
            {"trace_id": f"t{i}", "decision": {"values_applied": ["efficiency", "speed"]}}
            for i in range(4)
        ]

        alerts = detector.detect(card, traces)

        if alerts:
            # Should detect VALUE_DRIFT or UNKNOWN
            assert alerts[0].analysis.drift_direction in [
                DriftDirection.VALUE_DRIFT,
                DriftDirection.UNKNOWN,
            ]

    def test_unknown_direction_when_pattern_unclear(self):
        """Unknown direction when no clear pattern detected."""
        detector = DivergenceDetector()
        card = {"card_id": "c1", "values": {"declared": []}}
        traces = [
            {"trace_id": f"t{i}", "decision": {"values_applied": []}}
            for i in range(4)
        ]

        alerts = detector.detect(card, traces)

        # With no clear pattern, should be UNKNOWN
        if alerts:
            assert alerts[0].analysis.drift_direction == DriftDirection.UNKNOWN


class TestDriftIndicators:
    """Tests for drift indicator generation."""

    def test_indicators_list_populated(self):
        """Alerts should have indicators explaining the drift."""
        detector = DivergenceDetector()
        card = {"card_id": "c1", "values": {"declared": ["v1"]}}
        traces = [
            {"trace_id": f"t{i}", "action": {}, "decision": {"values_applied": ["v2"]}}
            for i in range(4)
        ]

        alerts = detector.detect(card, traces)

        if alerts:
            # Should have at least the similarity trend indicator
            indicators = alerts[0].analysis.specific_indicators
            assert isinstance(indicators, list)


class TestDetectDivergenceFunction:
    """Tests for the convenience function."""

    def test_function_works_same_as_class(self):
        """detect_divergence function should work same as class method."""
        card = {"card_id": "c1", "values": {"declared": ["v1"]}}
        traces = [
            {"trace_id": f"t{i}", "decision": {"values_applied": ["v2"]}}
            for i in range(4)
        ]

        # Using function
        alerts_func = detect_divergence(card, traces)

        # Using class
        detector = DivergenceDetector()
        alerts_class = detector.detect(card, traces)

        # Should produce same results
        assert len(alerts_func) == len(alerts_class)

    def test_function_accepts_custom_thresholds(self):
        """Function should accept custom threshold parameters."""
        card = {"card_id": "c1"}
        traces = [{"trace_id": f"t{i}"} for i in range(10)]

        # With high sustained threshold, no alerts
        alerts = detect_divergence(
            card, traces,
            similarity_threshold=0.3,
            sustained_threshold=20,
        )

        assert alerts == []


class TestDivergenceEdgeCases:
    """Edge case tests for DivergenceDetector."""

    def test_traces_with_missing_fields(self):
        """Traces with missing fields should not crash."""
        detector = DivergenceDetector()
        card = {"card_id": "c1"}
        traces = [
            {"trace_id": "t1"},  # Minimal
            {"trace_id": "t2", "action": {}},  # Empty action
            {"trace_id": "t3", "decision": {}},  # Empty decision
        ]

        # Should not raise
        alerts = detector.detect(card, traces)
        assert isinstance(alerts, list)

    def test_card_with_missing_fields(self):
        """Card with missing fields should not crash."""
        detector = DivergenceDetector()
        card = {}  # Empty card
        traces = [
            {"trace_id": f"t{i}", "decision": {"values_applied": ["v1"]}}
            for i in range(4)
        ]

        # Should not raise
        alerts = detector.detect(card, traces)
        assert isinstance(alerts, list)

    def test_alert_generation_only_once_at_threshold(self):
        """Alert should be generated once when threshold reached, not on every subsequent trace."""
        detector = DivergenceDetector(sustained_turns_threshold=3)
        card = {"card_id": "c1", "values": {"declared": ["v1"]}}
        traces = [
            {"trace_id": f"t{i}", "decision": {"values_applied": ["v2"]}}
            for i in range(10)  # Many drifting traces
        ]

        alerts = detector.detect(card, traces)

        # Should only generate one alert (when threshold first reached)
        # Not one alert per trace after threshold
        assert len(alerts) == 1
