"""AAP CLI — Command line interface for Agent Alignment Protocol.

Usage:
    aap init --values "principal_benefit,transparency"
    aap verify --card alignment-card.json --trace trace.json
    aap check-coherence --my-card my-card.json --their-card vendor-card.json
    aap drift --card alignment-card.json --traces ./traces/
"""

from __future__ import annotations

import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

import click


# ANSI color codes for output formatting
class Colors:
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def success(msg: str) -> str:
    """Format success message."""
    return f"{Colors.GREEN}\u2713{Colors.RESET} {msg}"


def warning(msg: str) -> str:
    """Format warning message."""
    return f"{Colors.YELLOW}\u26a0{Colors.RESET} {msg}"


def error(msg: str) -> str:
    """Format error message."""
    return f"{Colors.RED}\u2717{Colors.RESET} {msg}"


def info(msg: str) -> str:
    """Format info message."""
    return f"{Colors.BLUE}\u2139{Colors.RESET} {msg}"


def bold(msg: str) -> str:
    """Format bold message."""
    return f"{Colors.BOLD}{msg}{Colors.RESET}"


# Standard values from the SPEC
STANDARD_VALUES = [
    "principal_benefit",
    "transparency",
    "minimal_data",
    "harm_prevention",
    "honesty",
    "user_control",
    "privacy",
    "fairness",
]

STANDARD_VALUE_DESCRIPTIONS = {
    "principal_benefit": "Prioritize the interests of the principal (user/organization)",
    "transparency": "Be open about capabilities, limitations, and decision-making",
    "minimal_data": "Collect and retain only necessary data",
    "harm_prevention": "Avoid actions that could cause harm",
    "honesty": "Provide accurate and truthful information",
    "user_control": "Respect user autonomy and control over their data",
    "privacy": "Protect personal and sensitive information",
    "fairness": "Treat all users equitably without discrimination",
}


@click.group()
@click.version_option(package_name="agent-alignment-protocol", message="%(prog)s %(version)s")
def main() -> None:
    """AAP — Agent Alignment Protocol CLI.

    Tools for creating, verifying, and analyzing agent alignment.

    \b
    Examples:
        aap init --values "principal_benefit,transparency"
        aap verify --card card.json --trace trace.json
        aap check-coherence --my-card mine.json --their-card theirs.json
        aap drift --card card.json --traces ./traces/
    """
    pass


@main.command("init")
@click.option(
    "--values",
    "-v",
    type=str,
    help="Comma-separated list of values (e.g., 'principal_benefit,transparency')",
)
@click.option(
    "--interactive",
    "-i",
    is_flag=True,
    help="Interactive mode: guided Alignment Card creation",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default="alignment-card.json",
    help="Output file path (default: alignment-card.json)",
)
@click.option(
    "--agent-id",
    type=str,
    help="Agent identifier (default: auto-generated UUID)",
)
@click.option(
    "--card-id",
    type=str,
    help="Card identifier (default: auto-generated UUID)",
)
def init_cmd(
    values: str | None,
    interactive: bool,
    output: str,
    agent_id: str | None,
    card_id: str | None,
) -> None:
    """Create a new Alignment Card.

    \b
    Non-interactive:
        aap init --values "principal_benefit,transparency"

    \b
    Interactive:
        aap init --interactive
    """
    if not values and not interactive:
        click.echo(error("Either --values or --interactive is required"))
        click.echo(info("Run 'aap init --help' for usage"))
        sys.exit(1)

    if interactive:
        card_dict = _create_card_interactive(agent_id, card_id)
    else:
        # Non-interactive path is guarded above (`if not values and not
        # interactive: sys.exit(1)`), so `values` is guaranteed non-None here.
        assert values is not None
        value_list = [v.strip() for v in values.split(",") if v.strip()]
        if not value_list:
            click.echo(error("No values provided"))
            sys.exit(1)

        # Validate values
        invalid_values = [v for v in value_list if v not in STANDARD_VALUES]
        if invalid_values:
            click.echo(warning(f"Non-standard values will require definitions: {invalid_values}"))

        card_dict = _create_card_from_values(value_list, agent_id, card_id)

    # Validate card by parsing with Pydantic
    try:
        from aap.schemas import AlignmentCard

        card = AlignmentCard.model_validate(card_dict)
        validated_dict = card.model_dump(mode="json", exclude_none=True)
    except Exception as e:
        click.echo(error(f"Card validation failed: {e}"))
        sys.exit(1)

    # Write to file
    output_path = Path(output)
    try:
        with open(output_path, "w") as f:
            json.dump(validated_dict, f, indent=2, default=str)
        click.echo(success(f"Created {output_path}"))
    except OSError as e:
        click.echo(error(f"Failed to write file: {e}"))
        sys.exit(1)


