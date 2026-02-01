"""SSM (Self-Similarity Matrix) analyzer for AAP drift detection.

Computes self-similarity matrices across AP-Traces using the calibrated
60/30/10 TF-IDF feature weighting. Extracted from Braid's SSMAnalyzer
and adapted for the AAP domain.

The SSM provides a cognitive fingerprint of behavioral patterns over time,
enabling detection of sustained drift from declared alignment.
"""

from __future__ import annotations

from typing import Any

from aap.verification.features import FeatureExtractor, cosine_similarity


class SSMAnalyzer:
    """Compute NxN self-similarity matrix for AP-Traces.

    Given a sequence of traces, computes pairwise similarity between all
    pairs to produce a matrix showing how behavioral patterns relate
    across time. Diagonal is always 1.0 (self-similarity).

    The matrix reveals:
    - Consistent behavior: high similarity in off-diagonal regions
    - Phase changes: block structure along diagonal
    - Drift: decreasing similarity in recent rows/columns
    """

    def __init__(self) -> None:
        """Initialize the SSM analyzer."""
        self._feature_extractor = FeatureExtractor()

    def analyze(self, traces: list[dict[str, Any]]) -> dict[str, Any]:
        """Compute self-similarity matrix for a list of AP-Traces.

        Args:
            traces: List of AP-Trace dicts per SPEC Section 5

        Returns:
            {
                "matrix": [[float]],  # NxN similarity matrix
                "trace_ids": [str],   # Ordered trace IDs
                "size": int           # Matrix dimension
            }
        """
        if not traces:
            return {"matrix": [], "trace_ids": [], "size": 0}

        # Extract feature vectors from each trace
        vectors = [self._extract_trace_vector(trace) for trace in traces]
        trace_ids = [trace.get("trace_id", str(i)) for i, trace in enumerate(traces)]

        # Compute NxN similarity matrix
        n = len(vectors)
        matrix = [[0.0] * n for _ in range(n)]

        for i in range(n):
            for j in range(i, n):
                sim = self._compute_similarity(vectors[i], vectors[j])
                matrix[i][j] = sim
                matrix[j][i] = sim  # Symmetric

        return {"matrix": matrix, "trace_ids": trace_ids, "size": n}

    def analyze_against_card(
        self,
        traces: list[dict[str, Any]],
        card: dict[str, Any],
    ) -> dict[str, Any]:
        """Compute similarity of each trace against an Alignment Card.

        Returns a 1xN vector of similarities plus aggregate statistics.

        Args:
            traces: List of AP-Trace dicts
            card: Alignment Card dict per SPEC Section 4

        Returns:
            {
                "similarities": [float],  # Per-trace similarity to card
                "trace_ids": [str],       # Ordered trace IDs
                "mean_similarity": float, # Average similarity
                "min_similarity": float,  # Minimum similarity
                "trend": float,           # Slope of similarity over time
            }
        """
        if not traces:
            return {
                "similarities": [],
                "trace_ids": [],
                "mean_similarity": 0.0,
                "min_similarity": 0.0,
                "trend": 0.0,
            }

        card_vector = self._extract_card_vector(card)
        trace_ids = [trace.get("trace_id", str(i)) for i, trace in enumerate(traces)]

        similarities = []
        for trace in traces:
            trace_vector = self._extract_trace_vector(trace)
            sim = self._compute_similarity(trace_vector, card_vector)
            similarities.append(round(sim, 4))

        # Compute aggregate statistics
        mean_sim = sum(similarities) / len(similarities) if similarities else 0.0
        min_sim = min(similarities) if similarities else 0.0

        # Compute trend (simple linear regression slope)
        trend = self._compute_trend(similarities)

        return {
            "similarities": similarities,
            "trace_ids": trace_ids,
            "mean_similarity": round(mean_sim, 4),
            "min_similarity": round(min_sim, 4),
            "trend": round(trend, 4),
        }

    def _extract_trace_vector(self, trace: dict[str, Any]) -> dict[str, float]:
        """Extract feature vector from an AP-Trace.

        Combines structural features (action, category, values) with
        content features (from selection_reasoning).
        """
        return self._feature_extractor.extract_trace_features(trace)

    def _extract_card_vector(self, card: dict[str, Any]) -> dict[str, float]:
        """Extract feature vector from an Alignment Card."""
        return self._feature_extractor.extract_card_features(card)

    def _compute_similarity(
        self,
        a: dict[str, float],
        b: dict[str, float],
    ) -> float:
        """Compute cosine similarity between two sparse feature vectors."""
        return cosine_similarity(a, b)

    def _compute_trend(self, values: list[float]) -> float:
        """Compute linear trend (slope) of a sequence of values.

        Positive trend = increasing similarity (recovering)
        Negative trend = decreasing similarity (drifting)
        """
        if len(values) < 2:
            return 0.0

        n = len(values)
        x_mean = (n - 1) / 2
        y_mean = sum(values) / n

        numerator = sum((i - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return 0.0

        return numerator / denominator


def compute_trace_card_similarity(
    trace: dict[str, Any],
    card: dict[str, Any],
) -> float:
    """Convenience function to compute similarity between a trace and card.

    Args:
        trace: AP-Trace dict
        card: Alignment Card dict

    Returns:
        Similarity score in [0.0, 1.0]
    """
    analyzer = SSMAnalyzer()
    result = analyzer.analyze_against_card([trace], card)
    return result["similarities"][0] if result["similarities"] else 0.0
