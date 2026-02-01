# Adding AAP to MCP Tools

This guide shows how to extend MCP (Model Context Protocol) tools and servers with AAP alignment properties, enabling alignment verification for tool invocations.

## Overview

MCP defines a protocol for exposing tools to language models. AAP extends MCP servers with alignment metadata that declares:

- **Who the server/tools serve** (principal relationship)
- **What values guide tool behavior** (declared values)
- **Which tools are bounded vs. require escalation** (autonomy envelope)
- **How invocations are audited** (trace commitment)

This extension enables clients to verify alignment before invoking tools, and produces AP-Traces for tool invocation auditing.

## Prerequisites

```bash
pip install agent-alignment-protocol
```

## MCP vs A2A: Key Differences

| Aspect | A2A | MCP |
|--------|-----|-----|
| Scope | Agent capabilities | Tool invocations |
| Granularity | Agent-level cards | Server + tool-level alignment |
| Discovery | Agent Card endpoint | Server manifest + tool list |
| Actions | Skills | Tools |

MCP alignment operates at two levels:
1. **Server-level**: Default alignment for all tools in the server
2. **Tool-level**: Override alignment for specific tools

## Step 1: Understand Your Current MCP Server

A standard MCP server exposes tools with JSON schemas:

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    name="filesystem",
    instructions="File system operations for reading and writing files."
)

@mcp.tool()
def read_file(path: str) -> str:
    """Read contents of a file.

    Args:
        path: Path to the file to read

    Returns:
        File contents as string
    """
    with open(path) as f:
        return f.read()

@mcp.tool()
def write_file(path: str, content: str) -> dict:
    """Write content to a file.

    Args:
        path: Path to the file to write
        content: Content to write

    Returns:
        Status dict with bytes written
    """
    with open(path, 'w') as f:
        bytes_written = f.write(content)
    return {"status": "success", "bytes_written": bytes_written}

@mcp.tool()
def delete_file(path: str) -> dict:
    """Delete a file from the filesystem.

    Args:
        path: Path to the file to delete

    Returns:
        Status dict
    """
    import os
    os.remove(path)
    return {"status": "deleted", "path": path}
```

This tells clients *what* tools are available, but not:
- Which tools are safe to invoke autonomously
- Which tools require user approval
- Which paths/operations are forbidden
- What values guide tool behavior

## Step 2: Add Server-Level Alignment

Create an alignment card for your MCP server:

```python
from mcp.server.fastmcp import FastMCP
from aap import AlignmentCard

# Define server alignment
SERVER_ALIGNMENT = AlignmentCard(
    aap_version="0.1.0",
    card_id="ac-filesystem-server-001",
    agent_id="mcp-filesystem",
    issued_at="2026-01-31T12:00:00Z",

    principal={
        "type": "human",
        "relationship": "delegated_authority"
    },

    values={
        "declared": ["user_control", "transparency", "minimal_data"],
        "conflicts_with": ["data_exfiltration", "unauthorized_access"]
    },

    autonomy_envelope={
        "bounded_actions": ["read_file"],
        "escalation_triggers": [
            {
                "condition": "tool == 'write_file'",
                "action": "escalate",
                "reason": "Write operations require user approval"
            }
        ],
        "forbidden_actions": ["delete_file"]
    },

    audit_commitment={
        "trace_format": "ap-trace-v1",
        "retention_days": 30,
        "queryable": True,
        "query_endpoint": "mcp://filesystem/alignment/traces"
    }
)

mcp = FastMCP(
    name="filesystem",
    instructions="File system operations with alignment verification."
)
```

### Key Mapping: MCP Tools to AAP Actions

| MCP Tool | AAP Treatment | Rationale |
|----------|---------------|-----------|
| `read_file` | `bounded_actions` | Read-only, low risk |
| `write_file` | `escalation_triggers` | Modifies state, needs approval |
| `delete_file` | `forbidden_actions` | Destructive, never autonomous |

## Step 3: Expose Alignment Card

MCP servers SHOULD expose their alignment card via a resource:

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(name="filesystem")

@mcp.resource("alignment://card")
def get_alignment_card() -> str:
    """Return the server's alignment card."""
    return SERVER_ALIGNMENT.model_dump_json(indent=2)
```

Alternatively, include alignment in server instructions:

```python
mcp = FastMCP(
    name="filesystem",
    instructions=f"""File system operations with AAP alignment.

## Alignment Card

{SERVER_ALIGNMENT.model_dump_json(indent=2)}

## Tool Boundaries

- **Bounded (autonomous)**: read_file
- **Escalate (needs approval)**: write_file
- **Forbidden (never)**: delete_file
"""
)
```

## Step 4: Generate AP-Traces for Tool Invocations

Wrap tool implementations to produce AP-Traces:

```python
from aap import APTrace, Action, Decision, Escalation
from datetime import datetime, timezone
import uuid
import functools

def traced_tool(tool_name: str, category: str):
    """Decorator to generate AP-Traces for tool invocations."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            trace_id = f"tr-{uuid.uuid4().hex[:12]}"
            timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

            # Check if escalation is required
            escalation_required = category == "escalate"

            if category == "forbidden":
                # Log attempt but don't execute
                trace = APTrace(
                    trace_id=trace_id,
                    agent_id="mcp-filesystem",
                    card_id=SERVER_ALIGNMENT.card_id,
                    timestamp=timestamp,
                    action=Action(
                        type="tool_invocation",
                        name=tool_name,
                        category="forbidden",
                    ),
                    decision=Decision(
                        alternatives_considered=[],
                        selected=None,
                        selection_reasoning="Forbidden action blocked",
                        values_applied=["user_control"],
                    ),
                    escalation=Escalation(
                        evaluated=True,
                        triggers_checked=[{"trigger": "forbidden_action", "matched": True}],
                        required=True,
                        reason="Action is in forbidden_actions list",
                    ),
                )
                store_trace(trace)
                raise PermissionError(f"Forbidden action: {tool_name}")

            # Execute the tool
            result = func(*args, **kwargs)

            # Build trace
            trace = APTrace(
                trace_id=trace_id,
                agent_id="mcp-filesystem",
                card_id=SERVER_ALIGNMENT.card_id,
                timestamp=timestamp,
                action=Action(
                    type="tool_invocation",
                    name=tool_name,
                    category=category,
                ),
                decision=Decision(
                    alternatives_considered=[
                        {
                            "option_id": "execute",
                            "description": f"Execute {tool_name}",
                            "score": 1.0,
                            "flags": [],
                        }
                    ],
                    selected="execute",
                    selection_reasoning=f"Tool {tool_name} within autonomy envelope",
                    values_applied=SERVER_ALIGNMENT.values["declared"],
                ),
                escalation=Escalation(
                    evaluated=True,
                    triggers_checked=[
                        {"trigger": f"tool == '{tool_name}'", "matched": escalation_required}
                    ],
                    required=escalation_required,
                    reason="Within bounded actions" if not escalation_required else "Requires approval",
                ),
                context={
                    "tool_args": kwargs,
                    "result_summary": str(result)[:100] if result else None,
                },
            )

            store_trace(trace)
            return result
        return wrapper
    return decorator

# Apply to tools
@mcp.tool()
@traced_tool("read_file", "bounded")
def read_file(path: str) -> str:
    """Read contents of a file."""
    with open(path) as f:
        return f.read()

@mcp.tool()
@traced_tool("write_file", "escalate")
def write_file(path: str, content: str) -> dict:
    """Write content to a file (requires approval)."""
    with open(path, 'w') as f:
        bytes_written = f.write(content)
    return {"status": "success", "bytes_written": bytes_written}

@mcp.tool()
@traced_tool("delete_file", "forbidden")
def delete_file(path: str) -> dict:
    """Delete a file (forbidden action)."""
    import os
    os.remove(path)
    return {"status": "deleted"}
```

## Step 5: Tool-Level Alignment Overrides

For servers with many tools, specify per-tool alignment:

```python
TOOL_ALIGNMENT = {
    "read_file": {
        "category": "bounded",
        "values": ["transparency", "minimal_data"],
        "conditions": [
            {"field": "path", "pattern": "^/home/", "action": "allow"},
            {"field": "path", "pattern": "^/etc/passwd", "action": "forbid"},
        ]
    },
    "write_file": {
        "category": "escalate",
        "values": ["user_control"],
        "escalation_reason": "Write operations modify system state",
    },
    "delete_file": {
        "category": "forbidden",
        "values": ["harm_prevention"],
        "forbidden_reason": "Destructive operations not permitted",
    },
    "list_directory": {
        "category": "bounded",
        "values": ["transparency"],
    },
}

def get_tool_category(tool_name: str) -> str:
    """Get alignment category for a tool."""
    return TOOL_ALIGNMENT.get(tool_name, {}).get("category", "escalate")
```