def _create_card_from_values(
    value_list: list[str],
    agent_id: str | None = None,
    card_id: str | None = None,
) -> dict[str, Any]:
    """Create a minimal Alignment Card (unified / ADR-039) from a list of values."""
    now = datetime.now(timezone.utc)
    resolved_agent_id = agent_id or f"agent-{uuid.uuid4().hex[:8]}"
    return {
        "card_version": "unified/2026-04-26",
        "card_id": card_id or f"ac-{uuid.uuid4().hex[:12]}",
        "agent_id": resolved_agent_id,
        "issued_at": now.isoformat(),
        "autonomy_mode": "observe",
        "integrity_mode": "observe",
        "principal": {
            "type": "human",
            "identifier": resolved_agent_id,
            "relationship": "delegated_authority",
        },
        "values": {
            "declared": value_list,
        },
        "autonomy": {
            "bounded_actions": ["search", "recommend", "compare", "summarize", "respond"],
            "escalation_triggers": [
                {
                    "condition": 'action_type == "purchase"',
                    "action": "escalate",
                    "reason": "Financial transactions require approval",
                },
                {
                    "condition": "amount > 100",
                    "action": "escalate",
                    "reason": "High-value actions require approval",
                },
            ],
        },
        "audit": {
            "trace_format": "ap-trace-v1",
            "retention_days": 90,
            "queryable": False,
        },
    }


def _create_card_interactive(
    agent_id: str | None = None, card_id: str | None = None
) -> dict[str, Any]:
    """Create an Alignment Card through interactive prompts."""
    click.echo(bold("\nAAP Alignment Card Creator\n"))

    # Values selection
    click.echo("Select values for your agent (space-separated numbers):\n")
    for i, value in enumerate(STANDARD_VALUES, 1):
        desc = STANDARD_VALUE_DESCRIPTIONS.get(value, "")
        click.echo(f"  {i}. {value}")
        click.echo(f"     {Colors.CYAN}{desc}{Colors.RESET}\n")

    selection = click.prompt(
        "Enter numbers (e.g., '1 2 3')",
        type=str,
        default="1 2",
    )

    try:
        indices = [int(x.strip()) for x in selection.split() if x.strip()]
        selected_values = [
            STANDARD_VALUES[i - 1] for i in indices if 1 <= i <= len(STANDARD_VALUES)
        ]
    except (ValueError, IndexError):
        click.echo(warning("Invalid selection, using defaults"))
        selected_values = ["principal_benefit", "transparency"]

    if not selected_values:
        selected_values = ["principal_benefit", "transparency"]

    click.echo(f"\nSelected values: {', '.join(selected_values)}\n")

    # Principal type
    principal_type = click.prompt(
        "Principal type",
        type=click.Choice(["human", "organization", "agent"]),
        default="human",
    )

    # Principal identifier (required by the unified schema when type != unspecified)
    default_identifier = agent_id or f"agent-{uuid.uuid4().hex[:8]}"
    principal_identifier = click.prompt(
        "Principal identifier (DID, email, org ID)",
        default=default_identifier,
    )

    # Relationship type
    relationship = click.prompt(
        "Relationship type",
        type=click.Choice(["delegated_authority", "advisory", "autonomous"]),
        default="delegated_authority",
    )

    # Bounded actions
    bounded_input = click.prompt(
        "Bounded actions (comma-separated)",
        default="search,recommend,respond",
    )
    bounded_actions = [a.strip() for a in bounded_input.split(",") if a.strip()]

    # Retention days
    retention_days = click.prompt(
        "Audit retention days",
        type=int,
        default=90,
    )

    now = datetime.now(timezone.utc)
    return {
        "card_version": "unified/2026-04-26",
        "card_id": card_id or f"ac-{uuid.uuid4().hex[:12]}",
        "agent_id": agent_id or default_identifier,
        "issued_at": now.isoformat(),
        "autonomy_mode": "observe",
        "integrity_mode": "observe",
        "principal": {
            "type": principal_type,
            "identifier": principal_identifier,
            "relationship": relationship,
        },
        "values": {
            "declared": selected_values,
        },
        "autonomy": {
            "bounded_actions": bounded_actions,
            "escalation_triggers": [
                {
                    "condition": 'action_type == "purchase"',
                    "action": "escalate",
                    "reason": "Financial transactions require approval",
                },
            ],
        },
        "audit": {
            "trace_format": "ap-trace-v1",
            "retention_days": retention_days,
            "queryable": False,
        },
    }


