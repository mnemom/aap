# Agent Alignment Protocol (AAP)

[![CI](https://github.com/alexgarden/aap/actions/workflows/ci.yml/badge.svg)](https://github.com/alexgarden/aap/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/alexgarden/aap/branch/main/graph/badge.svg)](https://codecov.io/gh/alexgarden/aap)
[![PyPI](https://img.shields.io/pypi/v/agent-alignment-protocol.svg)](https://pypi.org/project/agent-alignment-protocol/)
[![npm](https://img.shields.io/npm/v/agent-alignment-protocol.svg)](https://www.npmjs.com/package/agent-alignment-protocol)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Spec](https://img.shields.io/badge/spec-v0.1.0-green.svg)](docs/SPEC.md)

**A transparency protocol for autonomous agents.**

AAP lets agents declare their alignment posture, produce auditable decision traces, and verify value coherence before coordinating with other agents. It extends existing protocols (A2A, MCP) with an alignment layer that makes agent behavior observable.

> AAP is a transparency protocol, not a trust protocol. It makes agent behavior more observable, not more guaranteed.

## Quick Start

```bash
# Install
pip install agent-alignment-protocol

# Generate an Alignment Card
aap init --values "principal_benefit,transparency,harm_prevention"
# ✓ Created alignment-card.json

# Instrument your agent
```

```python
from aap import trace_decision, load_card

card = load_card("alignment-card.json")

@trace_decision(card)
def recommend_product(user_preferences):
    # Your agent logic here
    # Decisions are automatically traced
    ...
```

```bash
# Verify behavior matches declaration
aap verify --card alignment-card.json --trace logs/trace.json
# ✓ 47/47 decisions within declared envelope
# ⚠ 3 decisions near boundary (logged)
# ✗ 0 boundary violations
```

## Why AAP?

The agent protocol stack provides capability discovery (A2A), tool integration (MCP), and payment authorization (AP2). None address a fundamental question: **Is this agent serving its principal's interests?**

| Protocol | Function | Gap |
|----------|----------|-----|
| **MCP** | Agent-to-tool connectivity | No alignment semantics |
| **A2A** | Task negotiation between agents | No value verification |
| **AP2** | Payment authorization | No behavioral audit |

As agent capabilities become symmetric—equal access to information, equal reasoning power—alignment becomes the primary differentiator. AAP provides the infrastructure to make alignment claims verifiable.

## Three Components

```
┌─────────────────┬─────────────────┬─────────────────┐
│ Alignment Card  │    AP-Trace     │ Value Coherence │
│                 │                 │    Handshake    │
├─────────────────┼─────────────────┼─────────────────┤
│ "What I claim   │ "What I         │ "Can we work    │
│  to be"         │  actually did"  │  together?"     │
└─────────────────┴─────────────────┴─────────────────┘
     Declaration        Audit          Coordination
```

### Alignment Card

A structured declaration of an agent's alignment posture:

```json
{
  "aap_version": "0.1.0",
  "agent_id": "did:web:my-agent.example.com",
  "principal": {
    "type": "human",
    "relationship": "delegated_authority"
  },
  "values": {
    "declared": ["principal_benefit", "transparency", "minimal_data"],
    "conflicts_with": ["deceptive_marketing", "hidden_fees"]
  },
  "autonomy_envelope": {
    "bounded_actions": ["search", "compare", "recommend"],
    "escalation_triggers": [
      {
        "condition": "purchase_value > 100",
        "action": "escalate",
        "reason": "Exceeds autonomous spending limit"
      }
    ],
    "forbidden_actions": ["share_credentials", "subscribe_to_services"]
  },
  "audit_commitment": {
    "trace_format": "ap-trace-v1",
    "retention_days": 90,
    "queryable": true
  }
}
```

### AP-Trace

An audit log entry recording each decision:

```json
{
  "trace_id": "tr-f47ac10b-58cc-4372",
  "card_id": "ac-f47ac10b-58cc-4372",
  "timestamp": "2026-01-31T12:30:00Z",
  "action": {
    "type": "recommend",
    "name": "product_recommendation",
    "category": "bounded"
  },
  "decision": {
    "alternatives_considered": [
      {"option_id": "A", "score": 0.85, "flags": []},
      {"option_id": "B", "score": 0.72, "flags": ["sponsored_content"]}
    ],
    "selected": "A",
    "selection_reasoning": "Highest score. Option B flagged as sponsored and deprioritized per principal_benefit value.",
    "values_applied": ["principal_benefit", "transparency"]
  },
  "escalation": {
    "evaluated": true,
    "required": false,
    "reason": "Recommendation only, no purchase action"
  }
}
```

### Value Coherence Handshake

Pre-coordination compatibility check between agents:

```python
from aap import check_coherence

result = check_coherence(my_card, their_card, task_context)

if result.compatible:
    # Proceed with coordination
    proceed_with_task()
else:
    # Handle conflict
    print(f"Value conflict: {result.conflicts}")
    # Escalate to principals or negotiate scope
```

## What AAP Does Not Do

This matters. Read it.

1. **AAP does NOT ensure alignment—it provides visibility.** An agent can produce perfect traces while acting against its principal's interests.

2. **Verified does NOT equal safe.** A verified trace means consistency with declared alignment. It doesn't mean the alignment is good or the outcome was beneficial.

3. **AP-Trace is sampled, not complete.** Traces capture decision points, not every computation. Significant reasoning may occur between traces.

4. **Value coherence is relative to declared values.** The handshake checks if declared values are compatible. It doesn't verify agents hold these values or will act on them.

5. **Tested on transformer-based agents.** Other architectures may exhibit behaviors AAP doesn't capture.

For the complete limitations disclosure, see [Section 10 of the Specification](docs/SPEC.md#10-limitations).

## Installation

```bash
# Python
pip install agent-alignment-protocol

# TypeScript
npm install agent-alignment-protocol
```

## Integration

### With A2A Agents

AAP extends the A2A Agent Card with an `alignment` block:

```json
{
  "name": "Shopping Assistant",
  "description": "Helps users find products",
  "url": "https://shopping.example.com",
  "alignment": {
    "$ref": "./alignment-card.json"
  }
}
```

See [A2A Migration Guide](docs/a2a-migration.md).

### With MCP Tools

AAP can trace tool invocations and verify they match declared alignment:

```python
from aap.integrations import mcp_traced

@mcp_traced(card)
def my_tool(params):
    ...
```

See [MCP Migration Guide](docs/mcp-migration.md).

## Verification

The verification engine checks whether observed behavior matches declared alignment:

```python
from aap import verify_trace, detect_drift

# Single trace verification
result = verify_trace(trace, card)
if not result.verified:
    print(f"Violations: {result.violations}")

# Drift detection over time
alerts = detect_drift(card, recent_traces)
for alert in alerts:
    print(f"Drift detected: {alert.drift_direction}")
```

**Verification checks:**
- Autonomy compliance (actions within declared bounds)
- Escalation compliance (required escalations were performed)
- Value consistency (applied values match declared values)
- Forbidden action compliance (no forbidden actions taken)

## Documentation

| Document | Description |
|----------|-------------|
| [**SPEC.md**](docs/SPEC.md) | Full protocol specification (IETF-style) |
| [**QUICKSTART.md**](docs/QUICKSTART.md) | Zero to compliant in 5 minutes |
| [**LIMITS.md**](docs/LIMITS.md) | What AAP guarantees and doesn't |
| [**SECURITY.md**](docs/SECURITY.md) | Threat model and security considerations |
| [**CALIBRATION.md**](docs/CALIBRATION.md) | How verification thresholds were derived |

## Examples

| Example | Description |
|---------|-------------|
| [`simple-agent/`](examples/simple-agent/) | Minimal AAP implementation |
| [`a2a-integration/`](examples/a2a-integration/) | A2A agent with AAP |
| [`mcp-integration/`](examples/mcp-integration/) | MCP tools with alignment |
| [`alignment-failure/`](examples/alignment-failure/) | Deliberate failure for testing |

## Status

**Current Version**: 0.1.0 (Draft)

| Component | Status |
|-----------|--------|
| Specification | ✅ Complete |
| JSON Schemas | 🔄 In Progress |
| Python SDK | 🔄 In Progress |
| TypeScript SDK | 📋 Planned |
| Verification Engine | 🔄 In Progress |
| Interactive Playground | 📋 Planned |

## API Reference

```python
# Core API
from aap import (
    verify_trace,      # Verify single trace against card
    check_coherence,   # Check value compatibility between agents
    detect_drift,      # Detect behavioral drift over time
)

# Models
from aap.schemas import (
    AlignmentCard,
    APTrace,
    VerificationResult,
    CoherenceResult,
    DriftAlert,
)

# CLI
# aap init [--values VALUES] [--output FILE]
# aap verify --card CARD --trace TRACE
# aap check-coherence --my-card MINE --their-card THEIRS
```

## Contributing

We welcome contributions. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

Key areas where we need help:
- SDK implementations in other languages
- Integration examples with popular agent frameworks
- Test vectors for edge cases
- Documentation improvements

## License

Apache 2.0. See [LICENSE](LICENSE) for details.

---

*Agent Alignment Protocol — Making agent alignment observable.*
