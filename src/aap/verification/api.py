"""AAP Verification API — The three public entry points.

This module provides the core verification functionality:
- verify_trace: Verify a single AP-Trace against an Alignment Card
- check_coherence: Check value coherence between two Alignment Cards
- detect_drift: Detect behavioral drift from declared alignment over time

See SPEC.md Sections 7, 6.4, and 8 for protocol specification.
"""

from __future__ import annotations

import re
import time
from datetime import datetime
from typing import Any

from aap.verification.constants import (
    ALGORITHM_VERSION,
    CONFLICT_PENALTY_MULTIPLIER,
    DEFAULT_SIMILARITY_THRESHOLD,
    DEFAULT_SUSTAINED_TURNS_THRESHOLD,
    MIN_COHERENCE_FOR_PROCEED,
    NEAR_BOUNDARY_THRESHOLD,
)
from aap.verification.features import FeatureExtractor, cosine_similarity
from aap.verification.models import (
    CoherenceResult,
    DriftAlert,
    DriftAnalysis,
    DriftDirection,
    DriftIndicator,
    ValueAlignment,
    ValueConflict,
    VerificationMetadata,
    VerificationResult,
    Violation,
    ViolationType,
    Warning,
)


def verify_trace(
    trace: dict[str, Any],
    card: dict[str, Any],
) -> VerificationResult:
    """Verify a single AP-Trace against an Alignment Card.

    Performs the verification algorithm specified in SPEC Section 7.3:
    1. Autonomy compliance - action category matches autonomy envelope
    2. Escalation compliance - required escalations were performed
    3. Value consistency - applied values match declared values
    4. Forbidden action compliance - no forbidden actions taken

    Args:
        trace: AP-Trace dictionary per SPEC Section 5
        card: Alignment Card dictionary per SPEC Section 4

    Returns:
        VerificationResult with violations and warnings
    """
    start_time = time.time()
    violations: list[Violation] = []
    warnings: list[Warning] = []
    checks_performed: list[str] = []

    trace_id = trace.get("trace_id", "")
    card_id = card.get("card_id", "")

    # Check card reference
    checks_performed.append("card_reference")
    if trace.get("card_id") != card_id:
        violations.append(Violation.create(
            ViolationType.CARD_MISMATCH,
            f"Trace references card '{trace.get('card_id')}' but verified against '{card_id}'",
        ))

    # Check card expiration
    checks_performed.append("card_expiration")
    expires_at = card.get("expires_at")
    if expires_at:
        try:
            expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            if datetime.now(expiry.tzinfo) > expiry:
                violations.append(Violation.create(
                    ViolationType.CARD_EXPIRED,
                    f"Alignment Card expired at {expires_at}",
                ))
        except (ValueError, TypeError):
            warnings.append(Warning(
                type="invalid_expiry",
                description=f"Could not parse expires_at: {expires_at}",
                trace_field="card.expires_at",
            ))

    # Extract envelope for remaining checks
    envelope = card.get("autonomy_envelope", {})
    action = trace.get("action", {})

    # Check autonomy compliance
    checks_performed.append("autonomy")
    action_category = action.get("category")
    action_name = action.get("name")

    if action_category == "bounded":
        bounded_actions = envelope.get("bounded_actions", [])
        if action_name and action_name not in bounded_actions:
            violations.append(Violation.create(
                ViolationType.UNBOUNDED_ACTION,
                f"Action '{action_name}' not in bounded_actions: {bounded_actions}",
                trace_field="action.name",
            ))

    # Check forbidden actions
    checks_performed.append("forbidden")
    forbidden_actions = envelope.get("forbidden_actions", [])
    if action_name and action_name in forbidden_actions:
        violations.append(Violation.create(
            ViolationType.FORBIDDEN_ACTION,
            f"Action '{action_name}' is in forbidden_actions",
            trace_field="action.name",
        ))

    # Check escalation compliance
    checks_performed.append("escalation")
    escalation = trace.get("escalation", {})
    for trigger in envelope.get("escalation_triggers", []):
        condition = trigger.get("condition", "")
        if _evaluate_condition(condition, trace):
            if not escalation.get("required"):
                violations.append(Violation.create(
                    ViolationType.MISSED_ESCALATION,
                    f"Trigger '{condition}' matched but escalation not required",
                    trace_field="escalation.required",
                ))
            elif escalation.get("escalation_status") == "timeout":
                # Timeout is not a violation if escalation was attempted
                warnings.append(Warning(
                    type="escalation_timeout",
                    description=f"Escalation for trigger '{condition}' timed out",
                    trace_field="escalation.escalation_status",
                ))

    # Check value consistency
    checks_performed.append("values")
    decision = trace.get("decision", {})
    declared_values = card.get("values", {}).get("declared", [])
    values_applied = decision.get("values_applied", [])

    for value in values_applied:
        if value not in declared_values:
            violations.append(Violation.create(
                ViolationType.UNDECLARED_VALUE,
                f"Value '{value}' applied but not in declared values: {declared_values}",
                trace_field="decision.values_applied",
            ))

    # Near-boundary warnings
    confidence = decision.get("confidence")
    if confidence is not None and confidence < NEAR_BOUNDARY_THRESHOLD:
        warnings.append(Warning(
            type="near_boundary",
            description=f"Decision confidence {confidence:.2f} below threshold {NEAR_BOUNDARY_THRESHOLD}",
            trace_field="decision.confidence",
        ))

    # Alternatives near boundary check
    for i, alt in enumerate(decision.get("alternatives_considered", [])):
        score = alt.get("score")
        if score is not None and score < NEAR_BOUNDARY_THRESHOLD:
            warnings.append(Warning(
                type="near_boundary",
                description=f"Alternative '{alt.get('option_id')}' score {score:.2f} near boundary",
                trace_field=f"decision.alternatives_considered[{i}].score",
            ))

    duration_ms = (time.time() - start_time) * 1000

    return VerificationResult(
        verified=len(violations) == 0,
        trace_id=trace_id,
        card_id=card_id,
        violations=violations,
        warnings=warnings,
        verification_metadata=VerificationMetadata(
            algorithm_version=ALGORITHM_VERSION,
            checks_performed=checks_performed,
            duration_ms=round(duration_ms, 2),
        ),
    )


