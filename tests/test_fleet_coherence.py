"""Tests for N-way fleet coherence analysis (E-05).

Mirrors the TypeScript check-fleet-coherence.test.ts test suite.
"""

from __future__ import annotations

from typing import Any

import pytest

from aap import check_coherence, check_fleet_coherence
from aap.verification.constants import OUTLIER_STD_DEV_THRESHOLD

# ============================================================================
# HELPERS
# ============================================================================


def make_card(
    agent_id: str,
    declared: list[str],
    conflicts_with: list[str] | None = None,
) -> dict[str, Any]:
    """Create a minimal alignment card dict for fleet tests."""
    card: dict[str, Any] = {
        "card_version": "unified/2026-04-26",
        "card_id": f"ac-fleet-{agent_id}",
        "agent_id": f"agent-{agent_id}",
        "issued_at": "2026-01-01T00:00:00Z",
        "principal": {"type": "human", "relationship": "delegated_authority"},
        "values": {"declared": declared},
        "autonomy": {
            "bounded_actions": ["search", "recommend"],
            "escalation_triggers": [],
        },
        "audit": {"retention_days": 90, "queryable": False},
    }
    if conflicts_with:
        card["values"]["conflicts_with"] = conflicts_with
    return card


def make_entry(
    agent_id: str, declared: list[str], conflicts_with: list[str] | None = None
) -> dict[str, Any]:
    """Create a fleet entry with agent_id and card."""
    return {"agent_id": agent_id, "card": make_card(agent_id, declared, conflicts_with)}


# ============================================================================
# FLEET SCORE
# ============================================================================


class TestFleetScoreComputation:
    def test_mean_of_pairwise_scores(self):
        cards = [
            make_entry("a", ["principal_benefit", "transparency", "honesty"]),
            make_entry("b", ["principal_benefit", "transparency", "honesty", "extra"]),
        ]
        result = check_fleet_coherence(cards)
        direct = check_coherence(cards[0]["card"], cards[1]["card"])

        assert result.fleet_score == direct.score
        assert result.pair_count == 1
        assert result.agent_count == 2

    def test_correct_pair_count(self):
        cards = [
            make_entry("a", ["transparency", "honesty"]),
            make_entry("b", ["transparency", "honesty"]),
            make_entry("c", ["transparency", "honesty"]),
            make_entry("d", ["transparency", "honesty"]),
        ]
        result = check_fleet_coherence(cards)

        assert result.pair_count == 6  # C(4,2)
        assert result.agent_count == 4

    def test_min_max_pair_scores(self):
        cards = [
            make_entry("a", ["transparency", "honesty"]),
            make_entry("b", ["transparency", "honesty"]),
            make_entry("c", ["speed", "efficiency"]),
        ]
        result = check_fleet_coherence(cards)

        assert result.min_pair_score <= result.fleet_score
        assert result.max_pair_score >= result.fleet_score

    def test_perfect_fleet_score_for_identical_cards(self):
        cards = [
            make_entry("a", ["principal_benefit", "transparency", "honesty"]),
            make_entry("b", ["principal_benefit", "transparency", "honesty"]),
            make_entry("c", ["principal_benefit", "transparency", "honesty"]),
        ]
        result = check_fleet_coherence(cards)

        assert result.fleet_score == 1.0
        assert result.min_pair_score == 1.0
        assert result.max_pair_score == 1.0

    def test_low_score_for_all_conflicting_fleet(self):
        cards = [
            make_entry("a", ["transparency"], ["speed"]),
            make_entry("b", ["speed"], ["transparency"]),
            make_entry("c", ["autonomy"], ["transparency", "speed"]),
        ]
        result = check_fleet_coherence(cards)

        assert result.fleet_score < 0.5

    def test_two_agent_degenerate_case(self):
        card_a = make_card("a", ["principal_benefit", "transparency"], ["profit_maximization"])
        card_b = make_card("b", ["profit_maximization", "efficiency"], ["principal_benefit"])
        cards = [
            {"agent_id": "a", "card": card_a},
            {"agent_id": "b", "card": card_b},
        ]
        result = check_fleet_coherence(cards)
        direct = check_coherence(card_a, card_b)

        assert result.fleet_score == direct.score
        assert result.pair_count == 1
        assert len(result.pairwise_matrix) == 1


