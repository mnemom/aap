"""MCP + AAP Integration Example

Demonstrates adding AAP alignment to MCP tool servers and generating
AP-Traces for tool invocations.

This example creates a simulated MCP filesystem server with AAP alignment:
- read_file: bounded action (autonomous)
- write_file: escalated action (requires approval)
- delete_file: forbidden action (always blocked)

It then simulates tool invocations and shows how AP-Traces are generated
and verified against the server's alignment card.

Run with: python main.py
"""

import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Add the src directory to the path for local development
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from aap import (
    Action,
    AlignmentCard,
    Alternative,
    APTrace,
    Decision,
    Escalation,
    verify_trace,
)
from aap.schemas.ap_trace import PrincipalResponse


def create_mcp_server_alignment() -> AlignmentCard:
    """Create alignment card for the MCP filesystem server."""
    return AlignmentCard(
        card_version="unified/2026-04-26",
        card_id="ac-mcp-filesystem-001",
        agent_id="mcp-filesystem-server",
        issued_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        autonomy_mode="enforce",
        integrity_mode="observe",
        principal={
            "type": "human",
            "identifier": "did:web:user.example.com",
            "relationship": "delegated_authority",
        },
        values={
            "declared": [
                "user_control",
                "transparency",
                "harm_prevention",
                "minimal_data",
            ],
            "conflicts_with": [
                "data_exfiltration",
                "unauthorized_access",
                "destructive_operations",
            ],
        },
        autonomy={
            "bounded_actions": ["read_file", "list_directory", "file_info"],
            "escalation_triggers": [
                {
                    "condition": "tool in ['write_file', 'append_file', 'create_file']",
                    "action": "escalate",
                    "reason": "Write operations require user approval",
                },
                {
                    "condition": "path.startswith('/etc/') or path.startswith('/sys/')",
                    "action": "escalate",
                    "reason": "System paths require explicit approval",
                },
            ],
            "forbidden_actions": ["delete_file", "execute_command", "chmod"],
        },
        audit={
            "trace_format": "ap-trace-v1",
            "retention_days": 90,
            "queryable": True,
            "query_endpoint": "mcp://filesystem/alignment/traces",
        },
    )


def simulate_read_file(
    server_alignment: AlignmentCard, path: str
) -> tuple[dict, APTrace]:
    """Simulate a read_file tool invocation with AP-Trace generation."""
    trace_id = f"tr-{uuid.uuid4().hex[:12]}"
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # Simulate reading the file
    content = f"Contents of {path} (simulated)"

    trace = APTrace(
        trace_id=trace_id,
        agent_id=server_alignment.agent_id,
        card_id=server_alignment.card_id,
        timestamp=timestamp,
        action=Action(
            type="execute",
            name="read_file",
            category="bounded",
        ),
        decision=Decision(
            alternatives_considered=[
                Alternative(
                    option_id="read",
                    description=f"Read contents of {path}",
                    score=1.0,
                    flags=[],
                ),
            ],
            selected="read",
            selection_reasoning="Read-only operation within autonomy envelope",
            values_applied=["transparency", "minimal_data"],
        ),
        escalation=Escalation(
            evaluated=True,
            triggers_checked=[
                {"trigger": "tool == 'read_file'", "matched": False},
                {"trigger": "path.startswith('/etc/')", "matched": path.startswith("/etc/")},
            ],
            required=False,
            reason="Bounded action, no escalation triggers matched",
        ),
        context={
            "tool": "read_file",
            "path": path,
            "bytes_read": len(content),
        },
    )

    return {"status": "success", "content": content}, trace


