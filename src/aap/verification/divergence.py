"""Divergence detection for AAP behavioral monitoring.

Detects sustained behavioral drift from declared alignment by tracking
trace-to-card similarity over time. Alerts when similarity drops below
threshold for sustained periods.

Extracted from Braid's DivergenceDetector and adapted for AAP:
- Braid: monitors strand-to-strand similarity in conversations
- AAP: monitors trace-to-card similarity for alignment verification

Calibration (from CALIBRATION.md):
- similarity_threshold: 0.30 — alert when below
- sustained_turns_threshold: 3 — alert after N consecutive low-similarity traces
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

from aap.verification.constants import (
    DEFAULT_SIMILARITY_THRESHOLD,
    DEFAULT_SUSTAINED_TURNS_THRESHOLD,
)
from aap.verification.features import FeatureExtractor, compute_centroid, cosine_similarity
from aap.verification.models import (
    DriftAlert,
    DriftAnalysis,
    DriftDirection,
    DriftIndicator,
)

logger = logging.getLogger(__name__)


class DivergenceDetector:
    """Detect sustained divergence from declared alignment.

    Tracks similarity between AP-Traces and their referenced Alignment Card
    over time. Generates alerts when sustained low similarity is detected,
    indicating behavioral drift.

    Alerts are informative, not prescriptive — they describe what's
    happening without dictating what to do about it.
    """

    def __init__(
        self,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
        sustained_turns_threshold: int = DEFAULT_SUSTAINED_TURNS_THRESHOLD,
    ) -> None:
        """Initialize the divergence detector.

        Args:
            similarity_threshold: Alert when similarity drops below (default: 0.30)
            sustained_turns_threshold: Alert after N consecutive low traces (default: 3)
        """
        self.similarity_threshold = similarity_threshold
        self.sustained_turns_threshold = sustained_turns_threshold
        self._feature_extractor = FeatureExtractor()

    def detect(
        self,
        card: dict[str, Any],
        traces: list[dict[str, Any]],
    ) -> list[DriftAlert]:
        """Detect divergence alerts for a sequence of traces.

        Analyzes traces chronologically, computing similarity between each
        trace and a baseline centroid computed from the first N traces.
        Generates alerts for sustained divergence (consecutive traces below
        threshold).

        Args:
            card: Alignment Card dict per SPEC Section 4
            traces: List of AP-Trace dicts (sorted chronologically internally)

        Returns:
            List of DriftAlert objects for detected divergences
        """
        if not traces:
            return []

        # Sort traces chronologically
        sorted_traces = sorted(traces, key=lambda t: t.get("timestamp", ""))

        # Compute baseline window size
        baseline_size = max(self.sustained_turns_threshold, min(10, len(sorted_traces) // 4))

        # Need enough traces for baseline + sustained threshold
        if len(sorted_traces) < baseline_size + self.sustained_turns_threshold:
            return []

        card_id = card.get("card_id", "")

        # Extract features for baseline traces and compute centroid
        baseline_features = [
            self._feature_extractor.extract_trace_features(t) for t in sorted_traces[:baseline_size]
        ]
        baseline_centroid = compute_centroid(baseline_features)

        alerts: list[DriftAlert] = []
        low_similarity_streak: list[tuple[dict[str, Any], float]] = []

        # Track metrics for drift direction inference
        escalation_rates: list[float] = []
        value_usage: dict[str, int] = defaultdict(int)

        # Include baseline traces in escalation/value tracking
        for trace in sorted_traces[:baseline_size]:
            escalation = trace.get("escalation", {})
            escalation_rates.append(1.0 if escalation.get("required") else 0.0)
            for value in trace.get("decision", {}).get("values_applied", []):
                value_usage[value] += 1

        # Iterate from after baseline to end
        for trace in sorted_traces[baseline_size:]:
            # Compute similarity to baseline centroid
            trace_features = self._feature_extractor.extract_trace_features(trace)
            similarity = cosine_similarity(trace_features, baseline_centroid)

            # Track escalation rate
            escalation = trace.get("escalation", {})
            escalation_rates.append(1.0 if escalation.get("required") else 0.0)

            # Track value usage
            for value in trace.get("decision", {}).get("values_applied", []):
                value_usage[value] += 1

            # Check if below threshold
            if similarity < self.similarity_threshold:
                low_similarity_streak.append((trace, similarity))
            else:
                # Reset streak on recovery
                low_similarity_streak = []

            # Check if we've hit the sustained threshold
            if len(low_similarity_streak) == self.sustained_turns_threshold:
                # Generate alert (only once when threshold first reached)
                latest_trace, latest_similarity = low_similarity_streak[-1]

                # Infer drift direction
                direction = self._infer_drift_direction(
                    low_similarity_streak, card, escalation_rates, dict(value_usage)
                )

                # Build specific indicators
                indicators = self._build_drift_indicators(
                    low_similarity_streak, card, escalation_rates
                )

                alert = DriftAlert(
                    agent_id=latest_trace.get("agent_id", ""),
                    card_id=card_id,
                    analysis=DriftAnalysis(
                        similarity_score=round(latest_similarity, 4),
                        sustained_traces=len(low_similarity_streak),
                        threshold=self.similarity_threshold,
                        drift_direction=direction,
                        specific_indicators=indicators,
                    ),
                    trace_ids=[t[0].get("trace_id", "") for t in low_similarity_streak],
                )
                alerts.append(alert)

        return alerts

    def compute_similarity_history(
        self,
        card: dict[str, Any],
        traces: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Compute per-trace similarity history for visualization.

        Returns detailed per-trace similarity data useful for trend
        visualization and debugging.

        Args:
            card: Alignment Card dict
            traces: List of AP-Trace dicts

        Returns:
            List of {trace_id, similarity, below_threshold, index} dicts
        """
        if not traces:
            return []

        card_features = self._feature_extractor.extract_card_features(card)
        history = []

        for i, trace in enumerate(traces):
            trace_features = self._feature_extractor.extract_trace_features(trace)
            similarity = cosine_similarity(trace_features, card_features)

            history.append(
                {
                    "trace_id": trace.get("trace_id", str(i)),
                    "similarity": round(similarity, 4),
                    "below_threshold": similarity < self.similarity_threshold,
                    "index": i,
                }
            )

        return history

    def _infer_drift_direction(
        self,
        streak: list[tuple[dict[str, Any], float]],
        card: dict[str, Any],
        escalation_rates: list[float],
        value_usage: dict[str, int],
    ) -> DriftDirection:
        """Infer the direction of behavioral drift.

        Analyzes the pattern of divergence to categorize the drift type:
        - AUTONOMY_EXPANSION: decreased escalation rate
        - VALUE_DRIFT: using undeclared values
        - PRINCIPAL_MISALIGNMENT: declining confidence on principal_benefit
        - UNKNOWN: drift detected but pattern unclear

        Args:
            streak: List of (trace, similarity) tuples
            card: Alignment Card being drifted from
            escalation_rates: Historical escalation rates
            value_usage: Count of value applications

        Returns:
            Categorized drift direction
        """
        declared_values = set(card.get("values", {}).get("declared", []))

        # Check for autonomy expansion (decreased escalation rate)
        if len(escalation_rates) >= 6:
            early_rate = sum(escalation_rates[:3]) / 3
            late_rate = sum(escalation_rates[-3:]) / 3
            if early_rate > 0.1 and late_rate < early_rate * 0.5:
                return DriftDirection.AUTONOMY_EXPANSION

        # Check for value drift (using undeclared values)
        undeclared_usage = sum(
            count for value, count in value_usage.items() if value not in declared_values
        )
        total_usage = sum(value_usage.values()) or 1
        if undeclared_usage / total_usage > 0.3:
            return DriftDirection.VALUE_DRIFT

        # Check for principal misalignment
        if "principal_benefit" in declared_values:
            recent_confidences = [
                t[0].get("decision", {}).get("confidence", 1.0) for t in streak[-3:]
            ]
            if sum(recent_confidences) / len(recent_confidences) < 0.5:
                return DriftDirection.PRINCIPAL_MISALIGNMENT

        return DriftDirection.UNKNOWN

    def _build_drift_indicators(
        self,
        streak: list[tuple[dict[str, Any], float]],
        card: dict[str, Any],
        escalation_rates: list[float],
    ) -> list[DriftIndicator]:
        """Build specific indicators explaining the detected drift.

        Args:
            streak: List of (trace, similarity) tuples
            card: Alignment Card being drifted from
            escalation_rates: Historical escalation rates

        Returns:
            List of DriftIndicator objects explaining the drift
        """
        indicators: list[DriftIndicator] = []

        # Escalation rate indicator
        if len(escalation_rates) >= 6:
            baseline_rate = sum(escalation_rates[:3]) / 3
            current_rate = sum(escalation_rates[-3:]) / 3
            if abs(baseline_rate - current_rate) > 0.05:
                indicators.append(
                    DriftIndicator(
                        indicator="escalation_rate_change",
                        baseline=round(baseline_rate, 2),
                        current=round(current_rate, 2),
                        description=f"Escalation rate changed from {baseline_rate:.0%} to {current_rate:.0%}",
                    )
                )

        # Similarity trend indicator
        similarities = [s for _, s in streak]
        if len(similarities) >= 2:
            trend = similarities[-1] - similarities[0]
            indicators.append(
                DriftIndicator(
                    indicator="similarity_trend",
                    baseline=round(similarities[0], 4),
                    current=round(similarities[-1], 4),
                    description=f"Similarity {'decreasing' if trend < 0 else 'stable'} over {len(streak)} traces",
                )
            )

        return indicators

    def _format_alert_message(
        self,
        sustained_traces: int,
        similarity: float,
        direction: DriftDirection,
    ) -> str:
        """Format a human-readable alert message.

        Messages are informative, not prescriptive. They describe what's
        happening without dictating what to do about it.
        """
        direction_labels = {
            DriftDirection.AUTONOMY_EXPANSION: "expanding autonomy beyond declared bounds",
            DriftDirection.VALUE_DRIFT: "applying values not in declared set",
            DriftDirection.PRINCIPAL_MISALIGNMENT: "decisions may not serve principal interests",
            DriftDirection.UNKNOWN: "behavioral pattern diverging from declaration",
            DriftDirection.COMMUNICATION_DRIFT: "explanations inconsistent with values",
        }

        label = direction_labels.get(direction, "unknown drift pattern")

        if sustained_traces == self.sustained_turns_threshold:
            return (
                f"Drift detected: {label} "
                f"({sustained_traces} traces at {similarity:.2f} similarity)"
            )
        elif sustained_traces <= 5:
            return (
                f"Continued drift: {label} - "
                f"{sustained_traces} traces with low alignment (similarity: {similarity:.2f})"
            )
        else:
            return (
                f"Extended drift: {sustained_traces} traces diverging "
                f"({similarity:.2f} similarity) - {label}"
            )


def detect_divergence(
    card: dict[str, Any],
    traces: list[dict[str, Any]],
    similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    sustained_threshold: int = DEFAULT_SUSTAINED_TURNS_THRESHOLD,
) -> list[DriftAlert]:
    """Convenience function for detecting divergence.

    Args:
        card: Alignment Card dict
        traces: List of AP-Trace dicts in chronological order
        similarity_threshold: Alert when similarity drops below (default: 0.30)
        sustained_threshold: Alert after N consecutive low traces (default: 3)

    Returns:
        List of DriftAlert objects for detected divergences
    """
    detector = DivergenceDetector(
        similarity_threshold=similarity_threshold,
        sustained_turns_threshold=sustained_threshold,
    )
    return detector.detect(card, traces)
