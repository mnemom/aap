# Adding AAP to A2A Agents

This guide shows how to extend A2A Agent Cards with AAP alignment properties.

## Overview

A2A (Agent-to-Agent) protocol defines Agent Cards for task negotiation. AAP extends these cards with alignment metadata.

## Before: Standard A2A Agent Card

```json
{
  "name": "shopping-agent",
  "version": "1.0",
  "description": "Finds and compares products",
  "capabilities": ["search", "compare", "recommend"]
}
```

## After: AAP-Extended Agent Card

```json
{
  "name": "shopping-agent",
  "version": "1.0",
  "description": "Finds and compares products",
  "capabilities": ["search", "compare", "recommend"],
  "alignment": {
    "principal": {"type": "human", "relationship": "delegated_authority"},
    "autonomy_envelope": {
      "bounded_actions": ["search", "compare", "recommend"],
      "escalation_triggers": ["purchase", "share_data"],
      "max_autonomous_value": 100
    },
    "audit_commitment": {
      "trace_format": "ap-trace-v1",
      "queryable": true
    },
    "values": {
      "declared": ["principal_benefit", "transparency"],
      "conflicts_with": ["deceptive_marketing"]
    }
  }
}
```

## Implementation

<!-- TODO: Detailed implementation guide -->