def simulate_write_file(
    server_alignment: AlignmentCard, path: str, content: str, approved: bool = False
) -> tuple[dict, APTrace]:
    """Simulate a write_file tool invocation with AP-Trace generation."""
    trace_id = f"tr-{uuid.uuid4().hex[:12]}"
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    if not approved:
        # Escalation required but not approved
        trace = APTrace(
            trace_id=trace_id,
            agent_id=server_alignment.agent_id,
            card_id=server_alignment.card_id,
            timestamp=timestamp,
            action=Action(
                type="deny",
                name="write_file",
                category="escalation_trigger",
            ),
            decision=Decision(
                alternatives_considered=[
                    Alternative(
                        option_id="write",
                        description=f"Write to {path}",
                        score=0.8,
                        flags=["requires_approval"],
                    ),
                    Alternative(
                        option_id="block",
                        description="Block unapproved write",
                        score=1.0,
                        flags=[],
                    ),
                ],
                selected="block",
                selection_reasoning="Write operation requires explicit approval",
                values_applied=["user_control"],
            ),
            escalation=Escalation(
                evaluated=True,
                triggers_checked=[
                    {"trigger": "tool in ['write_file', 'append_file', 'create_file']", "matched": True},
                ],
                required=True,
                reason="Write operations require user approval",
            ),
            context={
                "tool": "write_file",
                "path": path,
                "approved": False,
            },
        )
        return {"status": "escalation_required", "reason": "Write requires approval"}, trace

    # Approved write
    trace = APTrace(
        trace_id=trace_id,
        agent_id=server_alignment.agent_id,
        card_id=server_alignment.card_id,
        timestamp=timestamp,
        action=Action(
            type="execute",
            name="write_file",
            category="escalation_trigger",
        ),
        decision=Decision(
            alternatives_considered=[
                Alternative(
                    option_id="write",
                    description=f"Write to {path}",
                    score=1.0,
                    flags=["approved"],
                ),
            ],
            selected="write",
            selection_reasoning="Write approved by principal",
            values_applied=["user_control", "transparency"],
        ),
        escalation=Escalation(
            evaluated=True,
            triggers_checked=[
                {"trigger": "tool in ['write_file', 'append_file', 'create_file']", "matched": True},
            ],
            required=True,
            principal_response=PrincipalResponse(
                decision="approved",
                timestamp=datetime.now(timezone.utc),
            ),
            reason="Write operations require user approval",
        ),
        context={
            "tool": "write_file",
            "path": path,
            "bytes_written": len(content),
            "approved": True,
        },
    )

    return {"status": "success", "bytes_written": len(content)}, trace


def simulate_delete_file(
    server_alignment: AlignmentCard, path: str
) -> tuple[dict, APTrace]:
    """Simulate a delete_file tool invocation (forbidden action)."""
    trace_id = f"tr-{uuid.uuid4().hex[:12]}"
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    trace = APTrace(
        trace_id=trace_id,
        agent_id=server_alignment.agent_id,
        card_id=server_alignment.card_id,
        timestamp=timestamp,
        action=Action(
            type="deny",
            name="delete_file",
            category="forbidden",
        ),
        decision=Decision(
            alternatives_considered=[
                Alternative(
                    option_id="delete",
                    description=f"Delete {path}",
                    score=0.0,
                    flags=["forbidden"],
                ),
                Alternative(
                    option_id="block",
                    description="Block forbidden operation",
                    score=1.0,
                    flags=[],
                ),
            ],
            selected="block",
            selection_reasoning="delete_file is a forbidden action",
            values_applied=["harm_prevention", "user_control"],
        ),
        escalation=Escalation(
            evaluated=True,
            triggers_checked=[
                {"trigger": "forbidden_action", "matched": True},
            ],
            required=True,
            reason="delete_file is in forbidden_actions list",
        ),
        context={
            "tool": "delete_file",
            "path": path,
            "blocked": True,
        },
    )

    return {"status": "forbidden", "reason": "delete_file is not permitted"}, trace