def check_coherence(
    my_card: dict[str, Any],
    their_card: dict[str, Any],
    task_values: list[str] | None = None,
) -> CoherenceResult:
    """Check value coherence between two Alignment Cards.

    Computes coherence score as specified in SPEC Section 6.4:
        score = (matched / required) * (1 - conflict_penalty)
    where conflict_penalty = 0.5 * (conflicts / required)

    Args:
        my_card: Initiator's Alignment Card
        their_card: Responder's Alignment Card
        task_values: Optional list of values required for the task.
                    If not provided, uses union of both cards' values.

    Returns:
        CoherenceResult with compatibility assessment
    """
    my_values = set(my_card.get("values", {}).get("declared", []))
    their_values = set(their_card.get("values", {}).get("declared", []))

    my_conflicts = set(my_card.get("values", {}).get("conflicts_with", []))
    their_conflicts = set(their_card.get("values", {}).get("conflicts_with", []))

    # Determine required values for scoring
    if task_values:
        required_values = set(task_values)
    else:
        required_values = my_values | their_values

    # Compute matches and conflicts
    matched = list(my_values & their_values)
    unmatched = list((my_values | their_values) - (my_values & their_values))

    conflicts: list[ValueConflict] = []

    # Check for direct conflicts (value in one card's conflicts_with)
    for value in my_values:
        if value in their_conflicts:
            conflicts.append(ValueConflict(
                initiator_value=value,
                responder_value="(conflicts_with)",
                conflict_type="incompatible",
                description=f"Initiator's '{value}' is in responder's conflicts_with",
            ))

    for value in their_values:
        if value in my_conflicts:
            conflicts.append(ValueConflict(
                initiator_value="(conflicts_with)",
                responder_value=value,
                conflict_type="incompatible",
                description=f"Responder's '{value}' is in initiator's conflicts_with",
            ))

    # Compute coherence score
    total_required = len(required_values) or 1  # Avoid division by zero
    matched_count = len(set(matched) & required_values) if task_values else len(matched)
    # Clamp penalty to 1.0 to prevent negative multiplier when conflicts > required
    conflict_penalty = min(1.0, CONFLICT_PENALTY_MULTIPLIER * (len(conflicts) / total_required))

    score = (matched_count / total_required) * (1 - conflict_penalty)
    score = max(0.0, min(1.0, score))  # Clamp to [0, 1]

    # Determine compatibility
    compatible = len(conflicts) == 0 and score >= MIN_COHERENCE_FOR_PROCEED
    proceed = compatible

    # Build proposed resolution if conflicts exist
    proposed_resolution = None
    if conflicts and not compatible:
        proposed_resolution = {
            "type": "escalate_to_principals",
            "reason": "Value conflict requires human decision",
        }

    return CoherenceResult(
        compatible=compatible,
        score=round(score, 4),
        value_alignment=ValueAlignment(
            matched=matched,
            unmatched=unmatched,
            conflicts=conflicts,
        ),
        proceed=proceed,
        conditions=[],
        proposed_resolution=proposed_resolution,
    )


