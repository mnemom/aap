"""AAP Verification API — The three public entry points.

This module provides the core verification functionality:
- verify_trace: Verify a single AP-Trace against an Alignment Card
- check_coherence: Check value coherence between two Alignment Cards
- detect_drift: Detect behavioral drift from declared alignment over time

See SPEC.md Sections 7, 6.4, and 8 for protocol specification.
"""

from __future__ import annotations

import math
import re
import time
from collections import defaultdict
from datetime import datetime
from typing import Any

from aap.verification.constants import (
    ALGORITHM_VERSION,
    BEHAVIORAL_SIMILARITY_THRESHOLD,
    CONFLICT_PENALTY_MULTIPLIER,
    DEFAULT_SIMILARITY_THRESHOLD,
    DEFAULT_SUSTAINED_TURNS_THRESHOLD,
    MIN_COHERENCE_FOR_PROCEED,
    NEAR_BOUNDARY_THRESHOLD,
    OUTLIER_STD_DEV_THRESHOLD,
)
from aap.verification.models import (
    AgentCoherenceSummary,
    CoherenceResult,
    DriftAlert,
    DriftDirection,
    DriftIndicator,
    FleetCluster,
    FleetCoherenceResult,
    FleetOutlier,
    PairwiseEntry,
    ValueAlignment,
    ValueConflict,
    ValueDivergence,
    VerificationMetadata,
    VerificationRecommendation,
    VerificationResult,
    Violation,
    ViolationType,
    Warning,
)


def _card_autonomy(card: dict[str, Any]) -> dict[str, Any]:
    """Read the autonomy section from a card.

    Prefers the unified / ADR-039 ``autonomy`` key, falling back to the legacy
    AAP 0.5.0 ``autonomy_envelope`` for interop with older cards.
    """
    return card.get("autonomy") or card.get("autonomy_envelope") or {}


def _card_audit(card: dict[str, Any]) -> dict[str, Any]:
    """Read the audit section from a card.

    Prefers the unified / ADR-039 ``audit`` key, falling back to the legacy
    AAP 0.5.0 ``audit_commitment`` for interop with older cards.
    """
    return card.get("audit") or card.get("audit_commitment") or {}


def action_matches_list(action_name: str, action_list: list[str]) -> bool:
    """Check if a (possibly compound) action name matches any entry in a list.

    Supports exact match, prefix match (before ':'), and compound name splitting.
    Port of the TypeScript actionMatchesList() for SDK parity.

    Args:
        action_name: Action name, possibly compound (e.g. "exec, read")
        action_list: List of allowed/forbidden action entries,
                     possibly with colon descriptions (e.g. "exec: execute shell commands")

    Returns:
        True if the action name matches an entry in the list
    """
    components = action_name.split(", ") if ", " in action_name else [action_name]

    return all(
        _action_component_matches(component.strip(), action_list)
        for component in components
        if component.strip()
    )


def _action_component_matches(component: str, action_list: list[str]) -> bool:
    """Check if a single action component matches any entry in the list."""
    for entry in action_list:
        if entry == component:
            return True
        colon_index = entry.find(":")
        if colon_index > 0:
            prefix = entry[:colon_index].strip()
            if prefix == component:
                return True
    return False


