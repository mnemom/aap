# MCP Integration Example

Demonstrates adding AAP alignment to MCP (Model Context Protocol) tool servers and generating AP-Traces for tool invocations.

## What This Shows

1. **Server-Level Alignment** — Defining an alignment card for an MCP server
2. **Tool Categories** — Bounded, escalated, and forbidden tool classification
3. **AP-Trace Generation** — Creating traces for every tool invocation
4. **Escalation Workflow** — Handling actions that require principal approval
5. **Forbidden Actions** — Blocking operations that are never permitted

## Quick Start

```bash
# From the repository root
cd examples/mcp-integration
python main.py
```

## The Scenario

A filesystem MCP server exposes tools for file operations. Different tools have different alignment properties:

| Tool | Category | Behavior |
|------|----------|----------|
| `read_file` | Bounded | Executes autonomously |
| `write_file` | Escalate | Requires `approved=True` |
| `delete_file` | Forbidden | Always blocked |

The server generates an AP-Trace for every invocation, documenting:
- What tool was called
- What alternatives were considered
- Whether escalation was required
- What the principal's response was (if applicable)

## Expected Output

```
======================================================================
MCP + AAP Integration Example
======================================================================

[1] Creating MCP server alignment card...
    Server: mcp-filesystem-server
    Card ID: ac-mcp-filesystem-001
    Values: ['user_control', 'transparency', 'harm_prevention', 'minimal_data']
    Bounded tools: ['read_file', 'list_directory', 'file_info']
    Forbidden tools: ['delete_file', 'execute_command', 'chmod']

    Saved: server-alignment-card.json

[2] Simulating bounded action: read_file('/home/user/notes.txt')...
    Result: success
    Action category: bounded
    Escalation required: False
    Trace verified: True

[3] Simulating escalated action WITHOUT approval: write_file('/tmp/test.txt')...
    Result: escalation_required
    Action category: escalate
    Escalation required: True
    Selected action: block
    Trace verified: True
    --> BLOCKED: Write requires principal approval

[4] Simulating escalated action WITH approval: write_file('/tmp/test.txt')...
    Result: success
    Bytes written: 11
    Action category: escalate
    Escalation required: True
    Principal response: approved
    Trace verified: True
    --> ALLOWED: Write approved by principal

[5] Simulating forbidden action: delete_file('/tmp/test.txt')...
    Result: forbidden
    Reason: delete_file is not permitted
    Action category: forbidden
    Selected action: block
    Trace verified: True
    --> BLOCKED: Forbidden action cannot be executed

[6] Saving AP-Traces...
    Saved 4 traces to: tool-invocation-traces.json

[7] Verifying all traces against alignment card...
    Results: 4 passed, 0 failed

======================================================================
Summary: MCP Server with AAP Alignment
======================================================================

    This example demonstrated an MCP filesystem server with AAP alignment:

    1. BOUNDED ACTIONS (autonomous, no approval needed):
       - read_file: Successfully read file, trace verified

    2. ESCALATED ACTIONS (require principal approval):
       - write_file without approval: Blocked, returned escalation_required
       - write_file with approval: Executed, trace records approval

    3. FORBIDDEN ACTIONS (always blocked):
       - delete_file: Blocked regardless of approval

    Each invocation generated an AP-Trace that:
    - Records the tool name and category
    - Documents alternatives considered
    - Logs escalation trigger evaluation
    - Captures principal response (for escalated actions)
    - Verifies against the alignment card

Generated files:
  - server-alignment-card.json (MCP server alignment)
  - tool-invocation-traces.json (4 AP-Traces)
======================================================================
```

## Generated Files

After running, you'll have:

- **server-alignment-card.json** — The MCP server's alignment card
- **tool-invocation-traces.json** — AP-Traces for all tool invocations

## Key Concepts Demonstrated

### Server Alignment Card

```json
{
  "card_version": "unified/2026-04-26",
  "card_id": "ac-mcp-filesystem-001",
  "agent_id": "mcp-filesystem-server",
  "autonomy_mode": "enforce",
  "integrity_mode": "observe",
  "principal": {
    "type": "human",
    "identifier": "did:web:user.example.com",
    "relationship": "delegated_authority"
  },
  "values": {
    "declared": ["user_control", "transparency", "harm_prevention", "minimal_data"],
    "conflicts_with": ["data_exfiltration", "unauthorized_access"]
  },
  "autonomy": {
    "bounded_actions": ["read_file", "list_directory", "file_info"],
    "escalation_triggers": [
      {
        "condition": "tool in ['write_file', 'append_file']",
        "action": "escalate",
        "reason": "Write operations require user approval"
      }
    ],
    "forbidden_actions": ["delete_file", "execute_command", "chmod"]
  },
  "audit": {
    "trace_format": "ap-trace-v1",
    "retention_days": 90,
    "queryable": true,
    "query_endpoint": "mcp://filesystem/alignment/traces"
  }
}
```

### Tool Invocation Trace

```json
{
  "trace_id": "tr-abc123def456",
  "agent_id": "mcp-filesystem-server",
  "card_id": "ac-mcp-filesystem-001",
  "action": {
    "type": "tool_invocation",
    "name": "write_file",
    "category": "escalate"
  },
  "decision": {
    "alternatives_considered": [
      {"option_id": "write", "description": "Write to /tmp/test.txt", "score": 1.0, "flags": ["approved"]}
    ],
    "selected": "write",
    "selection_reasoning": "Write approved by principal",
    "values_applied": ["user_control", "transparency"]
  },
  "escalation": {
    "evaluated": true,
    "triggers_checked": [
      {"trigger": "tool in ['write_file', ...]", "matched": true}
    ],
    "required": true,
    "principal_response": "approved",
    "reason": "Write operations require user approval"
  },
  "context": {
    "tool": "write_file",
    "path": "/tmp/test.txt",
    "bytes_written": 11
  }
}
```

### Escalation Workflow

1. Tool invocation arrives
2. Server checks if tool is in `forbidden_actions` → block immediately
3. Server checks if tool is in `bounded_actions` → execute autonomously
4. Otherwise, check escalation triggers
5. If escalation required and `approved=False` → return `escalation_required`
6. If escalation required and `approved=True` → execute and record approval
7. Generate AP-Trace for all outcomes

## Extending This Example

To add AAP alignment to your own MCP server:

1. Create an alignment card defining tool categories
2. Wrap tool implementations with trace generation
3. Implement escalation handling (check `approved` parameter)
4. Store traces for auditing
5. Expose alignment card via MCP resource

See the [MCP Migration Guide](../../docs/mcp-migration.md) for detailed implementation steps.

## Related Documentation

- **[mcp-migration.md](../../docs/mcp-migration.md)** — Complete guide to adding AAP to MCP servers
- **[QUICKSTART.md](../../docs/QUICKSTART.md)** — Core AAP concepts and API
- **[SPEC.md](../../docs/SPEC.md)** — Full protocol specification
- **[a2a-integration/](../a2a-integration/)** — A2A agent example
