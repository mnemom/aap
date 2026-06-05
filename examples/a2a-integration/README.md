# A2A Integration Example

Demonstrates extending A2A Agent Cards with AAP alignment properties and using value coherence checks to decide whether to coordinate with other agents. Available in both **Python** and **TypeScript**.

## What This Shows

1. **A2A + AAP Agent Cards** — Combining capability declaration with alignment posture
2. **Value Coherence Handshake** — Checking compatibility before delegation
3. **Conflict Detection** — Identifying value conflicts between agents
4. **Delegation Decisions** — Recording coordination decisions with AP-Traces

## Quick Start

```bash
# Python
cd examples/a2a-integration
python main.py

# TypeScript
cd examples/a2a-integration
npm install
npx tsx index.ts
```

Both produce equivalent output.

## The Scenario

A user's shopping assistant needs to coordinate with vendor agents to find deals. Before delegating, it must verify that the vendor's values are compatible with its own.

**User Agent values:**
- `principal_benefit` — prioritize user's interests
- `transparency` — disclose reasoning
- `minimal_data` — collect only necessary info
- `honesty` — no deception

**User Agent conflicts with:**
- `deceptive_marketing`
- `hidden_fees`
- `upselling`

The example tests coordination with two vendors:

| Vendor | Values Include | Result |
|--------|----------------|--------|
| Vendor Deals Agent | `upselling` | INCOMPATIBLE |
| Ethical Vendor Agent | `principal_benefit`, `honesty`, `transparency` | COMPATIBLE |

## Expected Output

```
======================================================================
A2A + AAP Integration Example
======================================================================

[1] Creating A2A Agent Cards with AAP alignment blocks...
    User Agent: user-shopping-assistant
    Values: ['principal_benefit', 'transparency', 'minimal_data', 'honesty']
    Conflicts with: ['deceptive_marketing', 'hidden_fees', 'upselling']

    Vendor Agent: vendor-deals-agent
    Values: ['customer_satisfaction', 'transparency', 'upselling', 'conversion']

    Ethical Vendor: ethical-vendor-agent
    Values: ['principal_benefit', 'transparency', 'honesty', 'minimal_data']

    Saved: user-agent-card.json, vendor-agent-card.json, compatible-vendor-card.json

[2] Checking value coherence with vendor agent...
    Compatible: False
    Score: 0.13
    Matched values: ['transparency']
    Conflicts:
      - [incompatible] Responder's 'upselling' is in initiator's conflicts_with
    Proceed: False
    --> ESCALATION REQUIRED: Cannot delegate to this vendor

[3] Recording delegation decision (rejected due to conflicts)...
    Trace verified: True
    Action recorded: vendor-coordination
    Decision: reject
    Saved: delegation-rejected-trace.json

[4] Checking value coherence with ethical vendor...
    Compatible: True
    Score: 1.00
    Matched values: ['principal_benefit', 'honesty', 'minimal_data', 'transparency']
    Conflicts: None
    Proceed: True
    --> DELEGATION APPROVED: Values are compatible

[5] Recording delegation decision (approved)...
    Trace verified: True
    Action recorded: vendor-coordination
    Decision: delegate
    Saved: delegation-approved-trace.json

======================================================================
Summary: A2A Coordination with AAP Value Coherence
======================================================================

    User agent attempted to coordinate with two vendor agents:

    1. Vendor Deals Agent:
       - Has 'upselling' in declared values
       - User agent has 'upselling' in conflicts_with
       - Result: INCOMPATIBLE (score: 0.13)
       - Action: Delegation rejected, escalated to principal

    2. Ethical Vendor Agent:
       - Shares user-aligned values (principal_benefit, transparency, honesty)
       - Also conflicts with upselling, hidden_fees, deceptive_marketing
       - Result: COMPATIBLE (score: 1.00)
       - Action: Delegation approved

    This demonstrates how AAP enables agents to verify value alignment
    BEFORE delegating tasks, preventing mid-execution conflicts.

Generated files:
  - user-agent-card.json (A2A + AAP user agent)
  - vendor-agent-card.json (A2A + AAP vendor with conflicts)
  - compatible-vendor-card.json (A2A + AAP compatible vendor)
  - delegation-rejected-trace.json (trace of rejected delegation)
  - delegation-approved-trace.json (trace of approved delegation)
======================================================================
```