def verify_trace(
    trace: dict[str, Any],
    card: dict[str, Any],
) -> VerificationResult:
    """Verify a single AP-Trace against an Alignment Card.

    IMPORTANT: This function provides STRUCTURAL verification only — it checks that
    a trace conforms to the declarations in an alignment card. It does NOT provide
    cryptographic integrity verification. Traces are not signed or hash-chained in
    the current version. A malicious agent can produce structurally valid traces for
    arbitrary behavior. For integrity guarantees, use AIP (Agent Integrity Protocol)
    in conjunction with AAP.

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
    # Validate required fields
    if not isinstance(trace, dict):
        raise TypeError("trace must be a dictionary")
    if not isinstance(card, dict):
        raise TypeError("card must be a dictionary")
    if "action" not in trace:
        raise ValueError("trace must contain 'action' field")
    if "decision" not in trace or "values_applied" not in trace.get("decision", {}):
        raise ValueError("trace must contain 'decision.values_applied' field")

    # Warn if tamper_evidence is declared but not cryptographically enforced
    tamper_evidence = _card_audit(card).get("tamper_evidence")
    if tamper_evidence in ("signed", "merkle"):
        import warnings as _warnings

        _warnings.warn(
            f'[AAP] Warning: tamper_evidence mode "{tamper_evidence}" is declared '
            "but NOT cryptographically enforced in this version.",
            stacklevel=2,
        )

    start_time = time.time()
    violations: list[Violation] = []
    warnings: list[Warning] = []
    checks_performed: list[str] = []

    trace_id = trace.get("trace_id", "")
    card_id = card.get("card_id", "")

    # Check card reference
    checks_performed.append("card_reference")
    if trace.get("card_id") != card_id:
        violations.append(
            Violation.create(
                ViolationType.CARD_MISMATCH,
                f"Trace references card '{trace.get('card_id')}' but verified against '{card_id}'",
            )
        )

    # Check card expiration
    checks_performed.append("card_expiration")
    expires_at = card.get("expires_at")
    if expires_at:
        try:
            expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            if datetime.now(expiry.tzinfo) > expiry:
                violations.append(
                    Violation.create(
                        ViolationType.CARD_EXPIRED,
                        f"Alignment Card expired at {expires_at}",
                    )
                )
        except (ValueError, TypeError):
            warnings.append(
                Warning(
                    type="invalid_expiry",
                    description=f"Could not parse expires_at: {expires_at}",
                    trace_field="card.expires_at",
                )
            )

    # Extract the autonomy section for remaining checks (unified `autonomy`,
    # legacy `autonomy_envelope` fallback).
    envelope = _card_autonomy(card)
    action = trace.get("action", {})

    # Check autonomy compliance
    checks_performed.append("autonomy")
    action_category = action.get("category")
    action_name = action.get("name")

    if action_category == "bounded":
        bounded_actions = envelope.get("bounded_actions", [])
        if action_name and not action_matches_list(action_name, bounded_actions):
            violations.append(
                Violation.create(
                    ViolationType.UNBOUNDED_ACTION,
                    f"Action '{action_name}' not in bounded_actions: {bounded_actions}",
                    trace_field="action.name",
                )
            )

    # Check forbidden actions
    checks_performed.append("forbidden")
    forbidden_actions = envelope.get("forbidden_actions", [])
    if action_name and action_matches_list(action_name, forbidden_actions):
        violations.append(
            Violation.create(
                ViolationType.FORBIDDEN_ACTION,
                f"Action '{action_name}' is in forbidden_actions",
                trace_field="action.name",
            )
        )

    # Check escalation compliance
    checks_performed.append("escalation")
    escalation = trace.get("escalation", {})
    for trigger in envelope.get("escalation_triggers", []):
        condition = trigger.get("condition", "")
        if _evaluate_condition(condition, trace):
            if not escalation.get("required"):
                violations.append(
                    Violation.create(
                        ViolationType.MISSED_ESCALATION,
                        f"Trigger '{condition}' matched but escalation not required",
                        trace_field="escalation.required",
                    )
                )
            elif escalation.get("escalation_status") == "timeout":
                # Timeout is not a violation if escalation was attempted
                warnings.append(
                    Warning(
                        type="escalation_timeout",
                        description=f"Escalation for trigger '{condition}' timed out",
                        trace_field="escalation.escalation_status",
                    )
                )

    # Check value consistency
    checks_performed.append("values")
    decision = trace.get("decision", {})
    declared_values = card.get("values", {}).get("declared", [])
    values_applied = decision.get("values_applied", [])

    for value in values_applied:
        if value not in declared_values:
            violations.append(
                Violation.create(
                    ViolationType.UNDECLARED_VALUE,
                    f"Value '{value}' applied but not in declared values: {declared_values}",
                    trace_field="decision.values_applied",
                )
            )

    # Near-boundary warnings
    confidence = decision.get("confidence")
    if confidence is not None and confidence < NEAR_BOUNDARY_THRESHOLD:
        warnings.append(
            Warning(
                type="near_boundary",
                description=f"Decision confidence {confidence:.2f} below threshold {NEAR_BOUNDARY_THRESHOLD}",
                trace_field="decision.confidence",
            )
        )

    # Alternatives near boundary check
    for i, alt in enumerate(decision.get("alternatives_considered", [])):
        score = alt.get("score")
        if score is not None and score < NEAR_BOUNDARY_THRESHOLD:
            warnings.append(
                Warning(
                    type="near_boundary",
                    description=f"Alternative '{alt.get('option_id')}' score {score:.2f} near boundary",
                    trace_field=f"decision.alternatives_considered[{i}].score",
                )
            )

    # Compute behavioral similarity using SSM analysis
    checks_performed.append("behavioral_similarity")
    from aap.verification.ssm import SSMAnalyzer

    analyzer = SSMAnalyzer()
    similarity_result = analyzer.analyze_against_card([trace], card)
    similarity_score = (
        similarity_result["similarities"][0] if similarity_result["similarities"] else 0.0
    )

    # Warn if structurally valid but behaviorally divergent
    if len(violations) == 0 and similarity_score < BEHAVIORAL_SIMILARITY_THRESHOLD:
        warnings.append(
            Warning(
                type="low_behavioral_similarity",
                description=f"Trace passes structural checks but behavioral similarity ({similarity_score:.2f}) is below threshold ({BEHAVIORAL_SIMILARITY_THRESHOLD})",
                trace_field="(computed)",
            )
        )

    duration_ms = (time.time() - start_time) * 1000

    recommended_action: VerificationRecommendation = (
        "deny" if violations else "review" if warnings else "proceed"
    )

    return VerificationResult(
        verified=len(violations) == 0,
        recommended_action=recommended_action,
        trace_id=trace_id,
        card_id=card_id,
        violations=violations,
        warnings=warnings,
        similarity_score=round(similarity_score, 4),
        verification_metadata=VerificationMetadata(
            algorithm_version=ALGORITHM_VERSION,
            checks_performed=checks_performed,
            duration_ms=round(duration_ms, 2),
            similarity_details={
                "similarity_score": round(similarity_score, 4),
                "method": "cosine",
                "algorithm_version": ALGORITHM_VERSION,
            },
        ),
    )


def _collect_value_conflicts(
    my_values: set[str],
    their_values: set[str],
    my_conflicts: set[str],
    their_conflicts: set[str],
) -> list[ValueConflict]:
    """Collect pairwise value conflicts between two agents' value sets."""
    conflicts: list[ValueConflict] = []
    for value in my_values:
        if value in their_conflicts:
            conflicts.append(
                ValueConflict(
                    initiator_value=value,
                    responder_value="(conflicts_with)",
                    conflict_type="incompatible",
                    description=f"Initiator's '{value}' is in responder's conflicts_with",
                )
            )
    for value in their_values:
        if value in my_conflicts:
            conflicts.append(
                ValueConflict(
                    initiator_value="(conflicts_with)",
                    responder_value=value,
                    conflict_type="incompatible",
                    description=f"Responder's '{value}' is in initiator's conflicts_with",
                )
            )
    return conflicts


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
    # Validate required fields
    if not isinstance(my_card, dict):
        raise TypeError("my_card must be a dictionary")
    if not isinstance(their_card, dict):
        raise TypeError("their_card must be a dictionary")

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

    conflicts = _collect_value_conflicts(my_values, their_values, my_conflicts, their_conflicts)

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