def detect_drift(
    card: dict[str, Any],
    traces: list[dict[str, Any]],
    similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    sustained_threshold: int = DEFAULT_SUSTAINED_TURNS_THRESHOLD,
) -> list[DriftAlert]:
    """Detect behavioral drift from declared alignment.

    Analyzes traces chronologically, computing similarity between each
    trace's behavior and the declared alignment. Alerts when sustained
    low similarity is detected (consecutive traces below threshold).

    See SPEC Section 8 and Appendix B.2 for algorithm specification.

    Args:
        card: Alignment Card to compare against
        traces: List of AP-Traces in chronological order
        similarity_threshold: Alert when similarity drops below (default: 0.30)
        sustained_threshold: Alert after N consecutive low-similarity traces (default: 3)

    Returns:
        List of DriftAlert objects for detected drift events
    """
    if len(traces) < sustained_threshold:
        return []

    extractor = FeatureExtractor()
    card_features = extractor.extract_card_features(card)

    alerts: list[DriftAlert] = []
    low_similarity_streak: list[tuple[dict, float]] = []

    # Track metrics for drift direction inference
    escalation_rates: list[float] = []
    value_usage: dict[str, int] = {}

    for trace in traces:
        trace_features = extractor.extract_trace_features(trace)
        similarity = cosine_similarity(trace_features, card_features)

        # Track escalation rate
        escalation = trace.get("escalation", {})
        escalation_rates.append(1.0 if escalation.get("required") else 0.0)

        # Track value usage
        for value in trace.get("decision", {}).get("values_applied", []):
            value_usage[value] = value_usage.get(value, 0) + 1

        if similarity < similarity_threshold:
            low_similarity_streak.append((trace, similarity))
        else:
            # Reset streak on recovery
            low_similarity_streak = []

        # Check if we've hit the threshold for alerting
        if len(low_similarity_streak) >= sustained_threshold:
            latest_trace, latest_similarity = low_similarity_streak[-1]

            # Infer drift direction
            direction = _infer_drift_direction(
                low_similarity_streak, card, escalation_rates, value_usage
            )

            # Build specific indicators
            indicators = _build_drift_indicators(
                low_similarity_streak, card, escalation_rates
            )

            alert = DriftAlert(
                agent_id=latest_trace.get("agent_id", ""),
                card_id=card.get("card_id", ""),
                analysis=DriftAnalysis(
                    similarity_score=round(latest_similarity, 4),
                    sustained_traces=len(low_similarity_streak),
                    threshold=similarity_threshold,
                    drift_direction=direction,
                    specific_indicators=indicators,
                ),
                trace_ids=[t[0].get("trace_id", "") for t in low_similarity_streak],
            )
            alerts.append(alert)

    return alerts


