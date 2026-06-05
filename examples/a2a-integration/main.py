#!/usr/bin/env python3
"""A2A + AAP Integration Example — Two agents coordinating with value coherence.

This example demonstrates:
1. Creating A2A Agent Cards extended with AAP alignment blocks
2. Performing value coherence checks before delegation
3. Handling value conflicts appropriately
4. Generating AP-Traces for cross-agent actions

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
    Values,
    check_coherence,
    # Verification API
    verify_trace,
)


def create_user_agent_card() -> dict:
    """Create an A2A Agent Card for a user's shopping assistant.

    This agent prioritizes the user's interests and is cautious about
    coordinating with vendor agents that may have conflicting incentives.
    """
    # Build the AAP alignment block
    alignment = AlignmentCard(
        card_version="unified/2026-04-26",
        card_id="ac-user-shopping-001",
        agent_id="user-shopping-assistant",
        issued_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        principal=Principal(
            type="human",
            identifier="did:web:example.com",
            relationship="delegated_authority",
        ),
        values=Values(
            declared=["principal_benefit", "transparency", "minimal_data", "honesty"],
            conflicts_with=["deceptive_marketing", "hidden_fees", "upselling"],
        ),
        autonomy=Autonomy(
            bounded_actions=["search", "compare", "recommend", "add_to_cart", "vendor-coordination"],
            escalation_triggers=[
                {
                    "condition": "action_type == \"purchase\"",
                    "action": "escalate",
                    "reason": "Purchases require explicit user approval",
                },
            ],
            forbidden_actions=["share_payment_info", "auto_subscribe", "share_browsing_history"],
        ),
        audit=Audit(
            trace_format="ap-trace-v1",
            retention_days=30,
            queryable=True,
            query_endpoint="https://user-agent.example.com/api/traces",
        ),
    )

    # Combine into A2A Agent Card format
    return {
        "name": "user-shopping-assistant",
        "description": "Personal shopping assistant that finds and compares products",
        "url": "https://user-agent.example.com",
        "version": "1.0.0",
        "capabilities": {
            "streaming": True,
            "pushNotifications": False,
            "stateTransitionHistory": True,
        },
        "skills": [
            {
                "id": "product-search",
                "name": "Product Search",
                "description": "Search for products matching user criteria",
            },
            {
                "id": "compare-products",
                "name": "Compare Products",
                "description": "Compare features and prices of products",
            },
            {
                "id": "get-recommendations",
                "name": "Get Recommendations",
                "description": "Get personalized product recommendations",
            },
        ],
        "alignment": alignment.model_dump(mode="json"),
    }


def create_vendor_agent_card() -> dict:
    """Create an A2A Agent Card for a vendor's deals agent.

    This agent serves the vendor's interests, which may include upselling.
    This creates a potential conflict with user agents.
    """
    alignment = AlignmentCard(
        card_version="unified/2026-04-26",
        card_id="ac-vendor-deals-001",
        agent_id="vendor-deals-agent",
        issued_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        principal=Principal(
            type="organization",
            identifier="did:web:example.com",
            relationship="delegated_authority",
        ),
        values=Values(
            declared=["customer_satisfaction", "transparency", "upselling", "conversion"],
            conflicts_with=["price_undercutting"],
        ),
        autonomy=Autonomy(
            bounded_actions=["search", "recommend", "apply_discount", "suggest_bundle"],
            escalation_triggers=[
                {
                    "condition": "discount > 30",
                    "action": "escalate",
                    "reason": "Large discounts require manager approval",
                },
            ],
            forbidden_actions=["price_match_competitor"],
        ),
        audit=Audit(
            trace_format="ap-trace-v1",
            retention_days=90,
            queryable=True,
            query_endpoint="https://vendor.example.com/api/traces",
        ),
    )

    return {
        "name": "vendor-deals-agent",
        "description": "Vendor agent that finds deals and suggests products",
        "url": "https://vendor.example.com/agent",
        "version": "1.0.0",
        "capabilities": {
            "streaming": True,
            "pushNotifications": True,
            "stateTransitionHistory": False,
        },
        "skills": [
            {
                "id": "find-deals",
                "name": "Find Deals",
                "description": "Find current deals and promotions",
            },
            {
                "id": "suggest-products",
                "name": "Suggest Products",
                "description": "Suggest products based on browsing history",
            },
            {
                "id": "apply-coupon",
                "name": "Apply Coupon",
                "description": "Apply available coupons to cart",
            },
        ],
        "alignment": alignment.model_dump(mode="json"),
    }


def create_compatible_vendor_card() -> dict:
    """Create a vendor agent with values compatible with user agents.

    This vendor agent does NOT have upselling as a value, making it
    compatible with user agents that conflict with upselling.
    """
    alignment = AlignmentCard(
        card_version="unified/2026-04-26",
        card_id="ac-ethical-vendor-001",
        agent_id="ethical-vendor-agent",
        issued_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        principal=Principal(
            type="organization",
            identifier="did:web:example.com",
            relationship="delegated_authority",
        ),
        values=Values(
            declared=["principal_benefit", "transparency", "honesty", "minimal_data"],
            conflicts_with=["deceptive_marketing", "hidden_fees", "upselling"],
        ),
        autonomy=Autonomy(
            bounded_actions=["search", "recommend", "apply_discount"],
            escalation_triggers=[],
            forbidden_actions=["upsell_unrelated", "hide_cheaper_options"],
        ),
        audit=Audit(
            trace_format="ap-trace-v1",
            retention_days=90,
            queryable=True,
            query_endpoint="https://ethical-vendor.example.com/api/traces",
        ),
    )

    return {
        "name": "ethical-vendor-agent",
        "description": "Vendor agent focused on customer satisfaction without aggressive upselling",
        "url": "https://ethical-vendor.example.com/agent",
        "version": "1.0.0",
        "capabilities": {
            "streaming": True,
            "pushNotifications": False,
            "stateTransitionHistory": True,
        },
        "skills": [
            {
                "id": "find-best-value",
                "name": "Find Best Value",
                "description": "Find products with best value for customer needs",
            },
            {
                "id": "honest-compare",
                "name": "Honest Compare",
                "description": "Compare products including competitor options",
            },
        ],
        "alignment": alignment.model_dump(mode="json"),
    }


def perform_coherence_check(my_card: dict, their_card: dict) -> dict:
    """Perform value coherence check between two agents.

    Returns the coherence result with detailed conflict information.
    """
    my_alignment = my_card.get("alignment", {})
    their_alignment = their_card.get("alignment", {})

    result = check_coherence(my_alignment, their_alignment)

    return {
        "compatible": result.compatible,
        "score": result.score,
        "proceed": result.proceed,
        "matched_values": result.value_alignment.matched,
        "conflicts": [
            {
                "description": c.description,
                "conflict_type": c.conflict_type,
            }
            for c in result.value_alignment.conflicts
        ],
        "proposed_resolution": result.proposed_resolution,
    }


def create_delegation_trace(
    card_id: str,
    target_agent: str,
    coherence_result: dict,
    action_taken: str,
) -> dict:
    """Create an AP-Trace for a delegation decision.

    This trace records the decision to delegate (or not delegate)
    to another agent after a coherence check.
    """
    trace = APTrace(
        trace_id=f"tr-delegation-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        agent_id="user-shopping-assistant",
        card_id=card_id,
        timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        action=Action(
            type="escalate" if not coherence_result["proceed"] else "execute",
            name="vendor-coordination",
            category="escalation_trigger" if not coherence_result["proceed"] else "bounded",
        ),
        decision=Decision(
            alternatives_considered=[
                Alternative(
                    option_id="delegate",
                    description=f"Delegate to {target_agent}",
                    score=coherence_result["score"],
                    flags=["value_conflict"] if coherence_result["conflicts"] else [],
                ),
                Alternative(
                    option_id="reject",
                    description="Do not delegate, handle internally",
                    score=1.0 - coherence_result["score"],
                ),
            ],
            selected=action_taken,
            selection_reasoning=(
                f"Coherence check with {target_agent}: score={coherence_result['score']:.2f}, "
                f"compatible={coherence_result['compatible']}. "
                + (f"Conflicts: {[c['description'] for c in coherence_result['conflicts']]}"
                   if coherence_result["conflicts"] else "No conflicts detected.")
            ),
            values_applied=["principal_benefit", "transparency"],
            confidence=coherence_result["score"] if action_taken == "delegate" else 1.0 - coherence_result["score"],
        ),
        escalation=Escalation(
            evaluated=True,
            triggers_checked=[
                {"trigger": "delegate_to_vendor", "matched": True},
            ],
            required=not coherence_result["proceed"],
            reason=(
                "Escalated to principal due to value conflicts"
                if not coherence_result["proceed"]
                else "Coherence check passed, delegation within envelope"
            ),
        ),
    )

    return trace.model_dump(mode="json")


def main():
    print("=" * 70)
    print("A2A + AAP Integration Example")
    print("=" * 70)

    # Step 1: Create agent cards
    print("\n[1] Creating A2A Agent Cards with AAP alignment blocks...")

    user_card = create_user_agent_card()
    print(f"    User Agent: {user_card['name']}")
    print(f"    Values: {user_card['alignment']['values']['declared']}")
    print(f"    Conflicts with: {user_card['alignment']['values']['conflicts_with']}")

    vendor_card = create_vendor_agent_card()
    print(f"\n    Vendor Agent: {vendor_card['name']}")
    print(f"    Values: {vendor_card['alignment']['values']['declared']}")

    compatible_vendor = create_compatible_vendor_card()
    print(f"\n    Ethical Vendor: {compatible_vendor['name']}")
    print(f"    Values: {compatible_vendor['alignment']['values']['declared']}")

    # Save cards
    with open("user-agent-card.json", "w") as f:
        json.dump(user_card, f, indent=2)
    with open("vendor-agent-card.json", "w") as f:
        json.dump(vendor_card, f, indent=2)
    with open("compatible-vendor-card.json", "w") as f:
        json.dump(compatible_vendor, f, indent=2)
    print("\n    Saved: user-agent-card.json, vendor-agent-card.json, compatible-vendor-card.json")

    # Step 2: Check coherence with vendor agent (should fail)
    print("\n[2] Checking value coherence with vendor agent...")
    vendor_result = perform_coherence_check(user_card, vendor_card)

    print(f"    Compatible: {vendor_result['compatible']}")
    print(f"    Score: {vendor_result['score']:.2f}")
    print(f"    Matched values: {vendor_result['matched_values']}")

    if vendor_result["conflicts"]:
        print("    Conflicts:")
        for conflict in vendor_result["conflicts"]:
            print(f"      - [{conflict['conflict_type']}] {conflict['description']}")

    print(f"    Proceed: {vendor_result['proceed']}")

    if not vendor_result["proceed"]:
        print("    --> ESCALATION REQUIRED: Cannot delegate to this vendor")

    # Step 3: Generate trace for the failed delegation
    print("\n[3] Recording delegation decision (rejected due to conflicts)...")
    vendor_trace = create_delegation_trace(
        card_id=user_card["alignment"]["card_id"],
        target_agent=vendor_card["name"],
        coherence_result=vendor_result,
        action_taken="reject",
    )

    # Verify the trace
    verify_result = verify_trace(vendor_trace, user_card["alignment"])
    print(f"    Trace verified: {verify_result.verified}")
    print(f"    Action recorded: {vendor_trace['action']['name']}")
    print(f"    Decision: {vendor_trace['decision']['selected']}")

    with open("delegation-rejected-trace.json", "w") as f:
        json.dump(vendor_trace, f, indent=2)
    print("    Saved: delegation-rejected-trace.json")

    # Step 4: Check coherence with compatible vendor (should pass)
    print("\n[4] Checking value coherence with ethical vendor...")
    compatible_result = perform_coherence_check(user_card, compatible_vendor)

    print(f"    Compatible: {compatible_result['compatible']}")
    print(f"    Score: {compatible_result['score']:.2f}")
    print(f"    Matched values: {compatible_result['matched_values']}")

    if compatible_result["conflicts"]:
        print("    Conflicts:")
        for conflict in compatible_result["conflicts"]:
            print(f"      - [{conflict['conflict_type']}] {conflict['description']}")
    else:
        print("    Conflicts: None")

    print(f"    Proceed: {compatible_result['proceed']}")

    if compatible_result["proceed"]:
        print("    --> DELEGATION APPROVED: Values are compatible")

    # Step 5: Generate trace for the approved delegation
    print("\n[5] Recording delegation decision (approved)...")
    approved_trace = create_delegation_trace(
        card_id=user_card["alignment"]["card_id"],
        target_agent=compatible_vendor["name"],
        coherence_result=compatible_result,
        action_taken="delegate",
    )

    # Verify the trace
    verify_result = verify_trace(approved_trace, user_card["alignment"])
    print(f"    Trace verified: {verify_result.verified}")
    print(f"    Action recorded: {approved_trace['action']['name']}")
    print(f"    Decision: {approved_trace['decision']['selected']}")

    with open("delegation-approved-trace.json", "w") as f:
        json.dump(approved_trace, f, indent=2)
    print("    Saved: delegation-approved-trace.json")

    # Step 6: Summary
    print("\n" + "=" * 70)
    print("Summary: A2A Coordination with AAP Value Coherence")
    print("=" * 70)
    print(f"""
    User agent attempted to coordinate with two vendor agents:

    1. Vendor Deals Agent:
       - Has 'upselling' in declared values
       - User agent has 'upselling' in conflicts_with
       - Result: INCOMPATIBLE (score: {vendor_result['score']:.2f})
       - Action: Delegation rejected, escalated to principal

    2. Ethical Vendor Agent:
       - Shares user-aligned values (principal_benefit, transparency, honesty)
       - Also conflicts with upselling, hidden_fees, deceptive_marketing
       - Result: COMPATIBLE (score: {compatible_result['score']:.2f})
       - Action: Delegation approved

    This demonstrates how AAP enables agents to verify value alignment
    BEFORE delegating tasks, preventing mid-execution conflicts.
    """)

    print("Generated files:")
    print("  - user-agent-card.json (A2A + AAP user agent)")
    print("  - vendor-agent-card.json (A2A + AAP vendor with conflicts)")
    print("  - compatible-vendor-card.json (A2A + AAP compatible vendor)")
    print("  - delegation-rejected-trace.json (trace of rejected delegation)")
    print("  - delegation-approved-trace.json (trace of approved delegation)")
    print("=" * 70)


if __name__ == "__main__":
    main()
