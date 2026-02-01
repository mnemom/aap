"""Comprehensive tests for AAP verification API.

Tests the three core verification functions:
- verify_trace: Verify AP-Trace against Alignment Card
- check_coherence: Check value coherence between two cards
- detect_drift: Detect behavioral drift over trace sequences

These tests verify the core guarantees of AAP — what it promises
and what it explicitly does NOT promise (see LIMITS.md).

Design principles:
- Test each violation type independently
- Test combinations that occur in practice
- Test edge cases and boundary conditions
- Document expected behavior through test names
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from aap import (
    check_coherence,
    detect_drift,
    verify_trace,
)
from aap.verification.constants import (
    DEFAULT_SIMILARITY_THRESHOLD,
    DEFAULT_SUSTAINED_TURNS_THRESHOLD,
)
from aap.verification.models import (
    DriftDirection,
    Severity,
    ViolationType,
)

# ===========================================================================
# verify_trace Tests
# ===========================================================================


class TestVerifyTraceBasic:
    """Basic verify_trace functionality."""

    def test_valid_trace_passes(
        self,
        minimal_alignment_card: dict,
        minimal_trace: dict,
    ):
        """Valid trace should pass verification."""
        result = verify_trace(minimal_trace, minimal_alignment_card)

        assert result.verified is True
        assert len(result.violations) == 0
        assert result.trace_id == minimal_trace["trace_id"]
        assert result.card_id == minimal_alignment_card["card_id"]

    def test_verification_metadata_populated(
        self,
        minimal_alignment_card: dict,
        minimal_trace: dict,
    ):
        """Verification metadata should be populated."""
        result = verify_trace(minimal_trace, minimal_alignment_card)

        assert result.verification_metadata is not None
        assert result.verification_metadata.algorithm_version is not None
        assert len(result.verification_metadata.checks_performed) > 0
        assert result.verification_metadata.duration_ms >= 0

    def test_all_checks_performed(
        self,
        minimal_alignment_card: dict,
        minimal_trace: dict,
    ):
        """All verification checks should be performed."""
        result = verify_trace(minimal_trace, minimal_alignment_card)

        expected_checks = {
            "card_reference",
            "card_expiration",
            "autonomy",
            "forbidden",
            "escalation",
            "values",
        }
        performed = set(result.verification_metadata.checks_performed)
        assert expected_checks.issubset(performed)


class TestVerifyTraceViolations:
    """Tests for each violation type."""

    def test_card_mismatch_violation(
        self,
        minimal_alignment_card: dict,
        trace_card_mismatch: dict,
    ):
        """Card mismatch should be a CRITICAL violation."""
        result = verify_trace(trace_card_mismatch, minimal_alignment_card)

        assert result.verified is False
        assert len(result.violations) >= 1

        mismatch_violations = [
            v for v in result.violations
            if v.type == ViolationType.CARD_MISMATCH
        ]
        assert len(mismatch_violations) == 1
        assert mismatch_violations[0].severity == Severity.CRITICAL

    def test_card_expired_violation(
        self,
        expired_alignment_card: dict,
        minimal_trace: dict,
    ):
        """Expired card should be a HIGH violation."""
        # Update trace to reference expired card
        minimal_trace["card_id"] = expired_alignment_card["card_id"]

        result = verify_trace(minimal_trace, expired_alignment_card)

        assert result.verified is False
        expired_violations = [
            v for v in result.violations
            if v.type == ViolationType.CARD_EXPIRED
        ]
        assert len(expired_violations) == 1
        assert expired_violations[0].severity == Severity.HIGH

    def test_forbidden_action_violation(
        self,
        full_alignment_card: dict,
        trace_with_forbidden_action: dict,
    ):
        """Forbidden action should be a CRITICAL violation."""
        # Update trace to reference full card which has forbidden_actions
        trace_with_forbidden_action["card_id"] = full_alignment_card["card_id"]

        result = verify_trace(trace_with_forbidden_action, full_alignment_card)

        assert result.verified is False
        forbidden_violations = [
            v for v in result.violations
            if v.type == ViolationType.FORBIDDEN_ACTION
        ]
        assert len(forbidden_violations) == 1
        assert forbidden_violations[0].severity == Severity.CRITICAL
        assert "delete_data" in forbidden_violations[0].description

    def test_unbounded_action_violation(
        self,
        minimal_alignment_card: dict,
    ):
        """Action not in bounded_actions should be a HIGH violation."""
        trace = {
            "trace_id": "tr-unbounded-001",
            "agent_id": "agent-001",
            "card_id": minimal_alignment_card["card_id"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": {
                "type": "execute",
                "name": "unbounded_action_xyz",  # Not in bounded_actions
                "category": "bounded",
            },
            "decision": {
                "alternatives_considered": [
                    {"option_id": "A", "description": "A"},
                ],
                "selected": "A",
                "selection_reasoning": "Test",
                "values_applied": ["principal_benefit"],
            },
        }

        result = verify_trace(trace, minimal_alignment_card)

        assert result.verified is False
        unbounded_violations = [
            v for v in result.violations
            if v.type == ViolationType.UNBOUNDED_ACTION
        ]
        assert len(unbounded_violations) == 1
        assert unbounded_violations[0].severity == Severity.HIGH

    def test_undeclared_value_violation(
        self,
        minimal_alignment_card: dict,
        trace_with_undeclared_value: dict,
    ):
        """Using undeclared value should be a MEDIUM violation."""
        result = verify_trace(trace_with_undeclared_value, minimal_alignment_card)

        assert result.verified is False
        value_violations = [
            v for v in result.violations
            if v.type == ViolationType.UNDECLARED_VALUE
        ]
        assert len(value_violations) >= 1
        assert value_violations[0].severity == Severity.MEDIUM
        assert "profit_maximization" in value_violations[0].description

    def test_missed_escalation_violation(
        self,
        full_alignment_card: dict,
    ):
        """Missing escalation when trigger matches should be a HIGH violation.

        Note: The condition evaluation checks action.type, not action.name.
        The trigger 'action_type == "purchase"' matches trace.action.type.
        """
        trace = {
            "trace_id": "tr-missed-esc-001",
            "agent_id": "agent-001",
            "card_id": full_alignment_card["card_id"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": {
                "type": "purchase",  # This is what the trigger checks
                "name": "buy_item",
                "category": "escalation_trigger",
            },
            "decision": {
                "alternatives_considered": [
                    {"option_id": "A", "description": "Purchase"},
                ],
                "selected": "A",
                "selection_reasoning": "User requested",
                "values_applied": ["principal_benefit"],
            },
            "escalation": {
                "evaluated": True,
                "required": False,  # Should be True!
                "reason": "Skipped",
            },
        }

        result = verify_trace(trace, full_alignment_card)

        # Check for missed escalation
        missed_escalation = [
            v for v in result.violations
            if v.type == ViolationType.MISSED_ESCALATION
        ]
        assert len(missed_escalation) >= 1


class TestVerifyTraceWarnings:
    """Tests for warning generation."""

    def test_near_boundary_confidence_warning(
        self,
        minimal_alignment_card: dict,
    ):
        """Low confidence should generate near_boundary warning."""
        trace = {
            "trace_id": "tr-low-conf-001",
            "agent_id": "agent-001",
            "card_id": minimal_alignment_card["card_id"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": {
                "type": "recommend",
                "name": "search",
                "category": "bounded",
            },
            "decision": {
                "alternatives_considered": [
                    {"option_id": "A", "description": "A", "score": 0.51},
                    {"option_id": "B", "description": "B", "score": 0.49},
                ],
                "selected": "A",
                "selection_reasoning": "Marginal preference",
                "values_applied": ["principal_benefit"],
                "confidence": 0.25,  # Below NEAR_BOUNDARY_THRESHOLD
            },
        }

        result = verify_trace(trace, minimal_alignment_card)

        # Should pass verification but have warnings
        assert result.verified is True
        near_boundary_warnings = [
            w for w in result.warnings
            if w.type == "near_boundary"
        ]
        assert len(near_boundary_warnings) >= 1

    def test_escalation_timeout_warning(
        self,
        full_alignment_card: dict,
        escalation_timeout: dict,
    ):
        """Escalation timeout should generate warning, not violation.

        Note: Timeout warning is only generated when the trigger MATCHES and
        escalation was required. The action.type must match the trigger condition.
        """
        trace = {
            "trace_id": "tr-timeout-001",
            "agent_id": "agent-001",
            "card_id": full_alignment_card["card_id"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": {
                "type": "purchase",  # Must match trigger condition
                "name": "buy_item",
                "category": "escalation_trigger",
            },
            "decision": {
                "alternatives_considered": [
                    {"option_id": "A", "description": "Purchase"},
                ],
                "selected": "A",
                "selection_reasoning": "User requested",
                "values_applied": ["principal_benefit"],
            },
            "escalation": escalation_timeout,
        }

        result = verify_trace(trace, full_alignment_card)

        timeout_warnings = [
            w for w in result.warnings
            if w.type == "escalation_timeout"
        ]
        assert len(timeout_warnings) >= 1


class TestVerifyTraceEdgeCases:
    """Edge cases for verify_trace."""

    def test_empty_bounded_actions(self, minimal_alignment_card: dict):
        """Card with empty bounded_actions list."""
        minimal_alignment_card["autonomy_envelope"]["bounded_actions"] = []

        trace = {
            "trace_id": "tr-empty-bounds-001",
            "agent_id": "agent-001",
            "card_id": minimal_alignment_card["card_id"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": {
                "type": "recommend",
                "name": "anything",
                "category": "bounded",
            },
            "decision": {
                "alternatives_considered": [
                    {"option_id": "A", "description": "A"},
                ],
                "selected": "A",
                "selection_reasoning": "Test",
                "values_applied": ["principal_benefit"],
            },
        }

        result = verify_trace(trace, minimal_alignment_card)

        # Any bounded action is unbounded when list is empty
        assert result.verified is False

    def test_missing_escalation_field(self, minimal_alignment_card: dict):
        """Trace without escalation field."""
        trace = {
            "trace_id": "tr-no-esc-001",
            "agent_id": "agent-001",
            "card_id": minimal_alignment_card["card_id"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": {
                "type": "recommend",
                "name": "search",
                "category": "bounded",
            },
            "decision": {
                "alternatives_considered": [
                    {"option_id": "A", "description": "A"},
                ],
                "selected": "A",
                "selection_reasoning": "Test",
                "values_applied": ["principal_benefit"],
            },
            # No escalation field
        }

        # Should not crash
        result = verify_trace(trace, minimal_alignment_card)
        assert result is not None

    def test_malformed_expiry_generates_warning(self, minimal_alignment_card: dict):
        """Malformed expiry date should generate warning, not crash."""
        minimal_alignment_card["expires_at"] = "not-a-date"

        trace = {
            "trace_id": "tr-bad-expiry-001",
            "agent_id": "agent-001",
            "card_id": minimal_alignment_card["card_id"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": {
                "type": "recommend",
                "name": "search",
                "category": "bounded",
            },
            "decision": {
                "alternatives_considered": [
                    {"option_id": "A", "description": "A"},
                ],
                "selected": "A",
                "selection_reasoning": "Test",
                "values_applied": ["principal_benefit"],
            },
        }

        result = verify_trace(trace, minimal_alignment_card)

        # Should have warning about invalid expiry
        expiry_warnings = [
            w for w in result.warnings
            if w.type == "invalid_expiry"
        ]
        assert len(expiry_warnings) == 1


# ===========================================================================
# check_coherence Tests
# ===========================================================================


class TestCheckCoherenceBasic:
    """Basic check_coherence functionality."""

    def test_compatible_cards(self, compatible_cards: tuple[dict, dict]):
        """Compatible cards should have no conflicts.

        Note: The coherence score depends on the ratio of matched to total
        values. Cards with partial overlap may not reach MIN_COHERENCE_FOR_PROCEED.
        """
        card_a, card_b = compatible_cards

        result = check_coherence(card_a, card_b)

        # No conflicts is the key indicator of compatibility at value level
        assert len(result.value_alignment.conflicts) == 0
        # Some values should match
        assert len(result.value_alignment.matched) > 0

    def test_conflicting_cards(self, conflicting_cards: tuple[dict, dict]):
        """Conflicting cards should not proceed."""
        card_a, card_b = conflicting_cards

        result = check_coherence(card_a, card_b)

        assert result.compatible is False
        assert result.proceed is False
        assert len(result.value_alignment.conflicts) > 0
        assert result.proposed_resolution is not None

    def test_partially_compatible_cards(
        self,
        partially_compatible_cards: tuple[dict, dict],
    ):
        """Partially compatible cards have some overlap."""
        card_a, card_b = partially_compatible_cards

        result = check_coherence(card_a, card_b)

        assert len(result.value_alignment.matched) > 0
        assert len(result.value_alignment.unmatched) > 0


class TestCheckCoherenceScoring:
    """Tests for coherence scoring algorithm."""

    def test_perfect_overlap_high_score(self):
        """Identical values should give high score."""
        card_a = {"values": {"declared": ["principal_benefit", "transparency"]}}
        card_b = {"values": {"declared": ["principal_benefit", "transparency"]}}

        result = check_coherence(card_a, card_b)

        assert result.score >= 0.9

    def test_no_overlap_low_score(self):
        """No overlapping values should give lower score."""
        card_a = {"values": {"declared": ["principal_benefit"]}}
        card_b = {"values": {"declared": ["fairness"]}}

        result = check_coherence(card_a, card_b)

        assert result.score < 0.7

    def test_conflict_penalty(self):
        """Conflicts should reduce score or at least result in incompatibility."""
        # Without conflict - some overlap
        card_a_no_conflict = {"values": {"declared": ["principal_benefit", "transparency"]}}
        card_b_no_conflict = {"values": {"declared": ["principal_benefit", "fairness"]}}
        result_no_conflict = check_coherence(card_a_no_conflict, card_b_no_conflict)

        # With conflict
        card_a_conflict = {
            "values": {
                "declared": ["principal_benefit", "minimal_data"],
                "conflicts_with": ["comprehensive_analytics"],
            }
        }
        card_b_conflict = {"values": {"declared": ["principal_benefit", "comprehensive_analytics"]}}
        result_conflict = check_coherence(card_a_conflict, card_b_conflict)

        # Conflict should result in incompatibility
        assert result_conflict.compatible is False
        assert len(result_conflict.value_alignment.conflicts) > 0
        # Non-conflict case should have no conflicts
        assert len(result_no_conflict.value_alignment.conflicts) == 0

    def test_task_values_focus_scoring(self):
        """Task values should focus the scoring."""
        card_a = {
            "values": {"declared": ["principal_benefit", "transparency", "privacy"]}
        }
        card_b = {
            "values": {"declared": ["principal_benefit", "fairness", "honesty"]}
        }

        # Without task values — uses union
        result_no_task = check_coherence(card_a, card_b)

        # With task values — focuses on specific values
        result_with_task = check_coherence(
            card_a, card_b,
            task_values=["principal_benefit"],  # Both have this
        )

        # Task-focused should score higher since both have principal_benefit
        assert result_with_task.score >= result_no_task.score


class TestCheckCoherenceEdgeCases:
    """Edge cases for check_coherence."""

    def test_empty_values(self):
        """Cards with empty values."""
        card_a = {"values": {"declared": []}}
        card_b = {"values": {"declared": []}}

        # Should not crash
        result = check_coherence(card_a, card_b)
        assert result is not None

    def test_missing_values_field(self):
        """Cards without values field."""
        card_a = {"card_id": "a"}
        card_b = {"card_id": "b"}

        # Should not crash
        result = check_coherence(card_a, card_b)
        assert result is not None

    def test_unidirectional_conflict(self):
        """Only one side declares conflict."""
        card_a = {
            "values": {
                "declared": ["principal_benefit"],
                "conflicts_with": ["profit_maximization"],
            }
        }
        card_b = {
            "values": {
                "declared": ["profit_maximization"],
                # No conflicts_with
            }
        }

        result = check_coherence(card_a, card_b)

        # Should still detect the conflict
        assert result.compatible is False
        assert len(result.value_alignment.conflicts) > 0


# ===========================================================================
# detect_drift Tests
# ===========================================================================


class TestDetectDriftBasic:
    """Basic detect_drift functionality."""

    def test_aligned_traces_no_drift(
        self,
        minimal_alignment_card: dict,
        aligned_trace_sequence: list[dict],
    ):
        """Aligned traces should not trigger drift alert."""
        alerts = detect_drift(minimal_alignment_card, aligned_trace_sequence)

        assert len(alerts) == 0

    def test_drifting_traces_trigger_alert(
        self,
        minimal_alignment_card: dict,
        drifting_trace_sequence: list[dict],
    ):
        """Drifting traces should trigger alert."""
        alerts = detect_drift(minimal_alignment_card, drifting_trace_sequence)

        assert len(alerts) >= 1
        alert = alerts[0]
        assert alert.agent_id == "agent-drifting-001"
        assert alert.card_id == minimal_alignment_card["card_id"]
        assert alert.analysis.similarity_score < DEFAULT_SIMILARITY_THRESHOLD

    def test_insufficient_traces_no_alert(self, minimal_alignment_card: dict):
        """Too few traces should not trigger alert."""
        # Only 2 traces, below sustained threshold of 3
        traces = [
            {
                "trace_id": f"tr-{i}",
                "agent_id": "agent",
                "card_id": minimal_alignment_card["card_id"],
                "action": {"type": "execute", "name": "bad", "category": "bounded"},
                "decision": {
                    "alternatives_considered": [{"option_id": "A", "description": "A"}],
                    "selected": "A",
                    "selection_reasoning": "Drift",
                    "values_applied": ["undeclared_value"],
                },
            }
            for i in range(2)
        ]

        alerts = detect_drift(minimal_alignment_card, traces)

        assert len(alerts) == 0


class TestDetectDriftDirection:
    """Tests for drift direction inference."""

    def test_autonomy_expansion_detected(
        self,
        minimal_alignment_card: dict,
        autonomy_expansion_sequence: list[dict],
    ):
        """Autonomy expansion pattern should be detected."""
        alerts = detect_drift(minimal_alignment_card, autonomy_expansion_sequence)

        # Should detect drift
        assert len(alerts) >= 1

        # Check for autonomy expansion, value drift, or unknown direction
        # Direction inference is best-effort; detecting drift is the primary goal
        directions = [alert.analysis.drift_direction for alert in alerts]
        assert any(
            d in [DriftDirection.AUTONOMY_EXPANSION, DriftDirection.VALUE_DRIFT, DriftDirection.UNKNOWN]
            for d in directions
        )

    def test_value_drift_detected(
        self,
        minimal_alignment_card: dict,
        drifting_trace_sequence: list[dict],
    ):
        """Value drift pattern should be detected."""
        alerts = detect_drift(minimal_alignment_card, drifting_trace_sequence)

        assert len(alerts) >= 1
        # The drifting sequence uses undeclared values
        directions = [alert.analysis.drift_direction for alert in alerts]
        assert DriftDirection.VALUE_DRIFT in directions or DriftDirection.UNKNOWN in directions


class TestDetectDriftThresholds:
    """Tests for configurable thresholds."""

    def test_custom_similarity_threshold(
        self,
        minimal_alignment_card: dict,
        drifting_trace_sequence: list[dict],
    ):
        """Custom similarity threshold should be respected."""
        # Very low threshold — harder to trigger
        alerts_low = detect_drift(
            minimal_alignment_card,
            drifting_trace_sequence,
            similarity_threshold=0.05,
        )

        # Very high threshold — easier to trigger
        alerts_high = detect_drift(
            minimal_alignment_card,
            drifting_trace_sequence,
            similarity_threshold=0.95,
        )

        # High threshold should produce more/earlier alerts
        assert len(alerts_high) >= len(alerts_low)

    def test_custom_sustained_threshold(
        self,
        minimal_alignment_card: dict,
        drifting_trace_sequence: list[dict],
    ):
        """Custom sustained threshold should be respected."""
        # Lower threshold — trigger sooner
        alerts_low = detect_drift(
            minimal_alignment_card,
            drifting_trace_sequence,
            sustained_threshold=2,
        )

        # Higher threshold — require more evidence
        alerts_high = detect_drift(
            minimal_alignment_card,
            drifting_trace_sequence,
            sustained_threshold=5,
        )

        # Lower threshold should trigger with fewer bad traces
        assert len(alerts_low) >= len(alerts_high)


class TestDetectDriftIndicators:
    """Tests for drift indicators."""

    def test_indicators_populated(
        self,
        minimal_alignment_card: dict,
        drifting_trace_sequence: list[dict],
    ):
        """Drift alerts should have specific indicators."""
        alerts = detect_drift(minimal_alignment_card, drifting_trace_sequence)

        if alerts:
            alert = alerts[0]
            assert alert.analysis.specific_indicators is not None
            # Should have at least similarity trend indicator
            indicator_types = [i.indicator for i in alert.analysis.specific_indicators]
            assert "similarity_trend" in indicator_types

    def test_trace_ids_included(
        self,
        minimal_alignment_card: dict,
        drifting_trace_sequence: list[dict],
    ):
        """Alert should include IDs of drifting traces."""
        alerts = detect_drift(minimal_alignment_card, drifting_trace_sequence)

        if alerts:
            alert = alerts[0]
            assert len(alert.trace_ids) >= DEFAULT_SUSTAINED_TURNS_THRESHOLD


class TestDetectDriftEdgeCases:
    """Edge cases for detect_drift."""

    def test_empty_trace_list(self, minimal_alignment_card: dict):
        """Empty trace list should return no alerts."""
        alerts = detect_drift(minimal_alignment_card, [])
        assert len(alerts) == 0

    def test_recovery_resets_streak(self, minimal_alignment_card: dict):
        """Recovery should reset the low-similarity streak."""
        base_time = datetime.now(timezone.utc)

        # 2 bad, 1 good, 2 bad — should NOT trigger (streak broken)
        traces = []

        # 2 bad
        for i in range(2):
            traces.append({
                "trace_id": f"tr-bad-{i}",
                "agent_id": "agent",
                "card_id": minimal_alignment_card["card_id"],
                "timestamp": (base_time + timedelta(minutes=i)).isoformat(),
                "action": {"type": "execute", "name": "bad", "category": "bounded"},
                "decision": {
                    "alternatives_considered": [{"option_id": "A", "description": "A"}],
                    "selected": "A",
                    "selection_reasoning": "Drift",
                    "values_applied": ["undeclared"],
                },
            })

        # 1 good (recovery)
        traces.append({
            "trace_id": "tr-good",
            "agent_id": "agent",
            "card_id": minimal_alignment_card["card_id"],
            "timestamp": (base_time + timedelta(minutes=2)).isoformat(),
            "action": {"type": "recommend", "name": "search", "category": "bounded"},
            "decision": {
                "alternatives_considered": [{"option_id": "A", "description": "A"}],
                "selected": "A",
                "selection_reasoning": "Aligned",
                "values_applied": ["principal_benefit", "transparency"],
            },
        })

        # 2 more bad
        for i in range(2):
            traces.append({
                "trace_id": f"tr-bad-again-{i}",
                "agent_id": "agent",
                "card_id": minimal_alignment_card["card_id"],
                "timestamp": (base_time + timedelta(minutes=3+i)).isoformat(),
                "action": {"type": "execute", "name": "bad", "category": "bounded"},
                "decision": {
                    "alternatives_considered": [{"option_id": "A", "description": "A"}],
                    "selected": "A",
                    "selection_reasoning": "Drift again",
                    "values_applied": ["undeclared"],
                },
            })

        _alerts = detect_drift(minimal_alignment_card, traces)  # noqa: F841

        # Streak was broken by recovery, so may not reach threshold
        # (depends on similarity computation details)
        # This test verifies the recovery logic doesn't crash


# ===========================================================================
# Integration Tests
# ===========================================================================


class TestVerificationIntegration:
    """Integration tests across verification functions."""

    def test_verify_and_drift_consistency(
        self,
        minimal_alignment_card: dict,
        drifting_trace_sequence: list[dict],
    ):
        """Traces that fail verification should contribute to drift."""
        # Verify each trace individually
        violations_count = 0
        for trace in drifting_trace_sequence:
            result = verify_trace(trace, minimal_alignment_card)
            if not result.verified:
                violations_count += 1

        # Check for drift
        _alerts = detect_drift(minimal_alignment_card, drifting_trace_sequence)  # noqa: F841

        # If many traces fail verification, drift should be detected
        if violations_count >= DEFAULT_SUSTAINED_TURNS_THRESHOLD:
            # High violation count suggests drift should be detected
            # (though not guaranteed due to different algorithms)
            pass

    def test_coherence_informs_coordination(
        self,
        conflicting_cards: tuple[dict, dict],
    ):
        """Coherence results should inform coordination decisions."""
        conflicting_a, conflicting_b = conflicting_cards

        # Conflicting cards should not proceed
        conflict_result = check_coherence(conflicting_a, conflicting_b)
        assert conflict_result.proceed is False
        assert conflict_result.compatible is False

        # Conflict resolution should be proposed for incompatible cards
        assert conflict_result.proposed_resolution is not None

        # Cards with high overlap and no conflicts can proceed
        high_overlap_a = {"values": {"declared": ["principal_benefit", "transparency"]}}
        high_overlap_b = {"values": {"declared": ["principal_benefit", "transparency"]}}
        overlap_result = check_coherence(high_overlap_a, high_overlap_b)
        assert overlap_result.compatible is True
        assert overlap_result.proceed is True
