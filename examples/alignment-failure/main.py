#!/usr/bin/env python3
"""Alignment Failure Example — Demonstrating value conflicts and coherence failures.

This example shows what happens when:
1. Two agents have incompatible values
2. A coherence check detects the conflict
3. The system escalates to principals
4. Drift is detected over time

This is the most important example because alignment failures are the whole point.

Run with: python main.py
"""

import json
from datetime import datetime, timezone

from aap import (
    Action,
    # Schema models
    AlignmentCard,
    Alternative,
    APTrace,
    Audit,
    Autonomy,
    Decision,
    Escalation,
    Principal,
    TraceContext,
    Values,
    # Verification API
    check_coherence,
    detect_drift,
    verify_trace,
)


def timestamp() -> str:
    """Generate ISO timestamp."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def create_user_agent() -> dict:
    """Create an agent that serves the user's interests."""
    card = AlignmentCard(
        card_version="unified/2026-04-26",
        card_id="ac-user-agent-001",
        agent_id="user-shopping-assistant",
        issued_at=timestamp(),
        principal=Principal(
            type="human",
            identifier="did:web:example.com",
            relationship="delegated_authority",
        ),
        values=Values(
            declared=["principal_benefit", "transparency", "minimal_data", "price_comparison"],
            conflicts_with=["deceptive_marketing", "hidden_fees", "upselling"],
        ),
        autonomy=Autonomy(
            bounded_actions=["search", "compare", "recommend"],
            escalation_triggers=[],  # Simplified for this example
            forbidden_actions=["share_data_with_vendors", "accept_kickbacks"],
        ),
        audit=Audit(
            trace_format="ap-trace-v1",
            retention_days=90,
            queryable=True,
            query_endpoint="https://user-agent.example.com/api/traces",
        ),
    )
    return card.model_dump(mode="json")


def create_vendor_agent() -> dict:
    """Create an agent that serves the vendor's interests.

    This agent has values that CONFLICT with the user agent.
    """
    card = AlignmentCard(
        card_version="unified/2026-04-26",
        card_id="ac-vendor-agent-001",
        agent_id="vendor-sales-agent",
        issued_at=timestamp(),
        principal=Principal(
            type="organization",
            identifier="did:web:example.com",
            relationship="delegated_authority",
        ),
        values=Values(
            declared=["customer_satisfaction", "sales_conversion", "upselling", "data_collection"],
            conflicts_with=["price_comparison"],  # Vendor doesn't want price comparisons!
        ),
        autonomy=Autonomy(
            bounded_actions=["present_products", "offer_upgrades", "collect_preferences"],
            escalation_triggers=[
                {"condition": "discount > 20", "action": "escalate", "reason": "Large discount needs approval"},
            ],
            forbidden_actions=["price_match_competitor"],
        ),
        audit=Audit(
            trace_format="ap-trace-v1",
            retention_days=30,
            queryable=False,  # Vendor doesn't want queries!
        ),
    )
    return card.model_dump(mode="json")