## Generated Files

After running, you'll have:

- **user-agent-card.json** — A2A Agent Card extended with AAP alignment
- **vendor-agent-card.json** — Vendor agent with conflicting values
- **compatible-vendor-card.json** — Vendor agent with compatible values
- **delegation-rejected-trace.json** — AP-Trace recording rejected delegation
- **delegation-approved-trace.json** — AP-Trace recording approved delegation

## Key Concepts Demonstrated

### A2A + AAP Agent Card Structure

```json
{
  "name": "user-shopping-assistant",
  "description": "Personal shopping assistant",
  "url": "https://user-agent.example.com",
  "version": "1.0.0",
  "capabilities": { "...": "standard A2A capabilities" },
  "skills": [ "...standard A2A skills..." ],

  "alignment": {
    "card_version": "unified/2026-04-26",
    "card_id": "ac-user-shopping-001",
    "autonomy_mode": "observe",
    "integrity_mode": "observe",
    "principal": {
      "type": "human",
      "identifier": "did:web:example.com",
      "relationship": "delegated_authority"
    },
    "values": {
      "declared": ["principal_benefit", "transparency"],
      "conflicts_with": ["upselling"]
    },
    "autonomy": { "...": "..." },
    "audit": { "...": "..." }
  }
}
```

### Value Coherence Check

```python
from aap import check_coherence

result = check_coherence(my_alignment, their_alignment)

if result.compatible:
    # Values are compatible
    proceed_with_delegation()
elif result.proceed:
    # Minor conflicts, can proceed with logging
    proceed_with_caution()
else:
    # Significant conflicts
    escalate_to_principal()
```

### Conflict Detection

The coherence check identifies specific conflicts:

- **Direct conflicts**: Their declared value is in my `conflicts_with` list
- **Inverse conflicts**: My declared value is in their `conflicts_with` list
- **Principal conflicts**: Different principal types with incompatible relationships

### Delegation Traces

Every delegation decision is recorded in an AP-Trace:

```json
{
  "action": {
    "type": "delegate",
    "name": "vendor-coordination",
    "category": "escalated"
  },
  "decision": {
    "alternatives_considered": [
      {"option_id": "delegate", "score": 0.42, "flags": ["value_conflict"]},
      {"option_id": "reject", "score": 0.58}
    ],
    "selected": "reject",
    "selection_reasoning": "Coherence check failed: upselling conflict",
    "values_applied": ["principal_benefit", "transparency"]
  },
  "escalation": {
    "required": true,
    "reason": "Escalated to principal due to value conflicts"
  }
}
```

## Extending This Example

To use this pattern in your own A2A agents:

1. Add an `alignment` block to your A2A Agent Card
2. Before delegating to another agent, fetch their Agent Card
3. Extract both alignment blocks and call `check_coherence()`
4. Handle the result based on your escalation policy
5. Record the delegation decision in an AP-Trace

See the [A2A Integration Guide](../../docs/A2A_INTEGRATION.md) for detailed implementation steps.

## Related Documentation

- **[A2A_INTEGRATION.md](../../docs/A2A_INTEGRATION.md)** — Complete guide to adding AAP to A2A agents
- **[QUICKSTART.md](../../docs/QUICKSTART.md)** — Core AAP concepts and API
- **[SPEC.md](../../docs/SPEC.md)** — Full protocol specification
- **[simple-agent/](../simple-agent/)** — Basic AAP example without A2A