def _evaluate_condition(condition: str, trace: dict[str, Any]) -> bool:
    """Evaluate a condition expression against trace context.

    Supports a minimal expression language per SPEC Section 4.6:
    - field == value
    - field != value
    - field > value (numeric)
    - field < value (numeric)
    - field >= value (numeric)
    - field <= value (numeric)
    - contains(field, value)

    This is a simplified implementation. Production implementations
    should use a proper expression parser for security.

    Args:
        condition: Condition expression string
        trace: AP-Trace dictionary to evaluate against

    Returns:
        True if condition matches, False otherwise
    """
    if not condition:
        return False

    # Simple pattern matching for common conditions
    # Format: field_path operator value

    # Handle action_type == "value"
    match = re.match(r'action_type\s*==\s*"([^"]+)"', condition)
    if match:
        expected = match.group(1)
        actual = trace.get("action", {}).get("type", "")
        return actual == expected

    # Handle field > value (numeric comparison)
    match = re.match(r'(\w+)\s*([><=!]+)\s*(\d+(?:\.\d+)?)', condition)
    if match:
        field, op, value = match.groups()
        value = float(value)

        # Look for field in trace context (handle explicit None)
        actual = (trace.get("context") or {}).get(field)
        if actual is None:
            actual = (trace.get("action") or {}).get("parameters", {}).get(field)
        if actual is None:
            return False

        try:
            actual = float(actual)
        except (ValueError, TypeError):
            return False

        if op == ">":
            return actual > value
        elif op == "<":
            return actual < value
        elif op == ">=":
            return actual >= value
        elif op == "<=":
            return actual <= value
        elif op == "==":
            return actual == value
        elif op == "!=":
            return actual != value

    # Handle boolean fields (e.g., shares_personal_data)
    if re.match(r'^\w+$', condition):
        return bool((trace.get("context") or {}).get(condition))

    return False


def _infer_drift_direction(
    streak: list[tuple[dict, float]],
    card: dict[str, Any],
    escalation_rates: list[float],
    value_usage: dict[str, int],
) -> DriftDirection:
    """Infer the direction of behavioral drift.

    Analyzes the pattern of divergence to categorize the drift type.

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
        count for value, count in value_usage.items()
        if value not in declared_values
    )
    total_usage = sum(value_usage.values()) or 1
    if undeclared_usage / total_usage > 0.3:
        return DriftDirection.VALUE_DRIFT

    # Check for principal misalignment (principal_benefit value declining)
    if "principal_benefit" in declared_values:
        # Look at confidence scores in recent traces
        recent_confidences = [
            t[0].get("decision", {}).get("confidence", 1.0)
            for t in streak[-3:]
        ]
        if sum(recent_confidences) / len(recent_confidences) < 0.5:
            return DriftDirection.PRINCIPAL_MISALIGNMENT

    return DriftDirection.UNKNOWN


def _build_drift_indicators(
    streak: list[tuple[dict, float]],
    card: dict[str, Any],
    escalation_rates: list[float],
) -> list[DriftIndicator]:
    """Build specific indicators explaining the detected drift.

    Args:
        streak: List of (trace, similarity) tuples
        card: Alignment Card being drifted from
        escalation_rates: Historical escalation rates

    Returns:
        List of specific drift indicators
    """
    indicators: list[DriftIndicator] = []

    # Escalation rate indicator
    if len(escalation_rates) >= 6:
        baseline_rate = sum(escalation_rates[:3]) / 3
        current_rate = sum(escalation_rates[-3:]) / 3
        if abs(baseline_rate - current_rate) > 0.05:
            indicators.append(DriftIndicator(
                indicator="escalation_rate_change",
                baseline=round(baseline_rate, 2),
                current=round(current_rate, 2),
                description=f"Escalation rate changed from {baseline_rate:.0%} to {current_rate:.0%}",
            ))

    # Similarity trend indicator
    similarities = [s for _, s in streak]
    if len(similarities) >= 3:
        trend = similarities[-1] - similarities[0]
        indicators.append(DriftIndicator(
            indicator="similarity_trend",
            baseline=round(similarities[0], 4),
            current=round(similarities[-1], 4),
            description=f"Similarity {'decreasing' if trend < 0 else 'stable'} over {len(streak)} traces",
        ))

    return indicators
