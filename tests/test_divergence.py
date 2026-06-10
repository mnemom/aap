"""Tests for DivergenceDetector — behavioral drift detection.

Tests the divergence detection module for monitoring sustained deviation
from baseline behavior using trace-to-trace centroid comparison.

The detector compares each trace against a baseline centroid computed from
the first N traces. Traces with the same features as the baseline yield
high similarity (no drift). Traces with different features yield low
similarity (drift detected).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from aap.verification.divergence import DivergenceDetector, detect_divergence
from aap.verification.models import DriftDirection


def _make_trace(
    trace_id: str,
    timestamp: str | None = None,
    action_name: str = "search",
    action_type: str = "recommend",
    category: str = "bounded",
    values_applied: list[str] | None = None,
    escalation_required: bool = False,
    escalation_evaluated: bool = True,
    confidence: float | None = None,
    agent_id: str = "agent-001",
) -> dict:
    """Helper to build a trace dict with sensible defaults."""
    trace: dict = {
        "trace_id": trace_id,
        "agent_id": agent_id,
        "action": {
            "type": action_type,
            "name": action_name,
            "category": category,
        },
        "decision": {
            "values_applied": values_applied or ["principal_benefit", "transparency"],
        },
        "escalation": {
            "evaluated": escalation_evaluated,
            "required": escalation_required,
        },
    }
    if timestamp is not None:
        trace["timestamp"] = timestamp
    if confidence is not None:
        trace["decision"]["confidence"] = confidence
    return trace


def _make_drift_trace(
    trace_id: str,
    timestamp: str | None = None,
    agent_id: str = "agent-001",
) -> dict:
    """Helper to build a maximally-divergent drift trace.

    Uses different action type, name, category, values, and escalation
    settings compared to the default baseline trace from _make_trace().
    """
    return _make_trace(
        trace_id,
        timestamp=timestamp,
        action_name="monetize",
        action_type="execute",
        category="forbidden",
        values_applied=["profit_maximization", "engagement"],
        escalation_required=True,
        escalation_evaluated=False,
        agent_id=agent_id,
    )


def _timestamps(n: int) -> list[str]:
    """Generate n chronologically-ordered ISO timestamps."""
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return [(base + timedelta(minutes=i)).isoformat() for i in range(n)]


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
        """Fewer traces than baseline + sustained threshold should return no alerts."""
        detector = DivergenceDetector(sustained_turns_threshold=3)
        card = {"card_id": "c1", "values": {"declared": ["v1"]}}
        # Only 2 traces; baseline_size >= 3 so baseline + sustained > 2
        traces = [
            _make_trace("t1", values_applied=["v2"]),
            _make_trace("t2", values_applied=["v2"]),
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
    def card(self):
        """Card used for card_id and direction inference."""
        return {
            "card_id": "card-001",
            "values": {"declared": ["principal_benefit", "transparency"]},
            "autonomy": {"bounded_actions": ["search", "recommend"]},
        }

    def test_consistent_traces_no_alert(self, card):
        """All traces with identical features should not trigger drift."""
        detector = DivergenceDetector(sustained_turns_threshold=3)
        ts = _timestamps(12)
        # 12 identical traces: baseline centroid == each trace => similarity ~1.0
        traces = [_make_trace(f"t{i}", timestamp=ts[i]) for i in range(12)]
        alerts = detector.detect(card, traces)
        assert alerts == []

    def test_behavioral_shift_triggers_alert(self, card):
        """Baseline of consistent traces then divergent traces should trigger alert."""
        detector = DivergenceDetector(sustained_turns_threshold=3)
        ts = _timestamps(12)

        # First 6 traces: consistent baseline behavior
        baseline_traces = [_make_trace(f"t{i}", timestamp=ts[i]) for i in range(6)]
        # Next 6 traces: completely different behavior
        drift_traces = [_make_drift_trace(f"t{i}", timestamp=ts[i]) for i in range(6, 12)]
        all_traces = baseline_traces + drift_traces
        alerts = detector.detect(card, all_traces)
        assert len(alerts) >= 1
        assert alerts[0].card_id == "card-001"

    def test_recovery_resets_streak(self, card):
        """A recovery trace (matching baseline) should reset the low-similarity streak."""
        detector = DivergenceDetector(sustained_turns_threshold=3)
        ts = _timestamps(12)

        # 6 baseline traces
        traces = [_make_trace(f"t{i}", timestamp=ts[i]) for i in range(6)]
        # 2 drifting traces
        traces.append(_make_drift_trace("d1", timestamp=ts[6]))
        traces.append(_make_drift_trace("d2", timestamp=ts[7]))
        # 1 recovery trace (same as baseline)
        traces.append(_make_trace("r1", timestamp=ts[8]))
        # 2 more drifting traces (not enough for sustained threshold of 3)
        traces.append(_make_drift_trace("d3", timestamp=ts[9]))
        traces.append(_make_drift_trace("d4", timestamp=ts[10]))

        alerts = detector.detect(card, traces)
        # Recovery at index 8 should reset streak; only 2 drift after that
        assert len(alerts) == 0

    def test_alert_contains_trace_ids(self, card):
        """Alert should contain IDs of traces in the streak."""
        detector = DivergenceDetector(sustained_turns_threshold=3)
        ts = _timestamps(12)

        traces = [_make_trace(f"t{i}", timestamp=ts[i]) for i in range(6)]
        for i in range(6, 12):
            traces.append(_make_drift_trace(f"drift-{i}", timestamp=ts[i]))
        alerts = detector.detect(card, traces)
        assert len(alerts) >= 1
        assert len(alerts[0].trace_ids) == 3

    def test_traces_sorted_regardless_of_input_order(self, card):
        """Traces should be sorted chronologically internally."""
        detector = DivergenceDetector(sustained_turns_threshold=3)
        ts = _timestamps(12)

        # Build traces in chronological order
        traces = [_make_trace(f"t{i}", timestamp=ts[i]) for i in range(6)]
        for i in range(6, 12):
            traces.append(_make_drift_trace(f"drift-{i}", timestamp=ts[i]))

        # Shuffle the order
        import random

        shuffled = traces.copy()
        random.seed(42)
        random.shuffle(shuffled)

        alerts_ordered = detector.detect(card, traces)
        alerts_shuffled = detector.detect(card, shuffled)

        assert len(alerts_ordered) == len(alerts_shuffled)

    def test_consistent_sparse_traces_no_drift(self, card):
        """Sparse traces that are all identical should not trigger drift."""
        detector = DivergenceDetector(sustained_turns_threshold=3)
        ts = _timestamps(12)

        # All traces have minimal / identical sparse features
        traces = [
            _make_trace(f"t{i}", timestamp=ts[i], values_applied=["principal_benefit"])
            for i in range(12)
        ]
        alerts = detector.detect(card, traces)
        assert alerts == []


class TestSimilarityHistory:
    """Tests for similarity history computation."""

    def test_history_length_matches_traces(self):
        """History should have one entry per trace."""
        detector = DivergenceDetector()
        card = {"card_id": "c1", "values": {"declared": ["v1"]}}
        traces = [{"trace_id": f"t{i}", "decision": {"values_applied": ["v1"]}} for i in range(5)]
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
        for entry in history:
            expected_below = entry["similarity"] < detector.similarity_threshold
            assert entry["below_threshold"] == expected_below


class TestDriftDirection:
    """Tests for drift direction inference."""

    def test_value_drift_direction(self):
        """Using undeclared values in drifting traces should suggest VALUE_DRIFT."""
        detector = DivergenceDetector(sustained_turns_threshold=3)
        card = {
            "card_id": "c1",
            "values": {"declared": ["principal_benefit"]},
        }
        ts = _timestamps(12)
        # Baseline: uses principal_benefit
        traces = [
            _make_trace(f"t{i}", timestamp=ts[i], values_applied=["principal_benefit"])
            for i in range(6)
        ]
        # Drift: uses undeclared values with maximally different features
        for i in range(6, 12):
            traces.append(_make_drift_trace(f"t{i}", timestamp=ts[i]))
        alerts = detector.detect(card, traces)
        if alerts:
            assert alerts[0].analysis.drift_direction in [
                DriftDirection.VALUE_DRIFT,
                DriftDirection.UNKNOWN,
            ]

    def test_unknown_direction_when_pattern_unclear(self):
        """Unknown direction when no clear pattern detected."""
        detector = DivergenceDetector(sustained_turns_threshold=3)
        card = {"card_id": "c1", "values": {"declared": []}}
        ts = _timestamps(12)
        # Baseline: some features
        traces = [_make_trace(f"t{i}", timestamp=ts[i], values_applied=[]) for i in range(6)]
        # Drift: different action but same empty values
        for i in range(6, 12):
            traces.append(
                _make_trace(
                    f"t{i}",
                    timestamp=ts[i],
                    action_name="export",
                    action_type="execute",
                    category="forbidden",
                    values_applied=[],
                    escalation_required=True,
                    escalation_evaluated=False,
                )
            )
        alerts = detector.detect(card, traces)
        if alerts:
            assert alerts[0].analysis.drift_direction == DriftDirection.UNKNOWN


class TestDriftIndicators:
    """Tests for drift indicator generation."""

    def test_indicators_list_populated(self):
        """Alerts should have indicators explaining the drift."""
        detector = DivergenceDetector(sustained_turns_threshold=3)
        card = {"card_id": "c1", "values": {"declared": ["v1"]}}
        ts = _timestamps(12)
        traces = [_make_trace(f"t{i}", timestamp=ts[i], values_applied=["v1"]) for i in range(6)]
        for i in range(6, 12):
            traces.append(_make_drift_trace(f"t{i}", timestamp=ts[i]))
        alerts = detector.detect(card, traces)
        if alerts:
            indicators = alerts[0].analysis.specific_indicators
            assert isinstance(indicators, list)


class TestDetectDivergenceFunction:
    """Tests for the convenience function."""

    def test_function_works_same_as_class(self):
        """detect_divergence function should work same as class method."""
        card = {"card_id": "c1", "values": {"declared": ["v1"]}}
        ts = _timestamps(12)
        traces = [_make_trace(f"t{i}", timestamp=ts[i], values_applied=["v1"]) for i in range(6)]
        for i in range(6, 12):
            traces.append(_make_drift_trace(f"t{i}", timestamp=ts[i]))
        alerts_func = detect_divergence(card, traces)
        detector = DivergenceDetector()
        alerts_class = detector.detect(card, traces)
        assert len(alerts_func) == len(alerts_class)

    def test_function_accepts_custom_thresholds(self):
        """Function should accept custom threshold parameters."""
        card = {"card_id": "c1"}
        ts = _timestamps(10)
        traces = [_make_trace(f"t{i}", timestamp=ts[i]) for i in range(10)]
        # With high sustained threshold, no alerts
        alerts = detect_divergence(
            card,
            traces,
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
        ts = _timestamps(12)
        traces = [_make_trace(f"t{i}", timestamp=ts[i], values_applied=["v1"]) for i in range(12)]
        # Should not raise
        alerts = detector.detect(card, traces)
        assert isinstance(alerts, list)

    def test_alert_generation_only_once_at_threshold(self):
        """Alert should be generated once when threshold reached, not on every subsequent trace."""
        detector = DivergenceDetector(sustained_turns_threshold=3)
        card = {"card_id": "c1", "values": {"declared": ["v1"]}}
        ts = _timestamps(16)
        # 6 baseline traces
        traces = [_make_trace(f"t{i}", timestamp=ts[i], values_applied=["v1"]) for i in range(6)]
        # 10 drifting traces (maximally divergent)
        for i in range(6, 16):
            traces.append(_make_drift_trace(f"t{i}", timestamp=ts[i]))
        alerts = detector.detect(card, traces)
        # Should only generate one alert (when threshold first reached)
        assert len(alerts) == 1