## Step 6: Client-Side Verification

Clients invoking MCP tools can verify alignment before invocation:

```python
from aap import verify_trace, check_coherence

class AlignedMCPClient:
    """MCP client with alignment verification."""

    def __init__(self, server_alignment: dict, my_alignment: dict):
        self.server_alignment = server_alignment
        self.my_alignment = my_alignment

    async def invoke_tool(self, tool_name: str, arguments: dict):
        """Invoke a tool with alignment checks."""

        # 1. Check value coherence with server
        coherence = check_coherence(self.my_alignment, self.server_alignment)
        if not coherence.proceed:
            raise ValueError(f"Value conflict with server: {coherence.value_alignment.conflicts}")

        # 2. Check if tool is within our autonomy envelope
        server_envelope = self.server_alignment.get("autonomy_envelope", {})
        bounded = server_envelope.get("bounded_actions", [])
        forbidden = server_envelope.get("forbidden_actions", [])

        if tool_name in forbidden:
            raise PermissionError(f"Tool {tool_name} is forbidden by server alignment")

        if tool_name not in bounded:
            # Requires escalation - check with principal
            approved = await self.request_approval(tool_name, arguments)
            if not approved:
                raise PermissionError(f"Tool {tool_name} requires approval (denied)")

        # 3. Invoke the tool
        result = await self._invoke(tool_name, arguments)

        # 4. Verify the trace (if server provides one)
        if hasattr(result, 'trace'):
            verification = verify_trace(result.trace, self.server_alignment)
            if not verification.verified:
                raise ValueError(f"Trace verification failed: {verification.violations}")

        return result
```

## Complete Example: Aligned MCP Server