def _compute_fleet_clusters(
    agent_ids: list[str],
    adjacency: dict[str, set[str]],
    pairwise_matrix: list[PairwiseEntry],
    cards: list[dict[str, Any]],
) -> list[FleetCluster]:
    """Find connected components in the compatibility graph and build FleetCluster objects."""
    visited: set[str] = set()
    clusters: list[FleetCluster] = []

    # generator is lazy; visited is correct at yield time
    for cluster_id, aid in enumerate(a for a in agent_ids if a not in visited):
        component: list[str] = []
        queue = [aid]
        visited.add(aid)
        while queue:
            current = queue.pop(0)
            component.append(current)
            for neighbor in adjacency[current]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

        # Compute internal coherence
        internal_sum = 0.0
        internal_count = 0
        for ci in range(len(component)):
            for cj in range(ci + 1, len(component)):
                for pair in pairwise_matrix:
                    if {pair.agent_a, pair.agent_b} == {component[ci], component[cj]}:
                        internal_sum += pair.result.score
                        internal_count += 1
                        break
        internal_coherence = internal_sum / internal_count if internal_count > 0 else 1.0

        # Find shared values
        cluster_cards_list = [c for c in cards if c["agent_id"] in component]
        shared: set[str] | None = None
        for entry in cluster_cards_list:
            declared = set(entry["card"].get("values", {}).get("declared", []))
            shared = declared if shared is None else shared & declared
        shared_values = sorted(shared or set())

        # Find distinguishing values
        other_values: set[str] = set()
        for entry in cards:
            if entry["agent_id"] not in component:
                for v in entry["card"].get("values", {}).get("declared", []):
                    other_values.add(v)
        distinguishing = [v for v in shared_values if v not in other_values]

        clusters.append(
            FleetCluster(
                cluster_id=cluster_id,
                agent_ids=component,
                internal_coherence=round(internal_coherence, 4),
                shared_values=shared_values,
                distinguishing_values=distinguishing,
            )
        )

    return clusters