def main():
    """Run the MCP + AAP integration example."""
    print("=" * 70)
    print("MCP + AAP Integration Example")
    print("=" * 70)
    print()

    # Step 1: Create server alignment card
    print("[1] Creating MCP server alignment card...")
    server_alignment = create_mcp_server_alignment()
    print(f"    Server: {server_alignment.agent_id}")
    print(f"    Card ID: {server_alignment.card_id}")
    print(f"    Values: {server_alignment.values.declared}")
    print(f"    Bounded tools: {server_alignment.autonomy.bounded_actions}")
    print(f"    Forbidden tools: {server_alignment.autonomy.forbidden_actions}")
    print()

    # Save alignment card. Use to_dict() (exclude_none) so the emitted file is
    # the clean unified shape — the platform validator treats an explicit
    # `null` on optional fields like values.definitions / values.hierarchy as
    # "present but invalid", so we omit them rather than write nulls.
    card_path = Path(__file__).parent / "server-alignment-card.json"
    with open(card_path, "w") as f:
        json.dump(server_alignment.to_dict(), f, indent=2)
    print(f"    Saved: {card_path.name}")
    print()

    traces = []

    # Step 2: Simulate bounded action (read_file)
    print("[2] Simulating bounded action: read_file('/home/user/notes.txt')...")
    result, trace = simulate_read_file(server_alignment, "/home/user/notes.txt")
    traces.append(trace)
    verification = verify_trace(
        trace.model_dump(mode="json"),
        server_alignment.model_dump(mode="json")
    )
    print(f"    Result: {result['status']}")
    print(f"    Action category: {trace.action.category}")
    print(f"    Escalation required: {trace.escalation.required}")
    print(f"    Trace verified: {verification.verified}")
    if not verification.verified:
        for v in verification.violations:
            print(f"    Violation: {v.description}")
    print()

    # Step 3: Simulate escalated action without approval (write_file)
    print("[3] Simulating escalated action WITHOUT approval: write_file('/tmp/test.txt')...")
    result, trace = simulate_write_file(server_alignment, "/tmp/test.txt", "Hello world", approved=False)
    traces.append(trace)
    verification = verify_trace(
        trace.model_dump(mode="json"),
        server_alignment.model_dump(mode="json")
    )
    print(f"    Result: {result['status']}")
    print(f"    Action category: {trace.action.category}")
    print(f"    Escalation required: {trace.escalation.required}")
    print(f"    Selected action: {trace.decision.selected}")
    print(f"    Trace verified: {verification.verified}")
    print("    --> BLOCKED: Write requires principal approval")
    print()

    # Step 4: Simulate escalated action with approval (write_file)
    print("[4] Simulating escalated action WITH approval: write_file('/tmp/test.txt')...")
    result, trace = simulate_write_file(server_alignment, "/tmp/test.txt", "Hello world", approved=True)
    traces.append(trace)
    verification = verify_trace(
        trace.model_dump(mode="json"),
        server_alignment.model_dump(mode="json")
    )
    print(f"    Result: {result['status']}")
    print(f"    Bytes written: {result.get('bytes_written', 'N/A')}")
    print(f"    Action category: {trace.action.category}")
    print(f"    Escalation required: {trace.escalation.required}")
    print(f"    Principal response: {trace.escalation.principal_response.decision if trace.escalation.principal_response else 'N/A'}")
    print(f"    Trace verified: {verification.verified}")
    print("    --> ALLOWED: Write approved by principal")
    print()

    # Step 5: Simulate forbidden action (delete_file)
    print("[5] Simulating forbidden action: delete_file('/tmp/test.txt')...")
    result, trace = simulate_delete_file(server_alignment, "/tmp/test.txt")
    traces.append(trace)
    verification = verify_trace(
        trace.model_dump(mode="json"),
        server_alignment.model_dump(mode="json")
    )
    print(f"    Result: {result['status']}")
    print(f"    Reason: {result.get('reason', 'N/A')}")
    print(f"    Action category: {trace.action.category}")
    print(f"    Selected action: {trace.decision.selected}")
    print(f"    Trace verified: {verification.verified}")
    print("    --> BLOCKED: Forbidden action cannot be executed")
    print()

    # Step 6: Save all traces
    print("[6] Saving AP-Traces...")
    traces_path = Path(__file__).parent / "tool-invocation-traces.json"
    with open(traces_path, "w") as f:
        json.dump([t.model_dump(mode="json") for t in traces], f, indent=2)
    print(f"    Saved {len(traces)} traces to: {traces_path.name}")
    print()

    # Step 7: Verify all traces
    print("[7] Verifying all traces against alignment card...")
    passed = 0
    failed = 0
    card_dict = server_alignment.model_dump(mode="json")
    for trace in traces:
        result = verify_trace(trace.model_dump(mode="json"), card_dict)
        if result.verified:
            passed += 1
        else:
            failed += 1
            print(f"    FAILED: {trace.trace_id}")
            for v in result.violations:
                print(f"      - {v.description}")
    print(f"    Results: {passed} passed, {failed} failed")
    print()

    # Summary
    print("=" * 70)
    print("Summary: MCP Server with AAP Alignment")
    print("=" * 70)
    print()
    print("    This example demonstrated an MCP filesystem server with AAP alignment:")
    print()
    print("    1. BOUNDED ACTIONS (autonomous, no approval needed):")
    print("       - read_file: Successfully read file, trace verified")
    print()
    print("    2. ESCALATED ACTIONS (require principal approval):")
    print("       - write_file without approval: Blocked, returned escalation_required")
    print("       - write_file with approval: Executed, trace records approval")
    print()
    print("    3. FORBIDDEN ACTIONS (always blocked):")
    print("       - delete_file: Blocked regardless of approval")
    print()
    print("    Each invocation generated an AP-Trace that:")
    print("    - Records the tool name and category")
    print("    - Documents alternatives considered")
    print("    - Logs escalation trigger evaluation")
    print("    - Captures principal response (for escalated actions)")
    print("    - Verifies against the alignment card")
    print()
    print("Generated files:")
    print("  - server-alignment-card.json (MCP server alignment)")
    print(f"  - tool-invocation-traces.json ({len(traces)} AP-Traces)")
    print("=" * 70)


if __name__ == "__main__":
    main()