```python
"""Filesystem MCP server with AAP alignment."""
from mcp.server.fastmcp import FastMCP
from aap import AlignmentCard, APTrace, Action, Decision, Escalation, verify_trace
from datetime import datetime, timezone
import uuid
import json
import os

# --- Alignment Configuration ---

SERVER_ALIGNMENT = AlignmentCard(
    aap_version="0.1.0",
    card_id="ac-filesystem-001",
    agent_id="mcp-filesystem",
    issued_at="2026-01-31T12:00:00Z",
    principal={"type": "human", "relationship": "delegated_authority"},
    values={
        "declared": ["user_control", "transparency", "harm_prevention"],
        "conflicts_with": ["data_exfiltration", "unauthorized_access"],
    },
    autonomy_envelope={
        "bounded_actions": ["read_file", "list_directory", "file_info"],
        "escalation_triggers": [
            {
                "condition": "tool in ['write_file', 'append_file']",
                "action": "escalate",
                "reason": "Write operations require approval"
            }
        ],
        "forbidden_actions": ["delete_file", "execute_command"],
    },
    audit_commitment={
        "trace_format": "ap-trace-v1",
        "retention_days": 90,
        "queryable": True,
        "query_endpoint": "mcp://filesystem/alignment/traces",
    },
)

# --- Trace Storage ---

TRACES: list[dict] = []

def store_trace(trace: APTrace):
    """Store trace for auditing."""
    TRACES.append(trace.model_dump(mode="json"))

# --- MCP Server ---

mcp = FastMCP(
    name="filesystem",
    instructions=f"""Filesystem operations with AAP alignment.

Alignment Card ID: {SERVER_ALIGNMENT.card_id}
Values: {', '.join(SERVER_ALIGNMENT.values['declared'])}

Tool Boundaries:
- Bounded (autonomous): read_file, list_directory, file_info
- Escalate (needs approval): write_file, append_file
- Forbidden (blocked): delete_file, execute_command
"""
)

# --- Alignment Resource ---

@mcp.resource("alignment://card")
def alignment_card() -> str:
    """Get server alignment card."""
    return SERVER_ALIGNMENT.model_dump_json(indent=2)

@mcp.resource("alignment://traces")
def alignment_traces() -> str:
    """Get recent AP-Traces."""
    return json.dumps(TRACES[-100:], indent=2)

# --- Tools with Tracing ---

@mcp.tool()
def read_file(path: str) -> str:
    """Read contents of a file (bounded action).

    Args:
        path: Path to the file to read

    Returns:
        File contents
    """
    trace_id = f"tr-{uuid.uuid4().hex[:12]}"
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    try:
        with open(path) as f:
            content = f.read()

        trace = APTrace(
            trace_id=trace_id,
            agent_id="mcp-filesystem",
            card_id=SERVER_ALIGNMENT.card_id,
            timestamp=timestamp,
            action=Action(type="tool_invocation", name="read_file", category="bounded"),
            decision=Decision(
                alternatives_considered=[{"option_id": "read", "description": f"Read {path}", "score": 1.0, "flags": []}],
                selected="read",
                selection_reasoning="Read-only operation within autonomy envelope",
                values_applied=["transparency"],
            ),
            escalation=Escalation(
                evaluated=True,
                triggers_checked=[{"trigger": "tool == 'read_file'", "matched": False}],
                required=False,
                reason="Bounded action",
            ),
            context={"path": path, "bytes_read": len(content)},
        )
        store_trace(trace)
        return content

    except Exception as e:
        # Trace the failure
        trace = APTrace(
            trace_id=trace_id,
            agent_id="mcp-filesystem",
            card_id=SERVER_ALIGNMENT.card_id,
            timestamp=timestamp,
            action=Action(type="tool_invocation", name="read_file", category="bounded"),
            decision=Decision(
                alternatives_considered=[],
                selected=None,
                selection_reasoning=f"Operation failed: {e}",
                values_applied=["transparency"],
            ),
            escalation=Escalation(evaluated=True, triggers_checked=[], required=False, reason="Failed"),
        )
        store_trace(trace)
        raise

@mcp.tool()
def write_file(path: str, content: str, approved: bool = False) -> dict:
    """Write content to a file (requires escalation).

    Args:
        path: Path to the file to write
        content: Content to write
        approved: Whether this write was explicitly approved by principal

    Returns:
        Status with bytes written
    """
    trace_id = f"tr-{uuid.uuid4().hex[:12]}"
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    if not approved:
        trace = APTrace(
            trace_id=trace_id,
            agent_id="mcp-filesystem",
            card_id=SERVER_ALIGNMENT.card_id,
            timestamp=timestamp,
            action=Action(type="tool_invocation", name="write_file", category="escalate"),
            decision=Decision(
                alternatives_considered=[],
                selected=None,
                selection_reasoning="Write operation requires explicit approval",
                values_applied=["user_control"],
            ),
            escalation=Escalation(
                evaluated=True,
                triggers_checked=[{"trigger": "tool == 'write_file'", "matched": True}],
                required=True,
                reason="Write operations require approval",
            ),
        )
        store_trace(trace)
        raise PermissionError("write_file requires approved=True (escalation)")

    with open(path, 'w') as f:
        bytes_written = f.write(content)

    trace = APTrace(
        trace_id=trace_id,
        agent_id="mcp-filesystem",
        card_id=SERVER_ALIGNMENT.card_id,
        timestamp=timestamp,
        action=Action(type="tool_invocation", name="write_file", category="escalate"),
        decision=Decision(
            alternatives_considered=[{"option_id": "write", "description": f"Write to {path}", "score": 1.0, "flags": ["approved"]}],
            selected="write",
            selection_reasoning="Write approved by principal",
            values_applied=["user_control", "transparency"],
        ),
        escalation=Escalation(
            evaluated=True,
            triggers_checked=[{"trigger": "tool == 'write_file'", "matched": True}],
            required=True,
            principal_response="approved",
            reason="Write operations require approval",
        ),
        context={"path": path, "bytes_written": bytes_written},
    )
    store_trace(trace)

    return {"status": "success", "bytes_written": bytes_written}

@mcp.tool()
def delete_file(path: str) -> dict:
    """Delete a file (forbidden action - always blocked).

    Args:
        path: Path to the file to delete

    Returns:
        Never returns - always raises
    """
    trace_id = f"tr-{uuid.uuid4().hex[:12]}"
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    trace = APTrace(
        trace_id=trace_id,
        agent_id="mcp-filesystem",
        card_id=SERVER_ALIGNMENT.card_id,
        timestamp=timestamp,
        action=Action(type="tool_invocation", name="delete_file", category="forbidden"),
        decision=Decision(
            alternatives_considered=[],
            selected=None,
            selection_reasoning="Forbidden action blocked",
            values_applied=["harm_prevention", "user_control"],
        ),
        escalation=Escalation(
            evaluated=True,
            triggers_checked=[{"trigger": "forbidden_action", "matched": True}],
            required=True,
            reason="delete_file is in forbidden_actions",
        ),
    )
    store_trace(trace)

    raise PermissionError("delete_file is a forbidden action")

# --- Verification Endpoint ---

@mcp.tool()
def verify_recent_traces(limit: int = 10) -> dict:
    """Verify recent traces against the alignment card.

    Args:
        limit: Number of recent traces to verify

    Returns:
        Verification summary
    """
    recent = TRACES[-limit:]
    results = []

    for trace_dict in recent:
        trace = APTrace(**trace_dict)
        result = verify_trace(trace, SERVER_ALIGNMENT)
        results.append({
            "trace_id": trace.trace_id,
            "passed": result.verified,
            "violations": [v.description for v in result.violations] if result.violations else [],
        })

    passed = sum(1 for r in results if r["passed"])

    return {
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "details": results,
    }

if __name__ == "__main__":
    mcp.run()
```

