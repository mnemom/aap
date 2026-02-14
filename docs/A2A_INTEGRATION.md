# A2A Integration Guide

> **Time to integrate: ~10 minutes.** This guide shows how to extend A2A Agent Cards with AAP alignment properties, enabling value coherence checks before agent-to-agent coordination. Examples in both Python and TypeScript.

## Overview

A2A (Agent-to-Agent) protocol defines Agent Cards for capability discovery and task negotiation. AAP extends these cards with an `alignment` block that declares:

- **Who the agent serves** (principal relationship)
- **What values guide decisions** (declared values and conflicts)
- **What it can do autonomously** (autonomy envelope)
- **How decisions are audited** (trace commitment)

This extension enables agents to verify value coherence *before* delegating tasks, rather than discovering conflicts mid-execution.

## Where A2A and AAP Fit

A2A and AAP are complementary protocols in the agentic AI stack, both part of the [Agentic AI Foundation (AAIF)](https://www.linuxfoundation.org/press/linux-foundation-announces-the-formation-of-the-agentic-ai-foundation):

```
┌───────────────────────────────────────────────────────────────┐
│                  Agentic AI Foundation (AAIF)                 │
├───────────────┬───────────────┬───────────────┬──────────────┤
│      MCP      │      A2A      │   AAP / AIP   │  AGENTS.md   │
│  Agent↔Tools  │  Agent↔Agent  │    Trust &     │   Project    │
│               │               │   Integrity    │  Guidance    │
├───────────────┼───────────────┼───────────────┼──────────────┤
│ "What tools   │ "What can we  │ "Should we     │ "How should  │
│  can I use?"  │  do together?"│  work together │  I behave    │
│               │               │  and can we    │  here?"      │
│               │               │  prove it?"    │              │
└───────────────┴───────────────┴───────────────┴──────────────┘
```

**MCP + A2A + AAP/AIP = the complete trust stack.** MCP connects agents to tools. A2A connects agents to each other. AAP verifies that coordinating agents share compatible values and produces auditable decision trails. AIP adds real-time integrity monitoring of agent reasoning.

## The Alignment Card as Superset of the A2A Agent Card

An A2A Agent Card tells other agents *what you can do*. An Alignment Card tells them *why you do it* and *whose interests you serve*.

| A2A Agent Card | AAP Alignment Card | What AAP Adds |
|---|---|---|
| `id`, `name` | `agent_id`, `card_id` | Stable identity for audit trails with issuance/expiry |
| `description` | `values.declared` | Machine-verifiable intent, not just prose |
| `skills` | `autonomy_envelope.bounded_actions` | Which skills are safe to execute autonomously |
| `capabilities` | `autonomy_envelope` | Escalation triggers, forbidden actions, spending limits |
| `securitySchemes` | *(complementary)* | A2A handles auth; AAP handles behavioral trust |
| `extensions` | `extensions.aap` | URI-based extension linking to alignment metadata |
| `signature` | `issued_at`, `expires_at` | Both support signed, time-bound artifacts |
| *(no equivalent)* | `principal` | Who the agent serves and their relationship |
| *(no equivalent)* | `values.conflicts_with` | Explicit declaration of incompatible values |
| *(no equivalent)* | `audit_commitment` | Trace format, retention, queryability guarantees |

The Alignment Card doesn't replace the A2A Agent Card — it extends it:

```
┌─────────────────────────────────────────────────┐
│              A2A Agent Card                      │
│  name, skills, capabilities, interfaces,         │
│  securitySchemes, extensions                     │
│                                                   │
│  ┌─────────────────────────────────────────────┐ │
│  │          AAP Alignment Block                │ │
│  │  principal, values, autonomy_envelope,      │ │
│  │  audit_commitment, extensions               │ │
│  └─────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

## Prerequisites

```bash
# Python
pip install agent-alignment-protocol

# TypeScript
npm install @mnemom/agent-alignment-protocol
```

## Step 1: Understand Your Current Agent Card

A standard A2A Agent Card (v0.3) declares capabilities:

```json
{
  "id": "shopping-assistant",
  "name": "shopping-assistant",
  "description": "Finds and compares products for users",
  "url": "https://shopping.example.com/agent",
  "version": "1.0.0",
  "provider": {
    "name": "Acme Corp",
    "contact": "support@acme.example.com"
  },
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
  ],
  "interfaces": [
    {"type": "json-rpc", "endpoint": "https://shopping.example.com/rpc"}
  ],
  "securitySchemes": {
    "oauth2": {
      "type": "oauth2",
      "flows": {
        "clientCredentials": {
          "tokenUrl": "https://auth.example.com/token",
          "scopes": {"agent:invoke": "Invoke agent skills"}
        }
      }
    }
  },
  "extensions": []
}
```

This tells other agents *what* your agent can do, but not *how* it makes decisions or *whose interests* it serves.

## Step 2: Add the Alignment Block

Extend your Agent Card with an `alignment` block and declare AAP support via the A2A extensions array:

```json
{
  "id": "shopping-assistant",
  "name": "shopping-assistant",
  "description": "Finds and compares products for users",
  "url": "https://shopping.example.com/agent",
  "version": "1.0.0",
  "provider": {
    "name": "Acme Corp",
    "contact": "support@acme.example.com"
  },
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
  "interfaces": [
    {"type": "json-rpc", "endpoint": "https://shopping.example.com/rpc"}
  ],
  "securitySchemes": {
    "oauth2": {"type": "oauth2", "...": "..."}
  },
  "extensions": [
    {
      "uri": "urn:aap:alignment-card",
      "version": "0.1.0",
      "required": false
    }
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

**Option C: A2A v0.3 Extensions** (declare support, serve separately)
```json
{
  "extensions": [
    {
      "uri": "urn:aap:alignment-card",
      "version": "0.1.0",
      "required": false
    }
  ]
}
```

With Option C, AAP-aware agents fetch the alignment card from the well-known URL. Non-AAP agents ignore the extension. Set `required: true` if you want to enforce that all coordinating agents must support AAP.

## Step 4: Implement Value Coherence Handshake

Before your agent delegates work to another agent, verify value coherence.

**Python:**

```python
from aap import check_coherence

def delegate_task(my_card: dict, their_agent_card: dict, task: dict):
    """Delegate a task to another agent after checking value coherence."""

    # Extract alignment blocks
    my_alignment = my_card.get("alignment", {})
    their_alignment = their_agent_card.get("alignment", {})

    if not their_alignment:
        # Other agent doesn't support AAP
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

**TypeScript:**

```typescript
import { checkCoherence } from '@mnemom/agent-alignment-protocol';
import type { AlignmentCard } from '@mnemom/agent-alignment-protocol';

interface A2AAgentCard {
  name: string;
  alignment?: AlignmentCard;
  [key: string]: unknown;
}

function delegateTask(myCard: A2AAgentCard, theirCard: A2AAgentCard, task: unknown) {
  const myAlignment = myCard.alignment;
  const theirAlignment = theirCard.alignment;

  if (!theirAlignment) {
    return handleNoAlignment(theirCard, task);
  }

  const result = checkCoherence(myAlignment, theirAlignment);

  if (result.compatible) {
    return executeDelegation(theirCard, task);
  }

  for (const conflict of result.value_alignment.conflicts) {
    console.log(`Value conflict: ${conflict.description}`);
  }

  if (result.proceed) {
    return executeDelegation(theirCard, task, { logConflicts: true });
  } else {
    return escalateToPrincipal({
      task,
      conflicts: result.value_alignment.conflicts,
      recommendation: result.proposed_resolution,
    });
  }
}
```

## Step 5: Generate AP-Traces for A2A Actions

When your agent performs actions (especially across agent boundaries), produce AP-Traces.

**Python:**

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

**TypeScript:**

```typescript
import { verifyTrace } from '@mnemom/agent-alignment-protocol';
import type { APTrace, Action, Decision, Alternative, Escalation } from '@mnemom/agent-alignment-protocol';
import { randomUUID } from 'crypto';

function searchProductsWithTrace(cardId: string, query: string, preferences: Record<string, unknown>) {
  const results = performSearch(query, preferences);

  const trace: APTrace = {
    trace_id: `tr-${randomUUID().replace(/-/g, '').slice(0, 12)}`,
    agent_id: 'shopping-assistant',
    card_id: cardId,
    timestamp: new Date().toISOString(),

    action: {
      type: 'search',
      name: 'product-search', // Matches A2A skill ID
      category: 'bounded',
    },

    decision: {
      alternatives_considered: results.slice(0, 5).map((r) => ({
        option_id: r.id,
        description: r.name,
        score: r.relevanceScore,
        flags: r.sponsored ? ['sponsored'] : [],
      })),
      selected: results[0]?.id ?? null,
      selection_reasoning: buildReasoning(results, preferences),
      values_applied: ['principal_benefit', 'transparency'],
    },

    escalation: {
      evaluated: true,
      triggers_checked: [
        { trigger: 'skill_id == "purchase"', matched: false },
      ],
      required: false,
      reason: 'Search action within autonomy envelope',
    },
  };

  storeTrace(trace);
  return results;
}
```

## Step 6: Handle Incoming Coherence Checks

When another agent requests your alignment card or initiates a coherence check.

**Python (Flask):**

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

**TypeScript (Express):**

```typescript
import express from 'express';
import { checkCoherence } from '@mnemom/agent-alignment-protocol';

const app = express();
app.use(express.json());

app.get('/.well-known/alignment-card.json', (_req, res) => {
  res.json(loadAlignmentCard());
});

app.post('/aap/coherence-check', (req, res) => {
  const theirCard = req.body.initiator_alignment;
  const myCard = loadAlignmentCard();
  const result = checkCoherence(theirCard, myCard);

  res.json({
    compatible: result.compatible,
    score: result.score,
    proceed: result.proceed,
    matched_values: result.value_alignment.matched,
    conflicts: result.value_alignment.conflicts.map((c) => ({
      description: c.description,
      conflict_type: c.conflict_type,
    })),
  });
});

app.listen(3000);
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

For a comprehensive example with multiple vendors, coherence checks, delegation traces, and verification, see the [working example code](../examples/a2a-integration/) (available in both Python and TypeScript).

## EU Compliance Shortcut

Both SDKs include presets for EU AI Act Article 50 compliance (enforcement August 2026):

**Python:**

```python
from aap import EU_COMPLIANCE_AUDIT_COMMITMENT, EU_COMPLIANCE_VALUES

alignment = AlignmentCard(
    # ...
    values=EU_COMPLIANCE_VALUES,
    audit_commitment=EU_COMPLIANCE_AUDIT_COMMITMENT,  # 365-day retention, queryable
)
```

**TypeScript:**

```typescript
import { EU_COMPLIANCE_AUDIT_COMMITMENT, EU_COMPLIANCE_VALUES } from '@mnemom/agent-alignment-protocol';

const alignment = {
  // ...
  values: EU_COMPLIANCE_VALUES,
  audit_commitment: EU_COMPLIANCE_AUDIT_COMMITMENT, // 365-day retention, queryable
};
```

See the [EU AI Act Compliance Guide](EU_AI_ACT_MAPPING.md) for full field-level Article 50 mapping.

## Beyond Verification: Real-Time Monitoring with AIP

AAP provides post-hoc verification — checking whether actions matched declared alignment after they happen. The [Agent Integrity Protocol (AIP)](https://github.com/mnemom/aip) adds real-time integrity monitoring by analyzing agent reasoning (thinking blocks) as they occur.

Both AAP and AIP share the same Alignment Card. An A2A agent with an alignment block gets both:

- **AAP**: Did this agent do what it said it would? (`verify_trace`, `check_coherence`, `detect_drift`)
- **AIP**: Is this agent thinking clearly right now? (integrity checkpoints with `clear` / `review_needed` / `boundary_violation` verdicts)

To make AAP/AIP signals visible in your existing observability stack, use the OpenTelemetry exporters:

```bash
# Python
pip install aip-otel-exporter

# TypeScript
npm install @mnemom/aip-otel-exporter
```

These emit standard OTel spans with attributes like `aap.verification.result`, `aap.verification.similarity_score`, `aip.integrity.verdict` — compatible with Langfuse, Arize Phoenix, Datadog, and Grafana.

## Integration Checklist

- [ ] Install AAP SDK (`pip install agent-alignment-protocol` / `npm install @mnemom/agent-alignment-protocol`)
- [ ] Audit your current A2A Agent Card
- [ ] Identify which skills are bounded vs. require escalation
- [ ] Define your principal relationship
- [ ] Declare your operational values and conflicts
- [ ] Add forbidden actions (things you'll never do)
- [ ] Add the `alignment` block to your Agent Card
- [ ] Add AAP to A2A `extensions` array (v0.3)
- [ ] Serve alignment card at `/.well-known/alignment-card.json`
- [ ] Implement coherence check endpoint
- [ ] Add AP-Trace generation to skill implementations
- [ ] Test with `verify_trace()` before deployment
- [ ] Implement handling for non-AAP agents (graceful degradation)
- [ ] Consider AIP for real-time integrity monitoring
- [ ] Configure OTel exporter for observability

## Handling Non-AAP Agents

Not all agents will support AAP. Define your policy:

**Python:**

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

**TypeScript:**

```typescript
function delegateWithFallback(myCard: A2AAgentCard, theirCard: A2AAgentCard, task: unknown) {
  const theirAlignment = theirCard.alignment;

  if (theirAlignment) {
    const result = checkCoherence(myCard.alignment!, theirAlignment);
    if (!result.proceed) {
      return escalateToPrincipal({ task, conflicts: result.value_alignment.conflicts });
    }
    return executeDelegation(theirCard, task);
  }

  if (isTrustedAgent(theirCard)) {
    return executeDelegation(theirCard, task, { logNoAap: true });
  }

  if (taskIsLowRisk(task)) {
    return executeDelegation(theirCard, task, { logNoAap: true });
  }

  return escalateToPrincipal({
    task,
    reason: 'Target agent does not support AAP alignment verification',
  });
}
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
- **[EU_AI_ACT_MAPPING.md](EU_AI_ACT_MAPPING.md)** — EU AI Act Article 50 compliance guide
- **[examples/a2a-integration/](../examples/a2a-integration/)** — Working example code (Python + TypeScript)

---

*Questions? See the [full specification](SPEC.md) or check the [examples](../examples/).*
