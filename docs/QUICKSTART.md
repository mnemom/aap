# Quick Start Guide

Get your agent producing verifiable alignment traces in 5 minutes.

## Installation

```bash
pip install agent-alignment-protocol
```

## Step 1: Define Your Alignment Card

An Alignment Card declares what your agent is, what values it holds, and what it will and won't do autonomously.

```python
from aap import AlignmentCard, Principal, Values, AutonomyEnvelope, AuditCommitment

# Build the card programmatically
card = AlignmentCard(
    aap_version="0.1.0",
    card_id="ac-my-shopping-agent-001",
    agent_id="shopping-assistant",
    issued_at="2026-01-31T12:00:00Z",

    principal=Principal(
        type="human",
        relationship="delegated_authority",
    ),

    values=Values(
        declared=["principal_benefit", "transparency", "minimal_data"],
        conflicts_with=["deceptive_marketing", "hidden_fees"],
    ),

    autonomy_envelope=AutonomyEnvelope(
        bounded_actions=["search", "compare", "recommend", "add_to_cart"],
        escalation_triggers=[
            {"condition": "action_type == \"purchase\"", "action": "escalate", "reason": "Purchases require approval"},
            {"condition": "purchase_value > 100", "action": "escalate", "reason": "Exceeds spending limit"},
        ],
        forbidden_actions=["share_credentials", "subscribe_to_services"],
    ),

    audit_commitment=AuditCommitment(
        trace_format="ap-trace-v1",
        retention_days=90,
        queryable=True,
    ),
)

# Export to dict for verification
card_dict = card.model_dump()

# Or save to JSON file
import json
with open("alignment-card.json", "w") as f:
    json.dump(card_dict, f, indent=2)
```

## Step 2: Generate AP-Traces for Decisions

Every significant decision your agent makes should produce a trace.

```python
from aap import APTrace, Action, Decision, Alternative, Escalation
from datetime import datetime
import uuid

def make_recommendation(user_preferences, products):
    """Example agent function that produces a traced decision."""

    # Your agent's decision logic
    scored_products = score_products(products, user_preferences)

    # Build the trace
    trace = APTrace(
        trace_id=f"tr-{uuid.uuid4().hex[:12]}",
        agent_id="shopping-assistant",
        card_id="ac-my-shopping-agent-001",  # Must match your card
        timestamp=datetime.utcnow().isoformat() + "Z",

        action=Action(
            type="recommend",
            name="product_recommendation",
            category="bounded",  # This action is within our autonomy envelope
        ),

        decision=Decision(
            alternatives_considered=[
                Alternative(
                    option_id=p["id"],
                    description=p["name"],
                    score=p["score"],
                    scoring_factors={"preference_match": p["match"], "price_value": p["value"]},
                    flags=["sponsored_content"] if p.get("sponsored") else [],
                )
                for p in scored_products[:3]  # Log top 3 considered
            ],
            selected=scored_products[0]["id"],
            selection_reasoning=f"Highest preference match. " +
                (f"Sponsored options deprioritized per principal_benefit value."
                 if any(p.get("sponsored") for p in scored_products[:3]) else ""),
            values_applied=["principal_benefit", "transparency"],
            confidence=scored_products[0]["score"],
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

    # Return both the recommendation and the trace
    return scored_products[0], trace.model_dump()
```

## Step 3: Verify Traces Against Your Card

Check that your agent's behavior matches its declared alignment.