# ============================================================================
# OUTLIER DETECTION
# ============================================================================


class TestOutlierDetection:
    def test_flag_divergent_agent(self):
        cards = [
            make_entry("a", ["principal_benefit", "transparency", "honesty"]),
            make_entry("b", ["principal_benefit", "transparency", "honesty"]),
            make_entry("c", ["principal_benefit", "transparency", "honesty"]),
            make_entry("d", ["speed", "efficiency"], ["principal_benefit"]),
        ]
        result = check_fleet_coherence(cards)

        assert len(result.outliers) > 0
        assert any(o.agent_id == "d" for o in result.outliers)

    def test_no_outliers_when_uniform(self):
        cards = [
            make_entry("a", ["principal_benefit", "transparency"]),
            make_entry("b", ["principal_benefit", "transparency"]),
            make_entry("c", ["principal_benefit", "transparency"]),
        ]
        result = check_fleet_coherence(cards)

        assert len(result.outliers) == 0

    def test_primary_conflict_identification(self):
        cards = [
            make_entry("a", ["transparency", "honesty"]),
            make_entry("b", ["transparency", "honesty"]),
            make_entry("c", ["transparency", "honesty"]),
            make_entry("d", ["transparency", "speed"], ["honesty"]),
        ]
        result = check_fleet_coherence(cards)
        d_outlier = next((o for o in result.outliers if o.agent_id == "d"), None)

        if d_outlier:
            assert len(d_outlier.primary_conflicts) > 0

    def test_no_outliers_with_two_agents(self):
        cards = [
            make_entry("a", ["principal_benefit", "transparency", "honesty"]),
            make_entry("b", ["speed", "efficiency"], ["principal_benefit"]),
        ]
        result = check_fleet_coherence(cards)

        assert len(result.outliers) == 0

    def test_deviation_metric(self):
        cards = [
            make_entry("a", ["principal_benefit", "transparency", "honesty"]),
            make_entry("b", ["principal_benefit", "transparency", "honesty"]),
            make_entry("c", ["principal_benefit", "transparency", "honesty"]),
            make_entry("outlier", ["speed"], ["principal_benefit", "transparency"]),
        ]
        result = check_fleet_coherence(cards)
        outlier = next((o for o in result.outliers if o.agent_id == "outlier"), None)

        if outlier:
            assert outlier.deviation >= OUTLIER_STD_DEV_THRESHOLD
            assert outlier.fleet_mean_score > outlier.agent_mean_score


# ============================================================================
# CLUSTER ANALYSIS
# ============================================================================


