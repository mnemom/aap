# Quick Start Guide

Get up and running with AAP in 5 minutes.

## Installation

```bash
pip install aap
```

## Basic Usage

### 1. Create an Alignment Card

```python
from aap import AlignmentCard

card = AlignmentCard(
    principal={"type": "human", "relationship": "delegated_authority"},
    autonomy_envelope={
        "bounded_actions": ["search", "compare", "recommend"],
        "escalation_triggers": ["purchase", "share_data"],
    },
    values={
        "declared": ["principal_benefit", "transparency"],
        "conflicts_with": ["deceptive_marketing"],
    },
)
```

### 2. Log Decisions with AP-Trace

```python
from aap import APTrace

trace = APTrace(
    action="recommend_product",
    considered=[
        {"option": "A", "score": 0.85, "reason": "best_match"},
        {"option": "B", "score": 0.68, "reason": "sponsored", "flagged": True},
    ],
    selected="A",
    reasoning="sponsored option deprioritized per principal values",
)
```

### 3. Verify Alignment Before Negotiation

```python
from aap import ValueCoherenceHandshake

handshake = ValueCoherenceHandshake(my_card=card, their_card=other_card)
if handshake.compatible:
    proceed()
else:
    escalate(handshake.conflicts)
```

## Next Steps

- [Full Specification](SPEC.md)
- [A2A Integration](a2a-migration.md)
- [MCP Integration](mcp-migration.md)
- [Limitations](LIMITS.md)