```python
from aap import verify_trace

# Verify a single trace
result = verify_trace(trace_dict, card_dict)

print(f"Verified: {result.verified}")
print(f"Similarity: {result.similarity_score:.2f}")

if not result.verified:
    for violation in result.violations:
        print(f"VIOLATION [{violation.severity}]: {violation.type}")
        print(f"  {violation.description}")

for warning in result.warnings:
    print(f"WARNING: {warning.type}")
    print(f"  {warning.description}")

# Example output for a compliant trace:
# Verified: True
# Similarity: 0.82
#
# Example output for a low-similarity trace (structural pass, behavioral warning):
# Verified: True
# Similarity: 0.38
# WARNING: low_behavioral_similarity
#   Trace passes structural checks but behavioral similarity (0.38) is below threshold (0.5)
#
# Example output for a violation:
# Verified: False
# Similarity: 0.15
# VIOLATION [HIGH]: unbounded_action
#   Action 'delete_account' not in bounded_actions: ['search', 'compare', 'recommend', 'add_to_cart']
```

**Similarity scoring:** The `similarity_score` (0.0-1.0) measures how semantically similar the trace's behavior is to the declared alignment. A trace can pass all structural checks but still receive a `low_behavioral_similarity` warning if `similarity_score < 0.50`.

## Step 4: Check Coherence Before Agent Coordination

Before your agent works with another agent, verify their values are compatible.

```python
from aap import check_coherence

# Another agent's card (received via handshake)
their_card = {
    "card_id": "ac-vendor-agent",
    "values": {
        "declared": ["customer_satisfaction", "transparency", "upselling"],
        "conflicts_with": ["price_comparison"],
    },
    # ... other fields
}

# Check coherence
result = check_coherence(card_dict, their_card)

print(f"Compatible: {result.compatible}")
print(f"Coherence score: {result.score}")
print(f"Matched values: {result.value_alignment.matched}")
print(f"Conflicts: {[c.description for c in result.value_alignment.conflicts]}")

if result.proceed:
    # Safe to coordinate
    coordinate_with_agent(their_card)
else:
    # Handle the conflict
    if result.proposed_resolution:
        print(f"Suggested resolution: {result.proposed_resolution}")
    # Escalate to human
    escalate_to_principal(result.value_alignment.conflicts)

# Example output:
# Compatible: False
# Coherence score: 0.4
# Matched values: ['transparency']
# Conflicts: ["Responder's 'upselling' may conflict with initiator's 'principal_benefit'"]
```

## Step 5: Detect Drift Over Time

Monitor your agent for behavioral drift from its declared alignment.

```python
from aap import detect_drift

# Collect traces over time
traces = [trace1, trace2, trace3, ...]  # List of trace dicts

# Check for drift
alerts = detect_drift(card_dict, traces)

for alert in alerts:
    print(f"DRIFT DETECTED for agent {alert.agent_id}")
    print(f"  Direction: {alert.analysis.drift_direction}")
    print(f"  Similarity score: {alert.analysis.similarity_score}")
    print(f"  Sustained for {alert.analysis.sustained_traces} traces")

    for indicator in alert.analysis.specific_indicators:
        print(f"  Indicator: {indicator.indicator}")
        print(f"    Baseline: {indicator.baseline} → Current: {indicator.current}")

# Example output:
# DRIFT DETECTED for agent shopping-assistant
#   Direction: autonomy_expansion
#   Similarity score: 0.25
#   Sustained for 4 traces
#   Indicator: escalation_rate_change
#     Baseline: 0.15 → Current: 0.03
```

## Complete Working Example

Here's a minimal but complete example you can run:

