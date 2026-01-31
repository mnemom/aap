# Agent Alignment Protocol (AAP)

> The missing alignment layer for the agent protocol stack.

AAP provides standardized primitives for AI agent alignment verification, transparency, and value-coherent coordination.

## The Problem

The tech industry has built protocols for agent coordination:

| Protocol | Function | Gap |
|----------|----------|-----|
| **MCP** | Agent-to-tool connectivity | No alignment semantics |
| **A2A** | Task negotiation between agents | No value verification |

**None of these answer the alignment question:**
- Is this agent serving its principal?
- What did it consider before deciding?
- When will it escalate vs. act autonomously?
- Are its values compatible with my agent's values?

## The Solution

AAP fills this gap with three core primitives:

### 1. Alignment Card
Extends A2A Agent Cards with alignment metadata:
- Principal relationship (who the agent serves)
- Autonomy envelope (what it can do independently)
- Audit commitment (how decisions are logged)
- Declared values (what it optimizes for)

### 2. AP-Trace
Standardized audit log format:
- What options were considered
- Why a particular choice was made
- What was escalated vs. decided autonomously

### 3. Value Coherence Handshake
Protocol for agent-to-agent alignment verification:
- Declare values before negotiating
- Detect incompatible value systems
- Escalate conflicts to humans

## What AAP Does NOT Claim

Honesty is essential:

- AAP does **not** guarantee agents will behave as declared
- AAP does **not** protect against sophisticated deception
- AAP does **not** replace human judgment for consequential decisions
- AAP does **not** certify agents as "safe" or "trustworthy"

**AAP is a transparency protocol, not a trust protocol.** It makes agent behavior observable, not guaranteed.

## Installation

```bash
pip install aap
```

## Quick Start

```python
from aap import AlignmentCard, APTrace, ValueCoherenceHandshake

# Define your agent's alignment
card = AlignmentCard(
    principal={"type": "human", "relationship": "delegated_authority"},
    autonomy_envelope={
        "bounded_actions": ["search", "compare", "recommend"],
        "escalation_triggers": ["purchase", "share_data"],
        "max_autonomous_value": 100,
    },
    values={
        "declared": ["principal_benefit", "transparency"],
        "conflicts_with": ["deceptive_marketing"],
    },
)

# Log a decision
trace = APTrace(
    action="recommend_product",
    considered=[
        {"option": "A", "score": 0.85, "reason": "best_match"},
        {"option": "B", "score": 0.68, "reason": "sponsored", "flagged": True},
    ],
    selected="A",
    reasoning="sponsored option deprioritized per principal values",
)

# Verify alignment before agent-to-agent negotiation
handshake = ValueCoherenceHandshake(my_card=card, their_card=other_agent_card)
if handshake.compatible:
    proceed_with_negotiation()
else:
    escalate_to_humans(handshake.conflicts)
```

## Documentation

- [Specification](docs/SPEC.md) - Full protocol specification
- [Quick Start](docs/QUICKSTART.md) - 5-minute integration guide
- [Limits](docs/LIMITS.md) - What AAP does and doesn't guarantee
- [A2A Integration](docs/a2a-migration.md) - Adding AAP to A2A agents
- [MCP Integration](docs/mcp-migration.md) - Adding alignment to MCP tools

## Examples

- [`examples/simple-agent/`](examples/simple-agent/) - Minimal AAP implementation
- [`examples/a2a-integration/`](examples/a2a-integration/) - A2A agent with AAP
- [`examples/mcp-integration/`](examples/mcp-integration/) - MCP tools with alignment
- [`examples/alignment-failure/`](examples/alignment-failure/) - Handling value conflicts

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](LICENSE) for details.
