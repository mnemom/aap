# Simple Agent Example

A minimal AAP implementation demonstrating the core workflow:

1. **Create an Alignment Card** — Declare what your agent is and what it will do
2. **Make decisions with tracing** — Produce AP-Traces for significant decisions
3. **Verify compliance** — Check that behavior matches declared alignment
4. **Catch violations** — See what happens when alignment is violated

## Quick Start

```bash
# From the repository root
cd examples/simple-agent
python main.py
```

## What It Does

The example creates a simple recommendation agent that:

- Declares values: `principal_benefit`, `transparency`, `honesty`
- Can perform: `search`, `compare`, `recommend` (bounded actions)
- Cannot perform: `share_personal_data`, `auto_subscribe` (forbidden)
- Must escalate: any `purchase` action

It then:

1. Makes a recommendation, deprioritizing sponsored content (compliant)
2. Verifies the trace passes
3. Attempts to share personal data (forbidden action)
4. Verifies the trace fails with a violation

## Expected Output

```
============================================================
AAP Simple Agent Example
============================================================

[1] Creating Alignment Card...
    Card ID: ac-simple-agent-001
    Values: ['principal_benefit', 'transparency', 'honesty']
    Bounded actions: ['search', 'compare', 'recommend']
    Forbidden actions: ['share_personal_data', 'auto_subscribe']
    Saved to: alignment-card.json

[2] Making a recommendation (compliant action)...
    Selected: Quality Product A (id: prod-A)
    Reasoning: Selected 'Quality Product A' with score 0.85. Sponsored options were deprioritized per principal_benefit value.

[3] Verifying trace against alignment card...
    Verified: True
    Violations: 0
    Warnings: 0
    ✓ Trace is compliant with declared alignment
    Saved to: trace-compliant.json

[4] Attempting forbidden action (for demonstration)...
    Action: share_personal_data

[5] Verifying forbidden action trace...
    Verified: False
    Violations: 1
    ✗ VIOLATION [CRITICAL]: forbidden_action
      Action 'share_personal_data' is in forbidden_actions
    Saved to: trace-violation.json

============================================================
Example complete. Generated files:
  - alignment-card.json (the agent's alignment declaration)
  - trace-compliant.json (a verified compliant trace)
  - trace-violation.json (a trace with violations)
============================================================
```

## Generated Files

After running, you'll have:

- `alignment-card.json` — The agent's alignment declaration
- `trace-compliant.json` — A trace that passes verification
- `trace-violation.json` — A trace that fails verification

## Key Concepts Demonstrated

### Sponsored Content Handling

The agent deprioritizes sponsored products even when they have higher raw scores:

```python
# Product B has score 0.90 but is sponsored
# Product A has score 0.85 and is not sponsored
# Agent selects Product A, logs reasoning in trace
```

### Forbidden Action Detection

When the agent attempts a forbidden action, verification catches it:

```python
# "share_personal_data" is in forbidden_actions
# Verification returns: verified=False, violation type=FORBIDDEN_ACTION
```

## Extending This Example

To use this pattern in your own agent:

1. Define your Alignment Card with appropriate values and boundaries
2. Wrap decision-making functions to produce traces
3. Run `verify_trace()` on traces before or after decisions
4. Handle violations appropriately (log, alert, block)

See the [QUICKSTART guide](../../docs/QUICKSTART.md) for more patterns.