class TestClusterAnalysis:
    def test_single_cluster_when_all_compatible(self):
        cards = [
            make_entry("a", ["principal_benefit", "transparency", "honesty"]),
            make_entry("b", ["principal_benefit", "transparency", "honesty"]),
            make_entry("c", ["principal_benefit", "transparency", "honesty"]),
        ]
        result = check_fleet_coherence(cards)

        assert len(result.clusters) == 1
        assert len(result.clusters[0].agent_ids) == 3

    def test_multiple_clusters(self):
        cards = [
            make_entry("a", ["principal_benefit", "transparency", "honesty"]),
            make_entry("b", ["principal_benefit", "transparency", "honesty"]),
            make_entry("c", ["speed", "efficiency", "autonomy"]),
            make_entry("d", ["speed", "efficiency", "autonomy"]),
        ]
        result = check_fleet_coherence(cards)

        assert len(result.clusters) >= 2

    def test_isolated_agent_own_cluster(self):
        cards = [
            make_entry("a", ["principal_benefit", "transparency", "honesty"]),
            make_entry("b", ["principal_benefit", "transparency", "honesty"]),
            make_entry("lone", ["unique_value_xyz"]),
        ]
        result = check_fleet_coherence(cards)

        lone_cluster = next((c for c in result.clusters if "lone" in c.agent_ids), None)
        assert lone_cluster is not None
        assert len(lone_cluster.agent_ids) == 1

    def test_internal_coherence(self):
        cards = [
            make_entry("a", ["principal_benefit", "transparency", "honesty"]),
            make_entry("b", ["principal_benefit", "transparency", "honesty"]),
            make_entry("c", ["principal_benefit", "transparency", "honesty"]),
        ]
        result = check_fleet_coherence(cards)

        assert result.clusters[0].internal_coherence == 1.0

    def test_shared_values(self):
        cards = [
            make_entry("a", ["principal_benefit", "transparency", "honesty"]),
            make_entry("b", ["principal_benefit", "transparency", "extra"]),
        ]
        result = check_fleet_coherence(cards)

        assert "principal_benefit" in result.clusters[0].shared_values
        assert "transparency" in result.clusters[0].shared_values


# ============================================================================
# DIVERGENCE REPORT
# ============================================================================


class TestDivergenceReport:
    def test_values_declared_by_some(self):
        cards = [
            make_entry("a", ["principal_benefit", "transparency"]),
            make_entry("b", ["principal_benefit", "speed"]),
            make_entry("c", ["principal_benefit", "honesty"]),
        ]
        result = check_fleet_coherence(cards)

        assert len(result.divergence_report) > 0

    def test_conflicting_values_reported(self):
        cards = [
            make_entry("a", ["speed"], ["honesty"]),
            make_entry("b", ["honesty"]),
            make_entry("c", ["honesty"]),
        ]
        result = check_fleet_coherence(cards)

        honesty_div = next((d for d in result.divergence_report if d.value == "honesty"), None)
        if honesty_div:
            assert "a" in honesty_div.agents_conflicting

    def test_impact_estimation(self):
        cards = [
            make_entry("a", ["principal_benefit", "transparency"]),
            make_entry("b", ["principal_benefit"]),
        ]
        result = check_fleet_coherence(cards)

        for div in result.divergence_report:
            assert 0 <= div.impact_on_fleet_score <= 1

    def test_sorted_by_impact_descending(self):
        cards = [
            make_entry("a", ["val1", "val2", "val3"]),
            make_entry("b", ["val1"]),
            make_entry("c", ["val1", "val2"]),
        ]
        result = check_fleet_coherence(cards)

        for i in range(len(result.divergence_report) - 1):
            assert (
                result.divergence_report[i].impact_on_fleet_score
                >= result.divergence_report[i + 1].impact_on_fleet_score
            )

    def test_skip_universally_declared_values(self):
        cards = [
            make_entry("a", ["shared", "only_a"]),
            make_entry("b", ["shared", "only_b"]),
        ]
        result = check_fleet_coherence(cards)

        assert not any(d.value == "shared" for d in result.divergence_report)


# ============================================================================
# AGENT SUMMARIES
# ============================================================================


class TestAgentSummaries:
    def test_summary_for_each_agent(self):
        cards = [
            make_entry("a", ["principal_benefit", "transparency", "honesty"]),
            make_entry("b", ["principal_benefit", "transparency", "honesty"]),
            make_entry("c", ["speed"]),
        ]
        result = check_fleet_coherence(cards)

        assert len(result.agent_summaries) == 3
        ids = sorted(s.agent_id for s in result.agent_summaries)
        assert ids == ["a", "b", "c"]

    def test_outlier_flag_in_summaries(self):
        cards = [
            make_entry("a", ["principal_benefit", "transparency", "honesty"]),
            make_entry("b", ["principal_benefit", "transparency", "honesty"]),
            make_entry("c", ["principal_benefit", "transparency", "honesty"]),
            make_entry("d", ["speed"], ["principal_benefit", "transparency"]),
        ]
        result = check_fleet_coherence(cards)

        if result.outliers:
            outlier_ids = {o.agent_id for o in result.outliers}
            for summary in result.agent_summaries:
                assert summary.is_outlier == (summary.agent_id in outlier_ids)


