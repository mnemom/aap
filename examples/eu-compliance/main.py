#!/usr/bin/env python3
"""EU AI Act Article 50 Compliance Example — AAP.

Demonstrates how to create an EU-compliant Alignment Card using the
compliance presets, generate a traced decision, verify it, and print
a compliance summary.

Run with: python main.py
"""

from datetime import datetime, timezone

from aap import (
    Action,
    AlignmentCard,
    Alternative,
    APTrace,
    Audit,
    Autonomy,
    Decision,
    Escalation,
    EscalationTrigger,
    Principal,
    Values,
    verify_trace,
)
from aap.compliance import (
    EU_COMPLIANCE_AUDIT,
    EU_COMPLIANCE_EXTENSIONS,
    EU_COMPLIANCE_VALUES,
)


def create_eu_compliant_card() -> dict:
    """Create an Alignment Card (unified / ADR-039) configured for EU AI Act compliance."""
    card = AlignmentCard(
        card_version="unified/2026-04-26",
        card_id="ac-eu-compliance-001",
        agent_id="eu-compliant-agent",
        issued_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        autonomy_mode="enforce",
        integrity_mode="enforce",
        principal=Principal(
            type="organization",
            identifier="Example Corp (EU)",
            relationship="delegated_authority",
            escalation_contact="compliance@example.com",
        ),
        values=Values(
            declared=list(EU_COMPLIANCE_VALUES),
            definitions={
                "transparency": {
                    "description": "All decisions are logged, auditable, and explainable to users",
                },
                "user_control": {
                    "description": "Users can request human review of any automated decision",
                },
            },
            conflicts_with=["deceptive_marketing", "data_exfiltration"],
            hierarchy="lexicographic",
        ),
        autonomy=Autonomy(
            bounded_actions=["search", "compare", "recommend", "summarize"],
            escalation_triggers=[
                EscalationTrigger(
                    condition='action_type == "purchase"',
                    action="escalate",
                    reason="Purchases require explicit human approval",
                ),
                EscalationTrigger(
                    condition="confidence < 0.6",
                    action="escalate",
                    reason="Low-confidence decisions require human review",
                ),
            ],
            forbidden_actions=["share_personal_data", "auto_subscribe", "delete_user_data"],
        ),
        audit=Audit(**EU_COMPLIANCE_AUDIT),
        extensions=EU_COMPLIANCE_EXTENSIONS,
    )
    return card.model_dump(mode="json")


def make_traced_recommendation(card_id: str) -> dict:
    """Generate a traced recommendation decision."""
    trace = APTrace(
        trace_id=f"tr-eu-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        agent_id="eu-compliant-agent",
        card_id=card_id,
        timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        action=Action(
            type="recommend",
            name="recommend",
            category="bounded",
        ),
        decision=Decision(
            alternatives_considered=[
                Alternative(
                    option_id="prod-A",
                    description="Eco-friendly Option A",
                    score=0.88,
                ),
                Alternative(
                    option_id="prod-B",
                    description="Budget Option B",
                    score=0.72,
                ),
                Alternative(
                    option_id="prod-C",
                    description="Sponsored Option C",
                    score=0.91,
                    flags=["sponsored_content"],
                ),
            ],
            selected="prod-A",
            selection_reasoning=(
                "Selected 'Eco-friendly Option A' (0.88). Sponsored Option C had a "
                "higher raw score (0.91) but was deprioritized per principal_benefit "
                "and transparency values. User interest takes precedence over vendor "
                "sponsorship."
            ),
            values_applied=["principal_benefit", "transparency", "honesty"],
            confidence=0.88,
        ),
        escalation=Escalation(
            evaluated=True,
            triggers_checked=[
                {"trigger": 'action_type == "purchase"', "matched": False},
                {"trigger": "confidence < 0.6", "matched": False},
            ],
            required=False,
            reason="Recommendation action with high confidence; no escalation needed",
        ),
    )
    return trace.model_dump(mode="json")


def print_compliance_summary(card: dict, result) -> None:
    """Print an Article 50 compliance summary."""
    print("\n" + "=" * 60)
    print("EU AI ACT ARTICLE 50 COMPLIANCE SUMMARY")
    print("=" * 60)

    eu = card.get("extensions", {}).get("eu_ai_act", {})

    print("\n  Art. 50(1) — User Disclosure:")
    print(f"    Agent ID:       {card['agent_id']}")
    print(f"    Principal:      {card['principal']['identifier']}")
    print(f"    Disclosure:     {eu.get('disclosure_text', 'NOT SET')}")

    print("\n  Art. 50(2) — Machine-Readable Marking:")
    print(f"    Trace format:   {card['audit']['trace_format']}")
    print(f"    Card version:   {card['card_version']}")

    print("\n  Art. 50(3) — Decision Transparency:")
    print(f"    Verified:       {result.verified}")
    print(f"    Violations:     {len(result.violations)}")
    print(f"    Warnings:       {len(result.warnings)}")

    print("\n  Art. 50(4) — Audit Trail:")
    print(f"    Retention:      {card['audit']['retention_days']} days")
    print(f"    Queryable:      {card['audit']['queryable']}")
    print(f"    Tamper evidence:{card['audit']['tamper_evidence']}")

    print(f"\n  Classification:   {eu.get('ai_system_classification', 'NOT SET')}")
    print(f"  Compliance ver:   {eu.get('compliance_version', 'NOT SET')}")
    print(f"  Art. 50 compliant:{eu.get('article_50_compliant', False)}")
    print("=" * 60)


def main():
    print("=" * 60)
    print("AAP EU AI Act Article 50 Compliance Example")
    print("=" * 60)

    # Step 1: Create EU-compliant card using presets
    print("\n[1] Creating EU-compliant Alignment Card...")
    card = create_eu_compliant_card()
    print(f"    Card ID: {card['card_id']}")
    print(f"    Values: {card['values']['declared']}")
    print(f"    Retention: {card['audit']['retention_days']} days")
    print(f"    Tamper evidence: {card['audit']['tamper_evidence']}")
    print(f"    EU extensions: {list(card['extensions']['eu_ai_act'].keys())}")

    # Step 2: Generate a traced decision
    print("\n[2] Making traced recommendation...")
    trace = make_traced_recommendation(card["card_id"])
    print(f"    Trace ID: {trace['trace_id']}")
    print(f"    Selected: {trace['decision']['selected']}")
    print(f"    Reasoning: {trace['decision']['selection_reasoning'][:80]}...")

    # Step 3: Verify the trace
    print("\n[3] Verifying trace against alignment card...")
    result = verify_trace(trace, card)
    print(f"    Verified: {result.verified}")
    print(f"    Violations: {len(result.violations)}")

    if result.verified:
        print("    Trace is compliant with declared alignment")

    # Step 4: Print compliance summary
    print_compliance_summary(card, result)


if __name__ == "__main__":
    main()