@main.command("verify")
@click.option(
    "--card",
    "-c",
    type=click.Path(exists=True),
    required=True,
    help="Path to Alignment Card JSON file",
)
@click.option(
    "--trace",
    "-t",
    type=click.Path(exists=True),
    help="Path to single AP-Trace JSON file",
)
@click.option(
    "--traces",
    "-T",
    type=click.Path(exists=True),
    help="Path to directory containing AP-Trace JSON files",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed verification info (checks performed, timing)",
)
def verify_cmd(card: str, trace: str | None, traces: str | None, verbose: bool) -> None:
    """Verify AP-Traces against an Alignment Card.

    \b
    Single trace:
        aap verify --card card.json --trace trace.json

    \b
    Directory of traces:
        aap verify --card card.json --traces ./traces/
    """
    if not trace and not traces:
        click.echo(error("Either --trace or --traces is required"))
        sys.exit(1)

    # Load card
    try:
        card_dict = _load_json(card)
    except Exception as e:
        click.echo(error(f"Failed to load card: {e}"))
        sys.exit(1)

    # Collect trace files
    trace_files: list[Path] = []
    if trace:
        trace_files.append(Path(trace))
    if traces:
        traces_path = Path(traces)
        if traces_path.is_dir():
            trace_files.extend(sorted(traces_path.glob("*.json")))
        else:
            trace_files.append(traces_path)

    if not trace_files:
        click.echo(error("No trace files found"))
        sys.exit(1)

    # Import verification function
    from aap import verify_trace

    # Verify each trace
    total = len(trace_files)
    passed = 0
    failed = 0
    warnings_count = 0

    click.echo(bold(f"\nVerifying {total} trace(s) against {card}...\n"))

    for trace_path in trace_files:
        try:
            trace_dict = _load_json(str(trace_path))
        except Exception as e:
            click.echo(error(f"{trace_path.name}: Failed to load - {e}"))
            failed += 1
            continue

        result = verify_trace(trace_dict, card_dict)

        # Show similarity score for all results
        sim_display = f"[similarity: {result.similarity_score:.2f}]"

        if result.verified:
            passed += 1
            if result.warnings:
                warnings_count += len(result.warnings)
                click.echo(
                    warning(
                        f"{trace_path.name}: Passed with {len(result.warnings)} warning(s) {Colors.CYAN}{sim_display}{Colors.RESET}"
                    )
                )
                for w in result.warnings:
                    click.echo(f"    {w.type}: {w.description}")
            else:
                click.echo(
                    success(f"{trace_path.name}: Passed {Colors.CYAN}{sim_display}{Colors.RESET}")
                )
        else:
            failed += 1
            click.echo(
                error(
                    f"{trace_path.name}: {len(result.violations)} violation(s) {Colors.CYAN}{sim_display}{Colors.RESET}"
                )
            )
            for v in result.violations:
                click.echo(f"    {Colors.RED}{v.type.value}{Colors.RESET}: {v.description}")

        # Verbose output
        if verbose and result.verification_metadata:
            meta = result.verification_metadata
            click.echo(f"    {Colors.CYAN}checks: {', '.join(meta.checks_performed)}{Colors.RESET}")
            click.echo(f"    {Colors.CYAN}duration: {meta.duration_ms:.1f}ms{Colors.RESET}")

    # Summary
    click.echo(bold("\n--- Summary ---"))
    click.echo(f"Total:    {total}")
    click.echo(success(f"Passed:   {passed}"))
    if warnings_count > 0:
        click.echo(warning(f"Warnings: {warnings_count}"))
    if failed > 0:
        click.echo(error(f"Failed:   {failed}"))

    if verbose:
        click.echo(
            f"\n{Colors.CYAN}Verification checks: card_reference, card_expiration, autonomy, forbidden, escalation, values, behavioral_similarity{Colors.RESET}"
        )

    sys.exit(0 if failed == 0 else 1)


