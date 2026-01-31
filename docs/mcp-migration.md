# Adding Alignment to MCP Tools

This guide shows how to add AAP alignment requirements to MCP tools.

## Overview

MCP (Model Context Protocol) defines how agents connect to tools. AAP adds alignment semantics to tool definitions and invocations.

## Tool Alignment Requirements

```json
{
  "tool": "purchase_product",
  "alignment_requirements": {
    "required_values": ["principal_benefit"],
    "conflicts_with": ["hidden_fees"],
    "escalation_required": true,
    "max_autonomous_value": 50
  }
}
```

## Pre-Invocation Check

Before invoking a tool, verify the agent's Alignment Card is compatible with the tool's requirements.

## AP-Trace Logging

Log all tool invocations in AP-Trace format for audit.

<!-- TODO: Detailed implementation guide -->