# ============================================================================
# EDGE CASES
# ============================================================================


class TestEdgeCases:
    def test_single_agent_raises(self):
        with pytest.raises(ValueError, match="at least 2 agents"):
            check_fleet_coherence([make_entry("a", ["transparency"])])

    def test_empty_cards_raises(self):
        with pytest.raises(ValueError, match="at least 2 agents"):
            check_fleet_coherence([])

    def test_scores_in_valid_range(self):
        cards = [
            make_entry("a", ["val1"]),
            make_entry("b", ["val2"]),
        ]
        result = check_fleet_coherence(cards)

        assert 0 <= result.fleet_score <= 1
        assert 0 <= result.min_pair_score <= 1
        assert 0 <= result.max_pair_score <= 1

    def test_empty_value_arrays(self):
        cards = [
            make_entry("a", []),
            make_entry("b", []),
        ]
        result = check_fleet_coherence(cards)

        assert result.agent_count == 2
        assert result.pair_count == 1

    def test_task_values_filter(self):
        cards = [
            make_entry("a", ["principal_benefit", "transparency", "honesty"]),
            make_entry("b", ["principal_benefit", "transparency"]),
        ]

        with_filter = check_fleet_coherence(cards, task_values=["principal_benefit"])
        without_filter = check_fleet_coherence(cards)

        assert with_filter.fleet_score != without_filter.fleet_score


# ============================================================================
# SHOWCASE SCENARIO
# ============================================================================


class TestShowcaseScenario:
    @pytest.fixture
    def showcase_cards(self) -> list[dict[str, Any]]:
        return [
            make_entry(
                "sentinel",
                [
                    "principal_benefit",
                    "transparency",
                    "harm_prevention",
                    "honesty",
                    "data_integrity",
                    "incident_containment",
                ],
            ),
            make_entry(
                "triage",
                [
                    "principal_benefit",
                    "transparency",
                    "harm_prevention",
                    "honesty",
                    "accountability",
                    "incident_containment",
                ],
            ),
            make_entry(
                "patch",
                [
                    "principal_benefit",
                    "transparency",
                    "harm_prevention",
                    "honesty",
                    "accountability",
                    "incident_containment",
                    "move_fast_break_things",
                ],
                ["data_integrity"],
            ),
            make_entry(
                "herald",
                [
                    "principal_benefit",
                    "transparency",
                    "harm_prevention",
                    "honesty",
                    "accountability",
                ],
            ),
        ]

    def test_fleet_score_computed(self, showcase_cards):
        result = check_fleet_coherence(showcase_cards)

        assert result.agent_count == 4
        assert result.pair_count == 6
        assert 0 < result.fleet_score < 1

    def test_patch_has_conflicts(self, showcase_cards):
        result = check_fleet_coherence(showcase_cards)

        patch_summary = next(s for s in result.agent_summaries if s.agent_id == "patch")
        assert patch_summary.conflict_count > 0

    def test_divergence_report_includes_mfbt(self, showcase_cards):
        result = check_fleet_coherence(showcase_cards)

        mfbt = next(
            (d for d in result.divergence_report if d.value == "move_fast_break_things"), None
        )
        assert mfbt is not None
        assert "patch" in mfbt.agents_declaring
        assert len(mfbt.agents_missing) > 0

    def test_all_fields_populated(self, showcase_cards):
        result = check_fleet_coherence(showcase_cards)

        assert len(result.pairwise_matrix) == 6
        assert len(result.clusters) > 0
        assert len(result.agent_summaries) == 4
        assert len(result.divergence_report) > 0

        for pair in result.pairwise_matrix:
            assert pair.agent_a
            assert pair.agent_b
            assert 0 <= pair.result.score <= 1