@main.command("check-coherence")
@click.option(
    "--my-card",
    "-m",
    type=click.Path(exists=True),
    required=True,
    help="Path to your Alignment Card JSON file",
)
@click.option(
    "--their-card",
    "-t",
    type=click.Path(exists=True),
    required=True,
    help="Path to their Alignment Card JSON file",
)
@click.option(
    "--task-values",
    type=str,
    help="Comma-separated list of values required for the task",
)
def check_coherence_cmd(
    my_card: str,
    their_card: str,
    task_values: str | None,
) -> None:
    """Check value coherence between two Alignment Cards.

    \b
    Example:
        aap check-coherence --my-card mine.json --their-card vendor.json
    """
    # Load cards
    try:
        my_card_dict = _load_json(my_card)
        their_card_dict = _load_json(their_card)
    except Exception as e:
        click.echo(error(f"Failed to load cards: {e}"))
        sys.exit(1)

    # Parse task values if provided
    task_value_list = None
    if task_values:
        task_value_list = [v.strip() for v in task_values.split(",") if v.strip()]

    # Check coherence
    from aap import check_coherence

    result = check_coherence(my_card_dict, their_card_dict, task_value_list)

    # Display results
    click.echo(bold("\n--- Coherence Check ---\n"))

    if result.compatible:
        click.echo(success("Compatible: Yes"))
    else:
        click.echo(error("Compatible: No"))

    click.echo(f"Score: {Colors.CYAN}{result.score:.2f}{Colors.RESET}")

    if result.value_alignment.matched:
        click.echo(f"Matched values: {', '.join(result.value_alignment.matched)}")

    if result.value_alignment.unmatched:
        click.echo(warning(f"Unmatched values: {', '.join(result.value_alignment.unmatched)}"))

    if result.value_alignment.conflicts:
        click.echo(error("Conflicts:"))
        for conflict in result.value_alignment.conflicts:
            click.echo(f"  - {conflict.description}")

    if result.proceed:
        click.echo(success("\nProceed: Yes"))
    else:
        click.echo(error("\nProceed: No"))
        if result.proposed_resolution:
            click.echo(f"Resolution: {result.proposed_resolution}")

    sys.exit(0 if result.proceed else 1)


@main.command("drift")
@click.option(
    "--card",
    "-c",
    type=click.Path(exists=True),
    required=True,
    help="Path to Alignment Card JSON file",
)
@click.option(
    "--traces",
    "-t",
    type=click.Path(exists=True),
    required=True,
    help="Path to directory containing AP-Trace JSON files (chronological order)",
)
@click.option(
    "--threshold",
    type=float,
    default=0.30,
    help="Similarity threshold for drift detection (default: 0.30)",
)
@click.option(
    "--sustained",
    type=int,
    default=3,
    help="Number of sustained low-similarity traces to trigger alert (default: 3)",
)
def drift_cmd(
    card: str,
    traces: str,
    threshold: float,
    sustained: int,
) -> None:
    """Detect behavioral drift from declared alignment.

    Analyzes traces chronologically to detect sustained deviation from
    the declared alignment posture.

    \b
    Example:
        aap drift --card card.json --traces ./traces/
    """
    # Load card
    try:
        card_dict = _load_json(card)
    except Exception as e:
        click.echo(error(f"Failed to load card: {e}"))
        sys.exit(1)

    # Load traces
    traces_path = Path(traces)
    if traces_path.is_dir():
        trace_files = sorted(traces_path.glob("*.json"))
    else:
        click.echo(error("--traces must be a directory"))
        sys.exit(1)

    if not trace_files:
        click.echo(error("No trace files found"))
        sys.exit(1)

    trace_list: list[dict[str, Any]] = []
    for tf in trace_files:
        try:
            trace_list.append(_load_json(str(tf)))
        except Exception as e:
            click.echo(warning(f"Skipping {tf.name}: {e}"))

    if not trace_list:
        click.echo(error("No valid traces loaded"))
        sys.exit(1)

    click.echo(bold(f"\nAnalyzing {len(trace_list)} traces for drift...\n"))

    # Detect drift
    from aap import detect_drift

    alerts = detect_drift(
        card_dict,
        trace_list,
        similarity_threshold=threshold,
        sustained_threshold=sustained,
    )

    if not alerts:
        click.echo(success("No drift detected"))
        sys.exit(0)

    # Display alerts
    click.echo(error(f"Detected {len(alerts)} drift alert(s):\n"))

    for i, alert in enumerate(alerts, 1):
        click.echo(f"{Colors.RED}Alert {i}{Colors.RESET}")
        if alert.trace_ids:
            click.echo(
                f"  Traces involved: {', '.join(alert.trace_ids[:3])}{'...' if len(alert.trace_ids) > 3 else ''}"
            )
        click.echo(
            f"  Direction: {Colors.YELLOW}{alert.analysis.drift_direction.value}{Colors.RESET}"
        )
        click.echo(f"  Similarity: {alert.analysis.similarity_score:.2f}")
        click.echo(f"  Sustained: {alert.analysis.sustained_traces} traces")

        if alert.analysis.specific_indicators:
            click.echo("  Indicators:")
            for ind in alert.analysis.specific_indicators:
                click.echo(f"    - {ind.description}")

        click.echo()

    sys.exit(1)


def _load_json(path: str) -> dict[str, Any]:
    """Load JSON file."""
    with open(path) as f:
        return cast("dict[str, Any]", json.load(f))


if __name__ == "__main__":
    main()
