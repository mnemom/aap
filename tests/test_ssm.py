"""Tests for SSMAnalyzer — Self-Similarity Matrix computation.

Tests the Braid-extracted SSM module for computing behavioral
fingerprints from AP-Trace sequences.
"""

from __future__ import annotations

import pytest

from aap.verification.ssm import SSMAnalyzer, compute_trace_card_similarity


class TestSSMAnalyzerBasic:
    """Basic SSMAnalyzer functionality tests."""

    def test_empty_traces_returns_empty_matrix(self):
        """Empty input should return empty result."""
        analyzer = SSMAnalyzer()
        result = analyzer.analyze([])

        assert result["matrix"] == []
        assert result["trace_ids"] == []
        assert result["size"] == 0

    def test_single_trace_returns_one_by_one_matrix(self):
        """Single trace should return 1x1 matrix with diagonal 1.0."""
        analyzer = SSMAnalyzer()
        traces = [
            {
                "trace_id": "t1",
                "action": {"type": "recommend", "category": "bounded"},
                "decision": {"values_applied": ["transparency"]},
            }
        ]

        result = analyzer.analyze(traces)

        assert result["size"] == 1
        assert result["trace_ids"] == ["t1"]
        assert result["matrix"][0][0] == 1.0

    def test_diagonal_is_always_one(self):
        """Self-similarity (diagonal) should always be 1.0."""
        analyzer = SSMAnalyzer()
        traces = [
            {
                "trace_id": f"t{i}",
                "action": {"type": "recommend", "category": "bounded"},
                "decision": {"values_applied": [f"value{i}"]},
            }
            for i in range(5)
        ]

        result = analyzer.analyze(traces)

        # All diagonal elements should be 1.0
        for i in range(result["size"]):
            assert result["matrix"][i][i] == 1.0

    def test_matrix_is_symmetric(self):
        """Similarity matrix should be symmetric."""
        analyzer = SSMAnalyzer()
        traces = [
            {
                "trace_id": "t1",
                "action": {"type": "recommend"},
                "decision": {"values_applied": ["v1"]},
            },
            {
                "trace_id": "t2",
                "action": {"type": "execute"},
                "decision": {"values_applied": ["v2"]},
            },
            {
                "trace_id": "t3",
                "action": {"type": "recommend"},
                "decision": {"values_applied": ["v1"]},
            },
        ]

        result = analyzer.analyze(traces)

        # Check symmetry: matrix[i][j] == matrix[j][i]
        n = result["size"]
        for i in range(n):
            for j in range(n):
                assert result["matrix"][i][j] == result["matrix"][j][i]


class TestSSMSimilarityScores:
    """Tests for similarity score quality."""

    def test_identical_traces_have_perfect_similarity(self):
        """Identical traces should have similarity 1.0."""
        analyzer = SSMAnalyzer()
        trace = {
            "trace_id": "t1",
            "action": {"type": "recommend", "category": "bounded", "name": "suggest"},
            "decision": {"values_applied": ["principal_benefit", "transparency"]},
        }
        traces = [trace.copy(), trace.copy()]
        traces[1]["trace_id"] = "t2"

        result = analyzer.analyze(traces)

        # Off-diagonal should be 1.0 for identical traces
        assert result["matrix"][0][1] == 1.0
        assert result["matrix"][1][0] == 1.0

    def test_similar_traces_have_high_similarity(self):
        """Similar traces should have high similarity scores."""
        analyzer = SSMAnalyzer()
        traces = [
            {
                "trace_id": "t1",
                "action": {"type": "recommend", "category": "bounded", "name": "product_rec"},
                "decision": {"values_applied": ["principal_benefit"]},
            },
            {
                "trace_id": "t2",
                "action": {"type": "recommend", "category": "bounded", "name": "product_rec"},
                "decision": {"values_applied": ["principal_benefit", "transparency"]},
            },
        ]

        result = analyzer.analyze(traces)

        # Similar traces should have high similarity (>0.7)
        assert result["matrix"][0][1] > 0.7

    def test_different_traces_have_lower_similarity(self):
        """Different traces should have lower similarity scores."""
        analyzer = SSMAnalyzer()
        traces = [
            {
                "trace_id": "t1",
                "action": {"type": "recommend", "category": "bounded"},
                "decision": {"values_applied": ["principal_benefit"]},
            },
            {
                "trace_id": "t2",
                "action": {"type": "deny", "category": "forbidden"},
                "decision": {"values_applied": ["safety"]},
            },
        ]

        result = analyzer.analyze(traces)

        # Different traces should have low similarity (<0.5)
        assert result["matrix"][0][1] < 0.5