## MCP Configuration with Alignment

Update your `.mcp.json` to indicate alignment support:

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "python",
      "args": ["-m", "filesystem_server"],
      "env": {
        "AAP_TRACE_ENABLED": "true",
        "AAP_TRACE_PATH": "/var/log/aap/filesystem/"
      },
      "metadata": {
        "alignment": {
          "supported": true,
          "card_resource": "alignment://card",
          "traces_resource": "alignment://traces"
        }
      }
    }
  }
}
```

## Migration Checklist

- [ ] Audit your current MCP tools
- [ ] Classify tools: bounded, escalate, or forbidden
- [ ] Create server-level alignment card
- [ ] Define tool-level overrides if needed
- [ ] Add alignment card resource (`alignment://card`)
- [ ] Implement AP-Trace generation for tool invocations
- [ ] Add trace storage/retrieval resource
- [ ] Test with `verify_trace()` before deployment
- [ ] Update `.mcp.json` with alignment metadata
- [ ] Document alignment in server instructions
- [ ] Handle non-AAP clients gracefully

## Handling Non-AAP Clients

MCP servers with AAP should still work with clients that don't support alignment:

```python
@mcp.tool()
def write_file(path: str, content: str, approved: bool = False) -> dict:
    """Write content to a file.

    Args:
        path: Path to write
        content: Content to write
        approved: AAP approval flag (non-AAP clients can omit)
    """
    # Non-AAP clients won't pass approved=True
    # Server policy: require approval for writes
    if not approved:
        return {
            "status": "escalation_required",
            "message": "This operation requires approval. Call with approved=True after user confirms.",
            "aap_info": {
                "action_category": "escalate",
                "reason": "Write operations require explicit approval",
                "card_id": SERVER_ALIGNMENT.card_id,
            }
        }

    # Proceed with approved write
    ...
```

## Standard Value Identifiers

Use these standard identifiers where applicable:

| Identifier | Description |
|------------|-------------|
| `user_control` | Respect user autonomy and consent |
| `transparency` | Disclose operations and reasoning |
| `minimal_data` | Access only necessary data |
| `harm_prevention` | Avoid destructive operations |
| `honesty` | Do not deceive or mislead |
| `privacy` | Protect personal information |
| `principal_benefit` | Prioritize principal's interests |

Custom values MUST be defined in the alignment card's `definitions` block.

## What's Next?

- **[QUICKSTART.md](QUICKSTART.md)** — Core AAP concepts and API
- **[SPEC.md](SPEC.md)** — Full protocol specification
- **[a2a-migration.md](a2a-migration.md)** — Adding AAP to A2A agents
- **[examples/mcp-integration/](../examples/mcp-integration/)** — Working example code

---

*Questions? See the [full specification](SPEC.md) or check the [examples](../examples/).*
