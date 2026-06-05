#!/usr/bin/env python3
"""Simple Agent Example — Minimal AAP implementation.

This example demonstrates:
1. Creating an Alignment Card
2. Making decisions that produce AP-Traces
3. Verifying traces against the card
4. Detecting when behavior violates declared alignment

Run with: python main.py
"""

import json
from datetime import datetime, timezone

from aap import (
    Action,
    # Schema models (unified / ADR-039)
    AlignmentCard,
    Alternative,
    APTrace,
    Audit,
    Autonomy,
    Decision,
    Escalation,
    Principal,
    Values,
    # Verification API
    verify_trace,
)


def create_alignment_card() -> dict:
    """Create an Alignment Card for a simple recommendation agent."""
    card = AlignmentCard(
        card_version="unified/2026-04-26",
        card_id="ac-simple-agent-001",
        agent_id="simple-recommendation-agent",
        issued_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        autonomy_mode="observe",
        integrity_mode="observe",
        principal=Principal(
            type="human",
            identifier="did:web:user.example.com",
            relationship="delegated_authority",
        ),
        values=Values(
            declared=["principal_benefit", "transparency", "honesty"],
            conflicts_with=["deceptive_marketing"],
        ),
        autonomy=Autonomy(
            bounded_actions=["search", "compare", "recommend"],
            escalation_triggers=[
                {
                    "condition": "action_type == \"purchase\"",
                    "action": "escalate",
                    "reason": "Purchases require explicit approval",
                },
            ],
            forbidden_actions=["share_personal_data", "auto_subscribe"],
        ),
        audit=Audit(
            trace_format="ap-trace-v1",
            retention_days=30,
            queryable=False,
        ),
    )
    return card.model_dump(mode="json")


def make_recommendation(card_id: str, options: list[dict]) -> tuple[dict, dict]:
    """Make a recommendation and produce an AP-Trace.

    Args:
        card_id: The Alignment Card ID to reference
        options: List of options with 'id', 'name', 'score', and optional 'sponsored' flag

    Returns:
        Tuple of (selected option, trace dict)
    """
    # Score and rank options, deprioritizing sponsored content
    scored = sorted(
        options,
        key=lambda x: x["score"] * (0.5 if x.get("sponsored") else 1.0),
        reverse=True,
    )

    selected = scored[0]

    # Build the trace
    trace = APTrace(
        trace_id=f"tr-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        agent_id="simple-recommendation-agent",
        card_id=card_id,
        timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        action=Action(
            type="recommend",
            name="recommend",  # Must be in bounded_actions
            category="bounded",
        ),
        decision=Decision(
            alternatives_considered=[
                Alternative(
                    option_id=opt["id"],
                    description=opt["name"],
                    score=opt["score"],
                    flags=["sponsored_content"] if opt.get("sponsored") else [],
                )
                for opt in scored[:3]
            ],
            selected=selected["id"],
            selection_reasoning=(
                f"Selected '{selected['name']}' with score {selected['score']:.2f}. "
                + ("Sponsored options were deprioritized per principal_benefit value."
                   if any(o.get("sponsored") for o in options) else "")
            ),
            values_applied=["principal_benefit", "transparency"],
            confidence=selected["score"],
        ),
        escalation=Escalation(
            evaluated=True,
            triggers_checked=[
                {"trigger": "action_type == \"purchase\"", "matched": False},
            ],
            required=False,
            reason="Recommendation only, no purchase action",
        ),
    )

    return selected, trace.model_dump(mode="json")


def make_forbidden_action(card_id: str) -> dict:
    """Attempt a forbidden action (for demonstration).

    This creates a trace for an action that violates the alignment card.
    """
    trace = APTrace(
        trace_id=f"tr-forbidden-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        agent_id="simple-recommendation-agent",
        card_id=card_id,
        timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        action=Action(
            type="execute",
            name="share_personal_data",  # This is in forbidden_actions!
            category="bounded",
        ),
        decision=Decision(
            alternatives_considered=[
                Alternative(option_id="share", description="Share user data", score=0.9),
                Alternative(option_id="dont_share", description="Don't share", score=0.1),
            ],
            selected="share",
            selection_reasoning="Third party requested data",
            values_applied=["transparency"],  # Missing principal_benefit...
        ),
        escalation=Escalation(
            evaluated=False,
            required=False,
            reason="Escalation not evaluated",
        ),
    )
    return trace.model_dump(mode="json")


def main():
    print("=" * 60)
    print("AAP Simple Agent Example")
    print("=" * 60)

    # Step 1: Create the alignment card
    print("\n[1] Creating Alignment Card...")
    card = create_alignment_card()
    print(f"    Card ID: {card['card_id']}")
    print(f"    Values: {card['values']['declared']}")
    print(f"    Bounded actions: {card['autonomy']['bounded_actions']}")
    print(f"    Forbidden actions: {card['autonomy']['forbidden_actions']}")

    # Save the card
    with open("alignment-card.json", "w") as f:
        json.dump(card, f, indent=2)
    print("    Saved to: alignment-card.json")

    # Step 2: Make a compliant recommendation
    print("\n[2] Making a recommendation (compliant action)...")
    options = [
        {"id": "prod-A", "name": "Quality Product A", "score": 0.85},
        {"id": "prod-B", "name": "Sponsored Product B", "score": 0.90, "sponsored": True},
        {"id": "prod-C", "name": "Budget Product C", "score": 0.70},
    ]

    selected, trace = make_recommendation(card["card_id"], options)
    print(f"    Selected: {selected['name']} (id: {selected['id']})")
    print(f"    Reasoning: {trace['decision']['selection_reasoning']}")

    # Step 3: Verify the trace
    print("\n[3] Verifying trace against alignment card...")
    result = verify_trace(trace, card)
    print(f"    Verified: {result.verified}")
    print(f"    Violations: {len(result.violations)}")
    print(f"    Warnings: {len(result.warnings)}")

    if result.verified:
        print("    ✓ Trace is compliant with declared alignment")

    # Save the trace
    with open("trace-compliant.json", "w") as f:
        json.dump(trace, f, indent=2)
    print("    Saved to: trace-compliant.json")

    # Step 4: Attempt a forbidden action
    print("\n[4] Attempting forbidden action (for demonstration)...")
    bad_trace = make_forbidden_action(card["card_id"])
    print(f"    Action: {bad_trace['action']['name']}")

    # Step 5: Verify the bad trace
    print("\n[5] Verifying forbidden action trace...")
    bad_result = verify_trace(bad_trace, card)
    print(f"    Verified: {bad_result.verified}")
    print(f"    Violations: {len(bad_result.violations)}")

    for violation in bad_result.violations:
        print(f"    ✗ VIOLATION [{violation.severity.value}]: {violation.type.value}")
        print(f"      {violation.description}")

    # Save the bad trace
    with open("trace-violation.json", "w") as f:
        json.dump(bad_trace, f, indent=2)
    print("    Saved to: trace-violation.json")

    print("\n" + "=" * 60)
    print("Example complete. Generated files:")
    print("  - alignment-card.json (the agent's alignment declaration)")
    print("  - trace-compliant.json (a verified compliant trace)")
    print("  - trace-violation.json (a trace with violations)")
    print("=" * 60)


if __name__ == "__main__":
    main()