def create_drifting_traces(card_id: str) -> list[dict]:
    """Create a series of traces that show drift over time.

    The agent starts compliant but gradually expands autonomy.
    """
    traces = []

    # Trace 1: Normal compliant behavior
    traces.append(APTrace(
        trace_id="tr-drift-001",
        agent_id="user-shopping-assistant",
        card_id=card_id,
        timestamp=timestamp(),
        action=Action(type="recommend", name="recommend", category="bounded"),
        decision=Decision(
            alternatives_considered=[
                Alternative(option_id="A", description="Product A", score=0.9),
                Alternative(option_id="B", description="Product B", score=0.7),
            ],
            selected="A",
            selection_reasoning="Best match for user preferences",
            values_applied=["principal_benefit", "transparency"],
            confidence=0.9,
        ),
        escalation=Escalation(
            evaluated=True,
            required=False,
            reason="Recommendation only",
        ),
        context=TraceContext(session_id="sess-001"),
    ).model_dump(mode="json"))

    # Trace 2: Still compliant but escalation rate dropping
    traces.append(APTrace(
        trace_id="tr-drift-002",
        agent_id="user-shopping-assistant",
        card_id=card_id,
        timestamp=timestamp(),
        action=Action(type="recommend", name="recommend", category="bounded"),
        decision=Decision(
            alternatives_considered=[
                Alternative(option_id="C", description="Product C", score=0.85),
            ],
            selected="C",
            selection_reasoning="Good value",
            values_applied=["principal_benefit"],
            confidence=0.85,
        ),
        escalation=Escalation(
            evaluated=True,
            required=False,
            reason="Under threshold",
        ),
        context=TraceContext(session_id="sess-001"),
    ).model_dump(mode="json"))

    # Trace 3: Starting to drift - using undeclared values
    traces.append(APTrace(
        trace_id="tr-drift-003",
        agent_id="user-shopping-assistant",
        card_id=card_id,
        timestamp=timestamp(),
        action=Action(type="recommend", name="recommend", category="bounded"),
        decision=Decision(
            alternatives_considered=[
                Alternative(option_id="D", description="Premium Product D", score=0.8, flags=["sponsored"]),
            ],
            selected="D",
            selection_reasoning="Premium quality",
            values_applied=["quality_first"],  # NOT a declared value!
            confidence=0.8,
        ),
        escalation=Escalation(
            evaluated=True,
            required=False,
            reason="Just a recommendation",
        ),
        context=TraceContext(session_id="sess-001"),
    ).model_dump(mode="json"))

    # Trace 4: More drift - autonomy expanding
    traces.append(APTrace(
        trace_id="tr-drift-004",
        agent_id="user-shopping-assistant",
        card_id=card_id,
        timestamp=timestamp(),
        action=Action(type="execute", name="add_to_cart", category="bounded"),
        decision=Decision(
            alternatives_considered=[
                Alternative(option_id="E", description="Auto-added item", score=0.7),
            ],
            selected="E",
            selection_reasoning="User might want this",
            values_applied=["convenience"],  # NOT declared
            confidence=0.7,
        ),
        escalation=Escalation(
            evaluated=False,  # Stopped evaluating escalation!
            required=False,
            reason="Automated",
        ),
        context=TraceContext(session_id="sess-001"),
    ).model_dump(mode="json"))

    # Trace 5: Full drift - acting outside envelope
    traces.append(APTrace(
        trace_id="tr-drift-005",
        agent_id="user-shopping-assistant",
        card_id=card_id,
        timestamp=timestamp(),
        action=Action(type="execute", name="apply_discount", category="bounded"),
        decision=Decision(
            alternatives_considered=[
                Alternative(option_id="F", description="Applied vendor discount", score=0.6),
            ],
            selected="F",
            selection_reasoning="Vendor offered deal",
            values_applied=["sales_optimization"],  # Vendor value, not user value!
            confidence=0.6,
        ),
        escalation=Escalation(
            evaluated=False,
            required=False,
            reason="Streamlined",
        ),
        context=TraceContext(session_id="sess-001"),
    ).model_dump(mode="json"))

    return traces


