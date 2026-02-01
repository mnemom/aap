# Adding AAP to A2A Agents

This guide shows how to extend A2A Agent Cards with AAP alignment properties, enabling value coherence checks before agent-to-agent coordination.

## Overview

A2A (Agent-to-Agent) protocol defines Agent Cards for capability discovery and task negotiation. AAP extends these cards with an `alignment` block that declares:

- **Who the agent serves** (principal relationship)
- **What values guide decisions** (declared values)
- **What it can do autonomously** (autonomy envelope)
- **How decisions are audited** (trace commitment)

This extension enables agents to verify value coherence *before* delegating tasks, rather than discovering conflicts mid-execution.

## Prerequisites

```bash
pip install agent-alignment-protocol
```

## Step 1: Understand Your Current Agent Card

A standard A2A Agent Card declares capabilities:

```json
{
  "name": "shopping-assistant",
  "description": "Finds and compares products for users",
  "url": "https://shopping.example.com/agent",
  "version": "1.0.0",
  "capabilities": {
    "streaming": true,
    "pushNotifications": false,
    "stateTransitionHistory": true
  },
  "skills": [
    {
      "id": "product-search",
      "name": "Product Search",
      "description": "Search for products matching criteria",
      "inputSchema": {
        "type": "object",
        "properties": {
          "query": {"type": "string"},
          "maxPrice": {"type": "number"}
        }
      }
    },
    {
      "id": "compare-products",
      "name": "Compare Products",
      "description": "Compare features of multiple products"
    },
    {
      "id": "purchase",
      "name": "Purchase Product",
      "description": "Complete a purchase transaction"
    }
  ]
}
```

This tells other agents *what* your agent can do, but not *how* it makes decisions or *whose interests* it serves.

## Step 2: Add the Alignment Block

Extend your Agent Card with an `alignment` block:

```json
{
  "name": "shopping-assistant",
  "description": "Finds and compares products for users",
  "url": "https://shopping.example.com/agent",
  "version": "1.0.0",
  "capabilities": {
    "streaming": true,
    "pushNotifications": false,
    "stateTransitionHistory": true
  },
  "skills": [
    {"id": "product-search", "name": "Product Search", "...": "..."},
    {"id": "compare-products", "name": "Compare Products", "...": "..."},
    {"id": "purchase", "name": "Purchase Product", "...": "..."}
  ],

  "alignment": {
    "aap_version": "0.1.0",
    "card_id": "ac-shopping-assistant-001",
    "agent_id": "shopping-assistant",
    "issued_at": "2026-01-31T12:00:00Z",

    "principal": {
      "type": "human",
      "relationship": "delegated_authority"
    },

    "values": {
      "declared": ["principal_benefit", "transparency", "minimal_data"],
      "conflicts_with": ["deceptive_marketing", "hidden_fees", "dark_patterns"]
    },

    "autonomy_envelope": {
      "bounded_actions": ["product-search", "compare-products"],
      "escalation_triggers": [
        {
          "condition": "skill_id == \"purchase\"",
          "action": "escalate",
          "reason": "Purchases require explicit user approval"
        },
        {
          "condition": "purchase_value > 100",
          "action": "escalate",
          "reason": "Exceeds autonomous spending limit"
        }
      ],
      "forbidden_actions": ["share_payment_info", "auto_subscribe"]
    },

    "audit_commitment": {
      "trace_format": "ap-trace-v1",
      "retention_days": 90,
      "queryable": true
    }
  }
}
```

### Key Mapping: A2A Skills to AAP Actions

Your A2A `skills` map to AAP `bounded_actions`:

| A2A Skill | AAP Treatment | Rationale |
|-----------|---------------|-----------|
| `product-search` | `bounded_actions` | Low risk, no state change |
| `compare-products` | `bounded_actions` | Low risk, no state change |
| `purchase` | `escalation_triggers` | Financial commitment, requires approval |

## Step 3: Serve the Alignment Card

AAP specifies that Alignment Cards SHOULD be served at a well-known URL:

```
GET https://shopping.example.com/.well-known/alignment-card.json
```

You can either:

**Option A: Embed in Agent Card** (recommended for A2A)
```json
{
  "name": "shopping-assistant",
  "alignment": { "...": "full alignment block" }
}
```

**Option B: Reference External Card**
```json
{
  "name": "shopping-assistant",
  "alignment": {
    "$ref": "https://shopping.example.com/.well-known/alignment-card.json"
  }
}
```

## Step 4: Implement Value Coherence Handshake