```python
from aap import (
    AlignmentCard, Principal, Values, AutonomyEnvelope, AuditCommitment,
    APTrace, Action, Decision, Alternative, Escalation,
    verify_trace, check_coherence, detect_drift,
)

# 1. Create alignment card
card = AlignmentCard(
    aap_version="0.1.0",
    card_id="ac-demo-001",
    agent_id="demo-agent",
    issued_at="2026-01-31T12:00:00Z",
    principal=Principal(type="human", relationship="delegated_authority"),
    values=Values(declared=["principal_benefit", "transparency"]),
    autonomy_envelope=AutonomyEnvelope(
        bounded_actions=["search", "recommend"],
        escalation_triggers=[],
        forbidden_actions=["delete"],
    ),
    audit_commitment=AuditCommitment(
        trace_format="ap-trace-v1",
        retention_days=30,
        queryable=False,
    ),
)
card_dict = card.model_dump()

# 2. Create a trace
trace = APTrace(
    trace_id="tr-demo-001",
    agent_id="demo-agent",
    card_id="ac-demo-001",
    timestamp="2026-01-31T12:30:00Z",
    action=Action(type="recommend", name="recommend", category="bounded"),
    decision=Decision(
        alternatives_considered=[
            Alternative(option_id="A", description="Option A", score=0.9),
            Alternative(option_id="B", description="Option B", score=0.7),
        ],
        selected="A",
        selection_reasoning="Highest score",
        values_applied=["principal_benefit"],
    ),
    escalation=Escalation(evaluated=True, required=False),
)
trace_dict = trace.model_dump()

# 3. Verify
result = verify_trace(trace_dict, card_dict)
print(f"Trace verified: {result.verified}")
print(f"Similarity score: {result.similarity_score:.2f}")
print(f"Violations: {len(result.violations)}")
print(f"Warnings: {len(result.warnings)}")

# Output:
# Trace verified: True
# Similarity score: 0.71
# Violations: 0
# Warnings: 0
```

## What's Next?

- **[Interactive Playground](playground/)** — Try verification in your browser with SSM visualization
- **[SPEC.md](SPEC.md)** — Full protocol specification for implementers
- **[LIMITS.md](LIMITS.md)** — What AAP can and cannot guarantee (read this)
- **[CALIBRATION.md](CALIBRATION.md)** — How similarity thresholds were derived
- **[a2a-migration.md](a2a-migration.md)** — Adding AAP to existing A2A agents
- **[mcp-migration.md](mcp-migration.md)** — Adding alignment to MCP tools
- **[Examples](../examples/)** — Complete working examples

## Common Patterns

### Decorator for Automatic Tracing

AAP provides built-in decorators for automatic trace generation:

```python
from aap import trace_decision, TracedResult

# Basic usage — traces are written to ./traces/ by default
@trace_decision(card_path="alignment-card.json")
def search_products(query: str) -> list:
    """Function automatically generates AP-Trace on each call."""
    results = find_products(query)
    return results

# Rich tracing with TracedResult — capture reasoning and alternatives
@trace_decision(card_path="alignment-card.json")
def recommend_product(query: str) -> TracedResult:
    """Return TracedResult for detailed decision metadata."""
    products = find_products(query)
    best = products[0]

    return TracedResult(
        result=best,
        alternatives=[
            {"option_id": p["id"], "score": p["score"]}
            for p in products[:3]
        ],
        reasoning=f"Selected {best['name']} with highest score",
        values_applied=["principal_benefit", "transparency"],
        confidence=best["score"],
    )

# MCP tool tracing
from aap import mcp_traced

@mcp_traced(card_path="alignment-card.json")
def my_mcp_tool(params: dict) -> dict:
    """MCP tool with automatic alignment tracing."""
    return {"status": "success"}
```

### Batch Verification

```python
def verify_session(card_dict: dict, traces: list[dict]) -> dict:
    """Verify all traces from a session and summarize results."""
    results = [verify_trace(t, card_dict) for t in traces]

    similarities = [r.similarity_score for r in results]

    return {
        "total": len(results),
        "verified": sum(1 for r in results if r.verified),
        "violations": sum(len(r.violations) for r in results),
        "warnings": sum(len(r.warnings) for r in results),
        "violation_types": list(set(
            v.type for r in results for v in r.violations
        )),
        # Similarity statistics
        "mean_similarity": sum(similarities) / len(similarities) if similarities else 0,
        "min_similarity": min(similarities) if similarities else 0,
        "low_similarity_count": sum(1 for s in similarities if s < 0.50),
    }
```

---

*Questions? See the [full specification](SPEC.md) or check out the [examples](../examples/).*