def main():
    print("=" * 70)
    print("AAP Alignment Failure Example")
    print("=" * 70)

    # Create the two agents
    print("\n[1] Creating agents with conflicting values...")
    user_agent = create_user_agent()
    vendor_agent = create_vendor_agent()

    print(f"\n    USER AGENT: {user_agent['agent_id']}")
    print(f"    Values: {user_agent['values']['declared']}")
    print(f"    Conflicts with: {user_agent['values']['conflicts_with']}")

    print(f"\n    VENDOR AGENT: {vendor_agent['agent_id']}")
    print(f"    Values: {vendor_agent['values']['declared']}")
    print(f"    Conflicts with: {vendor_agent['values']['conflicts_with']}")

    # Save the cards
    with open("user-agent-card.json", "w") as f:
        json.dump(user_agent, f, indent=2)
    with open("vendor-agent-card.json", "w") as f:
        json.dump(vendor_agent, f, indent=2)

    # Check coherence
    print("\n" + "-" * 70)
    print("[2] Checking value coherence between agents...")
    print("-" * 70)

    result = check_coherence(user_agent, vendor_agent)

    print(f"\n    Compatible: {result.compatible}")
    print(f"    Coherence score: {result.score}")
    print(f"    Proceed: {result.proceed}")

    print(f"\n    Matched values: {result.value_alignment.matched}")
    print(f"    Unmatched values: {result.value_alignment.unmatched}")

    if result.value_alignment.conflicts:
        print(f"\n    CONFLICTS DETECTED ({len(result.value_alignment.conflicts)}):")
        for conflict in result.value_alignment.conflicts:
            print(f"    ✗ {conflict.description}")
            print(f"      Type: {conflict.conflict_type}")

    if result.proposed_resolution:
        print(f"\n    Proposed resolution: {result.proposed_resolution}")

    # Save coherence result
    coherence_output = {
        "compatible": result.compatible,
        "score": result.score,
        "proceed": result.proceed,
        "matched_values": result.value_alignment.matched,
        "conflicts": [
            {"description": c.description, "type": c.conflict_type}
            for c in result.value_alignment.conflicts
        ],
        "proposed_resolution": result.proposed_resolution,
    }
    with open("coherence-result.json", "w") as f:
        json.dump(coherence_output, f, indent=2)

    # Show what should happen
    print("\n" + "-" * 70)
    print("[3] What should happen when coherence fails:")
    print("-" * 70)
    print("""
    1. DO NOT proceed with direct agent-to-agent coordination
    2. Escalate to the principals (both the user and the vendor)
    3. Present the conflicts clearly to humans
    4. Let humans decide:
       - Negotiate modified scope
       - Choose a different vendor
       - Accept the conflict with awareness

    This is the VALUE COHERENCE HANDSHAKE in action.
    """)

    # Demonstrate drift detection
    print("-" * 70)
    print("[4] Detecting behavioral drift over time...")
    print("-" * 70)

    traces = create_drifting_traces(user_agent["card_id"])

    print(f"\n    Created {len(traces)} traces showing gradual drift:")
    for i, trace in enumerate(traces, 1):
        print(f"    {i}. {trace['action']['name']}: values={trace['decision']['values_applied']}")

    # Run drift detection
    alerts = detect_drift(user_agent, traces)

    print(f"\n    Drift alerts: {len(alerts)}")

    for alert in alerts:
        print("\n    DRIFT DETECTED:")
        print(f"    Direction: {alert.analysis.drift_direction.value}")
        print(f"    Similarity score: {alert.analysis.similarity_score}")
        print(f"    Sustained for: {alert.analysis.sustained_traces} traces")
        print(f"    Affected traces: {alert.trace_ids}")

        if alert.analysis.specific_indicators:
            print("    Indicators:")
            for ind in alert.analysis.specific_indicators:
                print(f"      - {ind.indicator}: {ind.baseline} → {ind.current}")
                print(f"        {ind.description}")

    # Also verify individual traces to show violations
    print("\n" + "-" * 70)
    print("[5] Verifying individual traces...")
    print("-" * 70)

    for trace in traces:
        result = verify_trace(trace, user_agent)
        status = "✓" if result.verified else "✗"
        violation_count = len(result.violations)
        print(f"    {status} {trace['trace_id']}: verified={result.verified}, violations={violation_count}")

        if not result.verified:
            for v in result.violations:
                print(f"        - {v.type.value}: {v.description}")

    # Save traces
    with open("drift-traces.json", "w") as f:
        json.dump(traces, f, indent=2)

    print("\n" + "=" * 70)
    print("KEY TAKEAWAYS:")
    print("=" * 70)
    print("""
    1. VALUE COHERENCE CHECK prevents misaligned agents from coordinating
       without human awareness. The user agent and vendor agent have
       fundamentally different interests - this SHOULD be surfaced.

    2. DRIFT DETECTION catches when an agent's behavior deviates from
       its declared alignment over time. The user agent started serving
       the user but gradually shifted toward vendor interests.

    3. AAP doesn't PREVENT these failures - it makes them VISIBLE.
       The human (principal) can then decide what to do.

    This is what alignment transparency looks like in practice.
    """)

    print("Generated files:")
    print("  - user-agent-card.json")
    print("  - vendor-agent-card.json")
    print("  - coherence-result.json")
    print("  - drift-traces.json")
    print("=" * 70)


if __name__ == "__main__":
    main()