Before your agent delegates work to another agent, verify value coherence:

```python
from aap import check_coherence

def delegate_task(my_card: dict, their_agent_card: dict, task: dict):
    """Delegate a task to another agent after checking value coherence."""

    # Extract alignment blocks
    my_alignment = my_card.get("alignment", {})
    their_alignment = their_agent_card.get("alignment", {})

    if not their_alignment:
        # Other agent doesn't support AAP
        # Policy decision: proceed with caution or require AAP
        return handle_no_alignment(their_agent_card, task)

    # Check coherence
    result = check_coherence(my_alignment, their_alignment)

    if result.compatible:
        # Values are compatible, proceed
        return execute_delegation(their_agent_card, task)

    # Handle conflicts
    for conflict in result.value_alignment.conflicts:
        print(f"Value conflict: {conflict.description}")

    if result.proceed:
        # Minor conflicts, can proceed with logging
        return execute_delegation(their_agent_card, task, log_conflicts=True)
    else:
        # Significant conflicts, escalate to principal
        return escalate_to_principal(
            task=task,
            conflicts=result.value_alignment.conflicts,
            recommendation=result.proposed_resolution
        )
```

## Step 5: Generate AP-Traces for A2A Actions

When your agent performs actions (especially across agent boundaries), produce AP-Traces:

```python
from aap import APTrace, Action, Decision, Alternative, Escalation
from datetime import datetime, timezone
import uuid

def search_products_with_trace(card_id: str, query: str, preferences: dict):
    """A2A skill implementation with AAP tracing."""

    # Your existing search logic
    results = perform_search(query, preferences)

    # Build trace for this decision
    trace = APTrace(
        trace_id=f"tr-{uuid.uuid4().hex[:12]}",
        agent_id="shopping-assistant",
        card_id=card_id,
        timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),

        action=Action(
            type="search",
            name="product-search",  # Matches A2A skill ID
            category="bounded",
        ),

        decision=Decision(
            alternatives_considered=[
                Alternative(
                    option_id=r["id"],
                    description=r["name"],
                    score=r["relevance_score"],
                    flags=["sponsored"] if r.get("sponsored") else [],
                )
                for r in results[:5]
            ],
            selected=results[0]["id"] if results else None,
            selection_reasoning=build_reasoning(results, preferences),
            values_applied=["principal_benefit", "transparency"],
        ),

        escalation=Escalation(
            evaluated=True,
            triggers_checked=[
                {"trigger": "skill_id == \"purchase\"", "matched": False},
            ],
            required=False,
            reason="Search action within autonomy envelope",
        ),
    )

    # Store trace for audit
    store_trace(trace.model_dump(mode="json"))

    return results
```

## Step 6: Handle Incoming Coherence Checks

When another agent requests your alignment card or initiates a coherence check:

```python
from flask import Flask, jsonify, request
from aap import check_coherence

app = Flask(__name__)

# Serve alignment card at well-known URL
@app.route("/.well-known/alignment-card.json")
def alignment_card():
    return jsonify(load_alignment_card())

# Handle coherence check requests
@app.route("/aap/coherence-check", methods=["POST"])
def coherence_check():
    """Respond to value coherence handshake."""
    their_card = request.json.get("initiator_alignment")
    my_card = load_alignment_card()

    result = check_coherence(their_card, my_card)

    return jsonify({
        "compatible": result.compatible,
        "score": result.score,
        "proceed": result.proceed,
        "matched_values": result.value_alignment.matched,
        "conflicts": [
            {"description": c.description, "severity": c.severity}
            for c in result.value_alignment.conflicts
        ],
    })
```

## Complete Example: Two Agents Coordinating

Here's a complete flow with a user agent delegating to a vendor agent:

```python
# user_agent.py
from aap import check_coherence

USER_AGENT_CARD = {
    "name": "user-shopping-agent",
    "alignment": {
        "aap_version": "0.1.0",
        "card_id": "ac-user-agent-001",
        "agent_id": "user-shopping-agent",
        "issued_at": "2026-01-31T12:00:00Z",
        "principal": {"type": "human", "relationship": "delegated_authority"},
        "values": {
            "declared": ["principal_benefit", "transparency", "minimal_data"],
            "conflicts_with": ["deceptive_marketing", "hidden_fees"],
        },
        "autonomy_envelope": {
            "bounded_actions": ["search", "compare", "recommend"],
            "escalation_triggers": [
                {"condition": "action == \"purchase\"", "action": "escalate", "reason": "Requires approval"}
            ],
            "forbidden_actions": ["share_payment_info"],
        },
        "audit_commitment": {"trace_format": "ap-trace-v1", "retention_days": 30, "queryable": True},
    }
}

VENDOR_AGENT_CARD = {
    "name": "vendor-deals-agent",
    "alignment": {
        "aap_version": "0.1.0",
        "card_id": "ac-vendor-agent-001",
        "agent_id": "vendor-deals-agent",
        "issued_at": "2026-01-31T12:00:00Z",
        "principal": {"type": "organization", "relationship": "delegated_authority"},
        "values": {
            "declared": ["customer_satisfaction", "transparency", "upselling"],
            "conflicts_with": [],
        },
        "autonomy_envelope": {
            "bounded_actions": ["search", "recommend", "apply_discount"],
            "escalation_triggers": [],
            "forbidden_actions": [],
        },
        "audit_commitment": {"trace_format": "ap-trace-v1", "retention_days": 90, "queryable": True},
    }
}

def coordinate_with_vendor():
    """Attempt to coordinate with vendor agent."""

    result = check_coherence(
        USER_AGENT_CARD["alignment"],
        VENDOR_AGENT_CARD["alignment"]
    )

    print(f"Compatible: {result.compatible}")
    print(f"Score: {result.score:.2f}")
    print(f"Matched values: {result.value_alignment.matched}")

    if result.value_alignment.conflicts:
        print("Conflicts detected:")
        for conflict in result.value_alignment.conflicts:
            print(f"  - {conflict.description}")

    if result.proceed:
        print("Proceeding with coordination (minor conflicts logged)")
    else:
        print("Escalating to principal for approval")

    return result

# Run
if __name__ == "__main__":
    coordinate_with_vendor()

# Output:
# Compatible: False
# Score: 0.42
# Matched values: ['transparency']
# Conflicts detected:
#   - Responder's 'upselling' may conflict with initiator's 'principal_benefit'
# Escalating to principal for approval
```

## Migration Checklist

- [ ] Audit your current A2A Agent Card
- [ ] Identify which skills are bounded vs. require escalation
- [ ] Define your principal relationship
- [ ] Declare your operational values
- [ ] Add forbidden actions (things you'll never do)
- [ ] Add the `alignment` block to your Agent Card
- [ ] Serve alignment card at `/.well-known/alignment-card.json`
- [ ] Implement coherence check endpoint
- [ ] Add AP-Trace generation to skill implementations
- [ ] Test with `verify_trace()` before deployment
- [ ] Implement handling for non-AAP agents (graceful degradation)

## Handling Non-AAP Agents

Not all agents will support AAP. Define your policy:

```python
def delegate_with_fallback(my_card: dict, their_card: dict, task: dict):
    """Handle delegation to agents with or without AAP support."""

    their_alignment = their_card.get("alignment")

    if their_alignment:
        # Full AAP flow
        result = check_coherence(my_card["alignment"], their_alignment)
        if not result.proceed:
            return escalate_to_principal(task, result.value_alignment.conflicts)
        return execute_delegation(their_card, task)

    # No AAP support - apply fallback policy
    if is_trusted_agent(their_card):
        # Known agent, proceed with logging
        return execute_delegation(their_card, task, log_no_aap=True)

    if task_is_low_risk(task):
        # Low-risk task, proceed with caution
        return execute_delegation(their_card, task, log_no_aap=True)

    # High-risk task with unknown agent - escalate
    return escalate_to_principal(
        task,
        reason="Target agent does not support AAP alignment verification"
    )
```

## Standard Value Identifiers

Use these standard identifiers where applicable:

| Identifier | Description |
|------------|-------------|
| `principal_benefit` | Prioritize principal's interests |
| `transparency` | Disclose reasoning and limitations |
| `minimal_data` | Collect only necessary information |
| `harm_prevention` | Avoid actions causing harm |
| `honesty` | Do not deceive or mislead |
| `user_control` | Respect user autonomy and consent |
| `privacy` | Protect personal information |
| `fairness` | Avoid discriminatory outcomes |

Custom values MUST be defined in the `definitions` block of your alignment card.

## What's Next?

- **[QUICKSTART.md](QUICKSTART.md)** — Core AAP concepts and API
- **[SPEC.md](SPEC.md)** — Full protocol specification
- **[LIMITS.md](LIMITS.md)** — What AAP can and cannot guarantee
- **[examples/a2a-integration/](../examples/a2a-integration/)** — Working example code

---

*Questions? See the [full specification](SPEC.md) or check the [examples](../examples/).*