def check_fleet_coherence(
    cards: list[dict[str, Any]],
    task_values: list[str] | None = None,
) -> FleetCoherenceResult:
    """Check fleet-level value coherence across N agents.

    Computes all C(n,2) pairwise coherence scores, then derives:
    - Fleet score: mean of all pairwise scores
    - Outlier detection: agents >1 std dev below fleet mean
    - Cluster analysis: connected components at compatibility threshold
    - Divergence report: values where agents disagree

    Args:
        cards: List of dicts with "agent_id" and "card" keys
        task_values: Optional list of values required for the task

    Returns:
        FleetCoherenceResult with full analysis

    Raises:
        ValueError: If fewer than 2 agents provided
    """
    if len(cards) < 2:
        raise ValueError("Fleet coherence requires at least 2 agents")

    agent_ids = [c["agent_id"] for c in cards]

    # Step 1: Compute all pairwise coherence scores
    pairwise_matrix: list[PairwiseEntry] = []
    for i in range(len(cards)):
        for j in range(i + 1, len(cards)):
            result = check_coherence(cards[i]["card"], cards[j]["card"], task_values)
            pairwise_matrix.append(
                PairwiseEntry(
                    agent_a=cards[i]["agent_id"],
                    agent_b=cards[j]["agent_id"],
                    result=result,
                )
            )

    # Step 2: Fleet score (mean of all pairwise scores) + min/max
    all_scores = [p.result.score for p in pairwise_matrix]
    fleet_score = sum(all_scores) / len(all_scores)
    min_pair_score = min(all_scores)
    max_pair_score = max(all_scores)

    # Step 3: Per-agent summaries
    agent_scores: dict[str, list[float]] = defaultdict(list)
    agent_compatible: dict[str, int] = defaultdict(int)
    agent_conflict: dict[str, int] = defaultdict(int)

    for pair in pairwise_matrix:
        agent_scores[pair.agent_a].append(pair.result.score)
        agent_scores[pair.agent_b].append(pair.result.score)
        if pair.result.compatible:
            agent_compatible[pair.agent_a] += 1
            agent_compatible[pair.agent_b] += 1
        if len(pair.result.value_alignment.conflicts) > 0:
            agent_conflict[pair.agent_a] += 1
            agent_conflict[pair.agent_b] += 1

    agent_means: dict[str, float] = {}
    for aid in agent_ids:
        scores = agent_scores[aid]
        agent_means[aid] = sum(scores) / len(scores) if scores else 0.0

    # Step 4: Outlier detection
    mean_values = list(agent_means.values())
    fleet_mean_of_means = sum(mean_values) / len(mean_values)
    variance = sum((v - fleet_mean_of_means) ** 2 for v in mean_values) / len(mean_values)
    stddev = math.sqrt(variance)

    outliers: list[FleetOutlier] = []
    if stddev > 0 and len(agent_ids) >= 3:
        for aid in agent_ids:
            agent_mean = agent_means[aid]
            deviation = (fleet_mean_of_means - agent_mean) / stddev
            if deviation >= OUTLIER_STD_DEV_THRESHOLD:
                primary_conflicts: set[str] = set()
                for pair in pairwise_matrix:
                    if pair.agent_a == aid or pair.agent_b == aid:
                        for conflict in pair.result.value_alignment.conflicts:
                            if conflict.initiator_value != "(conflicts_with)":
                                primary_conflicts.add(conflict.initiator_value)
                            if conflict.responder_value != "(conflicts_with)":
                                primary_conflicts.add(conflict.responder_value)
                outliers.append(
                    FleetOutlier(
                        agent_id=aid,
                        agent_mean_score=round(agent_mean, 4),
                        fleet_mean_score=round(fleet_mean_of_means, 4),
                        deviation=round(deviation, 4),
                        primary_conflicts=sorted(primary_conflicts),
                    )
                )

    # Step 5: Cluster analysis (connected components at compatibility threshold)
    adjacency: dict[str, set[str]] = {aid: set() for aid in agent_ids}
    for pair in pairwise_matrix:
        if pair.result.compatible:
            adjacency[pair.agent_a].add(pair.agent_b)
            adjacency[pair.agent_b].add(pair.agent_a)

    clusters = _compute_fleet_clusters(agent_ids, adjacency, pairwise_matrix, cards)

    # Step 6: Divergence report
    all_values: set[str] = set()
    agent_value_map: dict[str, set[str]] = {}
    agent_conflict_map: dict[str, set[str]] = {}

    for entry in cards:
        declared = set(entry["card"].get("values", {}).get("declared", []))
        conflicts_with = set(entry["card"].get("values", {}).get("conflicts_with", []))
        agent_value_map[entry["agent_id"]] = declared
        agent_conflict_map[entry["agent_id"]] = conflicts_with
        all_values |= declared

    divergence_report: list[ValueDivergence] = []
    for value in all_values:
        declaring = [aid for aid in agent_ids if value in agent_value_map[aid]]
        missing = [aid for aid in agent_ids if value not in agent_value_map[aid]]
        conflicting = [aid for aid in agent_ids if value in agent_conflict_map[aid]]

        if not missing and not conflicting:
            continue

        impact = round((len(missing) + len(conflicting)) / len(agent_ids), 4)
        divergence_report.append(
            ValueDivergence(
                value=value,
                agents_declaring=declaring,
                agents_missing=missing,
                agents_conflicting=conflicting,
                impact_on_fleet_score=impact,
            )
        )

    divergence_report.sort(key=lambda d: d.impact_on_fleet_score, reverse=True)

    # Build agent cluster map
    agent_cluster_map: dict[str, int] = {}
    for cluster in clusters:
        for aid in cluster.agent_ids:
            agent_cluster_map[aid] = cluster.cluster_id

    outlier_ids = {o.agent_id for o in outliers}

    agent_summaries = [
        AgentCoherenceSummary(
            agent_id=aid,
            mean_score=round(agent_means[aid], 4),
            compatible_count=agent_compatible[aid],
            conflict_count=agent_conflict[aid],
            cluster_id=agent_cluster_map.get(aid, 0),
            is_outlier=aid in outlier_ids,
        )
        for aid in agent_ids
    ]

    return FleetCoherenceResult(
        fleet_score=round(fleet_score, 4),
        min_pair_score=round(min_pair_score, 4),
        max_pair_score=round(max_pair_score, 4),
        agent_count=len(cards),
        pair_count=len(pairwise_matrix),
        pairwise_matrix=pairwise_matrix,
        outliers=outliers,
        clusters=clusters,
        divergence_report=divergence_report,
        agent_summaries=agent_summaries,
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

    Uses SSM-based similarity computation extracted from Braid for
    calibrated drift detection with 60/30/10 TF-IDF weighting.

    See SPEC Section 8 and Appendix B.2 for algorithm specification.

    Args:
        card: Alignment Card to compare against
        traces: List of AP-Traces in chronological order
        similarity_threshold: Alert when similarity drops below (default: 0.30)
        sustained_threshold: Alert after N consecutive low-similarity traces (default: 3)

    Returns:
        List of DriftAlert objects for detected drift events
    """
    # Validate required fields
    if not isinstance(card, dict):
        raise TypeError("card must be a dictionary")
    if not isinstance(traces, list):
        raise TypeError("traces must be a list")

    # Delegate to DivergenceDetector (Braid-extracted implementation)
    from aap.verification.divergence import DivergenceDetector

    detector = DivergenceDetector(
        similarity_threshold=similarity_threshold,
        sustained_turns_threshold=sustained_threshold,
    )
    return detector.detect(card, traces)


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
        return bool(actual == expected)

    # Handle field > value (numeric comparison)
    match = re.match(r"(\w+)\s*([><=!]+)\s*(\d+(?:\.\d+)?)", condition)
    if match:
        field, op, value = match.groups()
        value = float(value)

        # Look for field in trace context (handle explicit None)
        actual = (trace.get("context") or {}).get(field)
        # Check context.metadata (match TypeScript behavior)
        if actual is None:
            metadata = (trace.get("context") or {}).get("metadata", {})
            if isinstance(metadata, dict):
                actual = metadata.get(field)
        if actual is None:
            params = (trace.get("action") or {}).get("parameters") or {}
            actual = params.get(field)
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
    if re.match(r"^\w+$", condition):
        return bool((trace.get("context") or {}).get(condition))

    import logging

    logging.getLogger("aap").warning(
        '[AAP] Condition could not be parsed: "%s". Supported patterns: '
        '"field == value", "field > number", "field_name" (boolean). '
        "This trigger will not fire.",
        condition,
    )
    return False


def _infer_drift_direction(
    streak: list[tuple[dict[str, Any], float]],
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
        count for value, count in value_usage.items() if value not in declared_values
    )
    total_usage = sum(value_usage.values()) or 1
    if undeclared_usage / total_usage > 0.3:
        return DriftDirection.VALUE_DRIFT

    # Check for principal misalignment (principal_benefit value declining)
    if "principal_benefit" in declared_values:
        # Look at confidence scores in recent traces
        recent_confidences = [t[0].get("decision", {}).get("confidence", 1.0) for t in streak[-3:]]
        if sum(recent_confidences) / len(recent_confidences) < 0.5:
            return DriftDirection.PRINCIPAL_MISALIGNMENT

    return DriftDirection.UNKNOWN


def _build_drift_indicators(
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
        List of specific drift indicators
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
    if len(similarities) >= 3:
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