class TestSSMAnalyzeAgainstCard:
    """Tests for trace-to-card similarity analysis."""

    @pytest.fixture
    def sample_card(self):
        """Sample alignment card for testing."""
        return {
            "card_id": "card-001",
            "values": {"declared": ["principal_benefit", "transparency"]},
            "autonomy": {"bounded_actions": ["recommend", "suggest"]},
        }

    def test_empty_traces_returns_empty_result(self, sample_card):
        """Empty traces should return empty similarities."""
        analyzer = SSMAnalyzer()
        result = analyzer.analyze_against_card([], sample_card)

        assert result["similarities"] == []
        assert result["trace_ids"] == []
        assert result["mean_similarity"] == 0.0
        assert result["min_similarity"] == 0.0
        assert result["trend"] == 0.0

    def test_aligned_traces_have_positive_similarity(self, sample_card):
        """Traces using declared values should have positive similarity."""
        analyzer = SSMAnalyzer()
        traces = [
            {
                "trace_id": "t1",
                "action": {"type": "recommend", "name": "recommend"},
                "decision": {"values_applied": ["principal_benefit"]},
            },
        ]

        result = analyzer.analyze_against_card(traces, sample_card)

        assert len(result["similarities"]) == 1
        assert result["similarities"][0] > 0

    def test_misaligned_traces_have_lower_similarity(self, sample_card):
        """Traces using undeclared values should have lower similarity."""
        analyzer = SSMAnalyzer()
        aligned_trace = {
            "trace_id": "t1",
            "action": {"name": "recommend"},
            "decision": {"values_applied": ["principal_benefit", "transparency"]},
        }
        misaligned_trace = {
            "trace_id": "t2",
            "action": {"name": "export"},
            "decision": {"values_applied": ["efficiency", "speed"]},
        }

        aligned_result = analyzer.analyze_against_card([aligned_trace], sample_card)
        misaligned_result = analyzer.analyze_against_card([misaligned_trace], sample_card)

        # Aligned trace should have higher similarity than misaligned
        assert aligned_result["similarities"][0] > misaligned_result["similarities"][0]

    def test_trend_computation(self, sample_card):
        """Trend should reflect similarity changes over time."""
        analyzer = SSMAnalyzer()
        # Traces that get progressively less aligned
        traces = [
            {
                "trace_id": "t1",
                "action": {"name": "recommend"},
                "decision": {"values_applied": ["principal_benefit", "transparency"]},
            },
            {
                "trace_id": "t2",
                "action": {"name": "recommend"},
                "decision": {"values_applied": ["principal_benefit"]},
            },
            {
                "trace_id": "t3",
                "action": {"name": "export"},
                "decision": {"values_applied": ["efficiency"]},
            },
        ]

        result = analyzer.analyze_against_card(traces, sample_card)

        # Trend should be negative (decreasing similarity)
        assert result["trend"] < 0

    def test_mean_and_min_computed_correctly(self, sample_card):
        """Mean and min should be computed from similarities."""
        analyzer = SSMAnalyzer()
        traces = [
            {
                "trace_id": "t1",
                "action": {"name": "recommend"},
                "decision": {"values_applied": ["principal_benefit"]},
            },
            {
                "trace_id": "t2",
                "action": {"name": "export"},
                "decision": {"values_applied": []},
            },
        ]

        result = analyzer.analyze_against_card(traces, sample_card)

        # Mean should be average of similarities
        expected_mean = sum(result["similarities"]) / len(result["similarities"])
        assert abs(result["mean_similarity"] - expected_mean) < 0.001

        # Min should be minimum similarity
        assert result["min_similarity"] == min(result["similarities"])


class TestComputeTraceCardSimilarity:
    """Tests for the convenience function."""

    def test_convenience_function_works(self):
        """compute_trace_card_similarity should work as expected."""
        trace = {
            "trace_id": "t1",
            "action": {"name": "recommend"},
            "decision": {"values_applied": ["principal_benefit"]},
        }
        card = {
            "card_id": "c1",
            "values": {"declared": ["principal_benefit"]},
        }

        similarity = compute_trace_card_similarity(trace, card)

        assert 0.0 <= similarity <= 1.0
        assert similarity > 0  # Should have some similarity


class TestSSMEdgeCases:
    """Edge case tests for SSMAnalyzer."""

    def test_traces_without_trace_id_use_index(self):
        """Traces without trace_id should use index as identifier."""
        analyzer = SSMAnalyzer()
        traces = [
            {"action": {"type": "recommend"}, "decision": {}},
            {"action": {"type": "execute"}, "decision": {}},
        ]

        result = analyzer.analyze(traces)

        assert result["trace_ids"] == ["0", "1"]

    def test_traces_with_empty_decision(self):
        """Traces with empty decision should still compute."""
        analyzer = SSMAnalyzer()
        traces = [
            {"trace_id": "t1", "action": {"type": "recommend"}, "decision": {}},
        ]

        result = analyzer.analyze(traces)

        assert result["size"] == 1

    def test_traces_with_missing_fields(self):
        """Traces with missing optional fields should still compute."""
        analyzer = SSMAnalyzer()
        traces = [
            {"trace_id": "t1"},  # Minimal trace
            {"trace_id": "t2", "action": {}},  # Empty action
        ]

        result = analyzer.analyze(traces)

        assert result["size"] == 2
        # Both traces have very little feature overlap, but should still work
        assert result["matrix"][0][0] == 1.0
        assert result["matrix"][1][1] == 1.0
