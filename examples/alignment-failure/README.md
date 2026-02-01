# Alignment Failure Example

**This is the most important example.** It demonstrates what AAP is actually for: making alignment failures visible.

## What It Shows

1. **Value Conflicts** — Two agents with incompatible values attempt to coordinate
2. **Coherence Check** — The conflict is detected before agents start working together
3. **Drift Detection** — An agent gradually drifts from its declared alignment
4. **Trace Verification** — Individual decisions are checked against the card

## Quick Start

```bash
cd examples/alignment-failure
python main.py
```

## The Scenario

### User Agent
- Principal: Human user
- Values: `principal_benefit`, `transparency`, `minimal_data`, `price_comparison`
- Conflicts with: `deceptive_marketing`, `hidden_fees`, `upselling`

### Vendor Agent
- Principal: Organization (vendor)
- Values: `customer_satisfaction`, `sales_conversion`, `upselling`, `data_collection`
- Conflicts with: `price_comparison`

**Notice the conflict**: The user agent values `price_comparison`. The vendor agent explicitly conflicts with `price_comparison`. The user agent conflicts with `upselling`. The vendor agent values `upselling`.

These agents have fundamentally different interests. AAP surfaces this.

## Expected Output

```
======================================================================
[2] Checking value coherence between agents...
======================================================================

    Compatible: False
    Coherence score: 0.0
    Proceed: False

    CONFLICTS DETECTED (2):
    ✗ Initiator's 'price_comparison' is in responder's conflicts_with
      Type: incompatible
    ✗ Responder's 'upselling' is in initiator's conflicts_with
      Type: incompatible

    Proposed resolution: {'type': 'escalate_to_principals', 'reason': 'Value conflict requires human decision'}
```

The coherence check **prevents** these agents from coordinating without human awareness.

## Drift Detection

The example also shows an agent that starts aligned but gradually drifts:

| Trace | Action | Values Applied | Status |
|-------|--------|---------------|--------|
| 1 | recommend | `principal_benefit`, `transparency` | ✓ Compliant |
| 2 | recommend | `principal_benefit` | ✓ Compliant |
| 3 | recommend | `quality_first` | ✗ Undeclared value |
| 4 | add_to_cart | `convenience` | ✗ Unbounded action, undeclared value |
| 5 | apply_discount | `sales_optimization` | ✗ Unbounded action, undeclared value |

The drift detection catches this:

```
    DRIFT DETECTED:
    Direction: value_drift
    Similarity score: 0.0
    Sustained for: 4 traces
```

## Key Takeaways

1. **VALUE COHERENCE CHECK** prevents misaligned agents from coordinating without human awareness. The user agent and vendor agent have fundamentally different interests — this SHOULD be surfaced.

2. **DRIFT DETECTION** catches when an agent's behavior deviates from its declared alignment over time. The user agent started serving the user but gradually shifted toward vendor interests.

3. **AAP doesn't PREVENT these failures — it makes them VISIBLE.** The human (principal) can then decide what to do.

## What Should Happen

When coherence fails:
1. DO NOT proceed with direct agent-to-agent coordination
2. Escalate to the principals (both the user and the vendor)
3. Present the conflicts clearly to humans
4. Let humans decide:
   - Negotiate modified scope
   - Choose a different vendor
   - Accept the conflict with awareness

When drift is detected:
1. Alert the principal
2. Review recent decisions
3. Determine if the drift is intentional (card needs updating) or problematic
4. Take corrective action

## Generated Files

- `user-agent-card.json` — User's agent alignment card
- `vendor-agent-card.json` — Vendor's agent alignment card
- `coherence-result.json` — Result of the coherence check
- `drift-traces.json` — The traces showing gradual drift

## Why This Matters

This example demonstrates the core value proposition of AAP:

> AAP is a transparency protocol, not a trust protocol. It makes alignment failures visible so humans can make informed decisions.

Without AAP, the user's agent and vendor's agent would negotiate directly, and the user would never know their agent was talking to an entity that explicitly doesn't want price comparisons and is optimizing for upselling.

With AAP, this conflict is surfaced *before* any coordination happens.
