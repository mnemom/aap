"""Tracing decorators for automatic AP-Trace generation.

Provides decorators that wrap function execution and generate AP-Trace
audit logs per SPEC Section 5. These enable transparent instrumentation
of agent decision points.

Example:
    from aap import trace_decision

    @trace_decision(card_path="alignment-card.json")
    def recommend_product(user_query: str, budget: float) -> Product:
        # Your decision logic here
        return selected_product

    # Each call automatically generates an AP-Trace in ./traces/
"""

from __future__ import annotations

import functools
import inspect
import json
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import (
    Any,
    ParamSpec,
    Protocol,
    TypeVar,
    cast,
    overload,
)

from aap.schemas import (
    ActionCategory,
    ActionType,
)
from aap.verification import VerificationResult, verify_trace

P = ParamSpec("P")
R = TypeVar("R")


class TraceHandler(Protocol):
    """Protocol for custom trace handlers."""

    def __call__(self, trace: dict[str, Any]) -> None:
        """Handle a generated trace."""
        ...


@dataclass
class TracedResult:
    """Rich result type for functions that want to provide decision metadata.

    When a traced function returns a TracedResult, the decorator extracts
    the full decision structure including alternatives and reasoning.

    Example:
        @trace_decision(card_path="card.json")
        def choose_action(context: dict) -> TracedResult:
            options = evaluate_options(context)
            selected = options[0]

            return TracedResult(
                value=selected.execute(),
                selected_id=selected.id,
                alternatives=[
                    {"option_id": o.id, "description": o.desc, "score": o.score}
                    for o in options
                ],
                reasoning="Selected highest-scoring option within budget.",
                values_applied=["principal_benefit", "efficiency"],
                confidence=0.92,
            )
    """

    value: Any
    """The actual return value to pass through to caller."""

    selected_id: str | None = None
    """ID of selected alternative (defaults to 'selected')."""

    alternatives: list[dict[str, Any]] = field(default_factory=list)
    """List of alternatives considered (will generate defaults if empty)."""

    reasoning: str = ""
    """Human-readable explanation of the selection."""

    values_applied: list[str] = field(default_factory=list)
    """Values that influenced this decision."""

    confidence: float | None = None
    """Decision confidence score (0.0 to 1.0)."""

    action_type: ActionType = ActionType.EXECUTE
    """Type of action (execute, recommend, escalate, deny)."""

    action_category: ActionCategory = ActionCategory.BOUNDED
    """How action relates to autonomy envelope."""

    escalation_required: bool = False
    """Whether this decision required escalation."""

    escalation_reason: str = ""
    """Reason for escalation (or why not required)."""

    context_metadata: dict[str, Any] = field(default_factory=dict)
    """Additional context to include in trace."""


@dataclass
class TraceConfig:
    """Configuration for trace generation."""

    card_path: str | None = None
    """Path to Alignment Card JSON file."""

    card: dict[str, Any] | None = None
    """Alignment Card dict (alternative to card_path)."""

    output_dir: str | Path = "./traces"
    """Directory to write trace files."""

    handler: TraceHandler | None = None
    """Custom handler for traces (overrides file output)."""

    auto_verify: bool = False
    """Verify each trace against the card."""

    raise_on_violation: bool = False
    """Raise exception if verification fails (requires auto_verify)."""

    default_values: list[str] = field(default_factory=list)
    """Default values_applied if not provided by function."""

    agent_id: str = ""
    """Agent ID for traces (auto-generated if empty)."""

    session_id: str | None = None
    """Session ID to include in trace context."""

    include_args: bool = False
    """Include function arguments in action.parameters.

    WARNING: When set to True, all function arguments are serialized into the
    trace output. This may inadvertently leak sensitive data (PII, credentials,
    API keys, etc.) into trace files. Only enable this when you are certain that
    function arguments do not contain sensitive information, or when traces are
    stored in a secure, access-controlled location.
    """

    include_return_repr: bool = False
    """Include repr of return value in trace (may leak data)."""


# Global trace storage for testing and inspection
_trace_store: list[dict[str, Any]] = []


def get_trace_store() -> list[dict[str, Any]]:
    """Get the in-memory trace store for testing."""
    return _trace_store


def clear_trace_store() -> None:
    """Clear the in-memory trace store."""
    _trace_store.clear()


def _load_card(config: TraceConfig) -> dict[str, Any]:
    """Load alignment card from config."""
    if config.card is not None:
        return config.card

    if config.card_path is not None:
        path = Path(config.card_path)
        if not path.exists():
            raise FileNotFoundError(f"Alignment card not found: {config.card_path}")
        with open(path) as f:
            return cast("dict[str, Any]", json.load(f))

    raise ValueError("Either card or card_path must be provided")


def _serialize_arg(value: Any) -> Any:
    """Serialize a function argument for inclusion in trace."""
    # Handle common types
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (list, tuple)):
        return [_serialize_arg(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _serialize_arg(v) for k, v in value.items()}
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if hasattr(value, "__dict__"):
        return {k: _serialize_arg(v) for k, v in value.__dict__.items() if not k.startswith("_")}
    # Fallback to string representation
    return str(value)


def _extract_parameters(
    func: Callable[..., Any],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> dict[str, Any]:
    """Extract function parameters as a serializable dict."""
    sig = inspect.signature(func)
    bound = sig.bind(*args, **kwargs)
    bound.apply_defaults()

    params = {}
    for name, value in bound.arguments.items():
        # Skip self/cls for methods
        if name in ("self", "cls"):
            continue
        params[name] = _serialize_arg(value)

    return params


def _build_trace(
    func: Callable[..., Any],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    result: Any,
    config: TraceConfig,
    card: dict[str, Any],
    start_time: datetime,
    end_time: datetime,
) -> dict[str, Any]:
    """Build an AP-Trace dict from function execution."""
    trace_id = f"tr-{uuid.uuid4().hex[:12]}"
    card_id = card.get("card_id", "")
    agent_id = config.agent_id or card.get("agent_id", f"agent-{uuid.uuid4().hex[:8]}")

    # Extract action name from function
    action_name = func.__name__

    # Build parameters if configured
    parameters = None
    if config.include_args:
        parameters = _extract_parameters(func, args, kwargs)

    # Handle TracedResult for rich decision data
    if isinstance(result, TracedResult):
        traced = result
        actual_value = traced.value
        selected_id = traced.selected_id or "selected"
        alternatives = traced.alternatives or [
            {"option_id": selected_id, "description": f"Selected by {action_name}"}
        ]
        reasoning = traced.reasoning or f"Selected by {action_name}"
        values_applied = traced.values_applied or config.default_values or []
        confidence = traced.confidence
        action_type = traced.action_type
        action_category = traced.action_category
        escalation_required = traced.escalation_required
        escalation_reason = traced.escalation_reason or (
            "Escalation required" if escalation_required else "No escalation required"
        )
        context_metadata = traced.context_metadata
    else:
        # Simple mode: generate minimal decision structure
        actual_value = result
        selected_id = "selected"
        alternatives = [{"option_id": "selected", "description": f"Result of {action_name}"}]
        reasoning = f"Executed {action_name}"
        values_applied = config.default_values or []
        confidence = None
        action_type = ActionType.EXECUTE
        action_category = ActionCategory.BOUNDED
        escalation_required = False
        escalation_reason = "No escalation triggers evaluated"
        context_metadata = {}

    # Build the trace dict (using dict for flexibility, not Pydantic model)
    trace: dict[str, Any] = {
        "trace_id": trace_id,
        "agent_id": agent_id,
        "card_id": card_id,
        "timestamp": end_time.isoformat(),
        "action": {
            "type": action_type.value if isinstance(action_type, ActionType) else action_type,
            "name": action_name,
            "category": action_category.value
            if isinstance(action_category, ActionCategory)
            else action_category,
        },
        "decision": {
            "alternatives_considered": [
                {
                    "option_id": alt.get("option_id", f"opt-{i}"),
                    "description": alt.get("description", ""),
                    "score": alt.get("score"),
                }
                for i, alt in enumerate(alternatives)
            ],
            "selected": selected_id,
            "selection_reasoning": reasoning,
            "values_applied": values_applied,
        },
        "escalation": {
            "evaluated": True,
            "required": escalation_required,
            "reason": escalation_reason,
        },
    }

    # Add optional fields
    if parameters:
        trace["action"]["parameters"] = parameters

    if confidence is not None:
        trace["decision"]["confidence"] = confidence

    # Add context
    context: dict[str, Any] = {}
    if config.session_id:
        context["session_id"] = config.session_id
    if context_metadata:
        context["metadata"] = context_metadata
    context["metadata"] = context.get("metadata", {})
    context["metadata"]["execution_time_ms"] = round(
        (end_time - start_time).total_seconds() * 1000, 2
    )

    if context:
        trace["context"] = context

    # Optionally include return value representation
    if config.include_return_repr:
        trace["context"] = trace.get("context", {})
        trace["context"]["metadata"] = trace["context"].get("metadata", {})
        trace["context"]["metadata"]["return_repr"] = repr(actual_value)[:500]

    return trace


def _write_trace(trace: dict[str, Any], config: TraceConfig) -> Path | None:
    """Write trace to file or handler."""
    # Store in memory for testing
    _trace_store.append(trace)

    # Custom handler takes precedence
    if config.handler is not None:
        config.handler(trace)
        return None

    # Write to file
    import os

    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    # Ensure restrictive directory permissions (umask may weaken mode= arg)
    os.chmod(output_dir, 0o700)

    filename = f"{trace['trace_id']}.json"
    filepath = output_dir / filename

    with open(filepath, "w") as f:
        json.dump(trace, f, indent=2, default=str)
    # Restrict file permissions to owner-only read/write
    os.chmod(filepath, 0o600)

    return filepath


def _verify_and_handle(
    trace: dict[str, Any],
    card: dict[str, Any],
    config: TraceConfig,
) -> VerificationResult:
    """Verify trace and optionally raise on violation."""
    result = verify_trace(trace, card)

    if not result.verified and config.raise_on_violation:
        violations = ", ".join(v.description for v in result.violations)
        raise AlignmentViolationError(
            f"Trace {trace['trace_id']} failed verification: {violations}",
            result=result,
        )

    return result


class AlignmentViolationError(Exception):
    """Raised when a trace fails verification and raise_on_violation is True."""

    def __init__(self, message: str, result: VerificationResult) -> None:
        super().__init__(message)
        self.result = result


# Type-preserving decorator overloads
@overload
def trace_decision(
    func: Callable[P, R],
) -> Callable[P, R]: ...


@overload
def trace_decision(
    *,
    card_path: str | None = None,
    card: dict[str, Any] | None = None,
    output_dir: str | Path = "./traces",
    handler: TraceHandler | None = None,
    auto_verify: bool = False,
    raise_on_violation: bool = False,
    default_values: list[str] | None = None,
    agent_id: str = "",
    session_id: str | None = None,
    include_args: bool = False,
    include_return_repr: bool = False,
) -> Callable[[Callable[P, R]], Callable[P, R]]: ...


def trace_decision(
    func: Callable[P, R] | None = None,
    *,
    card_path: str | None = None,
    card: dict[str, Any] | None = None,
    output_dir: str | Path = "./traces",
    handler: TraceHandler | None = None,
    auto_verify: bool = False,
    raise_on_violation: bool = False,
    default_values: list[str] | None = None,
    agent_id: str = "",
    session_id: str | None = None,
    include_args: bool = False,
    include_return_repr: bool = False,
) -> Callable[P, R] | Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator that generates AP-Traces for function calls.

    Wraps a function to automatically generate an AP-Trace audit entry
    for each invocation. The trace captures the function name, parameters,
    return value, and timing information.

    For richer traces with alternatives and reasoning, have your function
    return a TracedResult object instead of a raw value.

    Args:
        card_path: Path to Alignment Card JSON file.
        card: Alignment Card dict (alternative to card_path).
        output_dir: Directory to write trace files (default: ./traces/).
        handler: Custom trace handler (overrides file output).
        auto_verify: Verify each trace against the card (default: False).
        raise_on_violation: Raise AlignmentViolationError on verification
            failure (requires auto_verify=True).
        default_values: Default values_applied if not provided by function.
        agent_id: Agent ID for traces (auto-generated if empty).
        session_id: Session ID to include in trace context.
        include_args: Include function arguments in action.parameters (default: False).
            WARNING: When True, all function arguments are serialized into trace
            output, which may leak sensitive data (PII, credentials, API keys).
        include_return_repr: Include repr of return value (default: False).

    Returns:
        Decorated function that generates traces.

    Raises:
        ValueError: If neither card nor card_path is provided.
        FileNotFoundError: If card_path doesn't exist.
        AlignmentViolationError: If auto_verify and raise_on_violation are True
            and the trace fails verification.

    Example:
        # Simple usage with card file
        @trace_decision(card_path="alignment-card.json")
        def recommend_product(query: str) -> Product:
            return find_best_product(query)

        # With auto-verification that raises on violations
        @trace_decision(
            card_path="alignment-card.json",
            auto_verify=True,
            raise_on_violation=True,
        )
        def execute_trade(symbol: str, amount: float) -> TradeResult:
            return broker.execute(symbol, amount)

        # Rich tracing with alternatives
        @trace_decision(card_path="alignment-card.json")
        def choose_response(context: dict) -> TracedResult:
            options = generate_options(context)
            selected = rank_and_select(options)
            return TracedResult(
                value=selected.text,
                selected_id=selected.id,
                alternatives=[
                    {"option_id": o.id, "description": o.text, "score": o.score}
                    for o in options
                ],
                reasoning="Selected response with highest helpfulness score.",
                values_applied=["principal_benefit", "transparency"],
                confidence=0.88,
            )
    """
    config = TraceConfig(
        card_path=card_path,
        card=card,
        output_dir=output_dir,
        handler=handler,
        auto_verify=auto_verify,
        raise_on_violation=raise_on_violation,
        default_values=default_values or [],
        agent_id=agent_id,
        session_id=session_id,
        include_args=include_args,
        include_return_repr=include_return_repr,
    )

    def decorator(fn: Callable[P, R]) -> Callable[P, R]:
        # Load card at decoration time for validation (lazy load on first call if needed)
        loaded_card: dict[str, Any] | None = None

        def get_card() -> dict[str, Any]:
            nonlocal loaded_card
            if loaded_card is None:
                loaded_card = _load_card(config)
            return loaded_card

        if inspect.iscoroutinefunction(fn):

            @functools.wraps(fn)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                card_dict = get_card()
                start_time = datetime.now(timezone.utc)

                result = await fn(*args, **kwargs)

                end_time = datetime.now(timezone.utc)

                trace = _build_trace(
                    fn, args, kwargs, result, config, card_dict, start_time, end_time
                )
                _write_trace(trace, config)

                if config.auto_verify:
                    _verify_and_handle(trace, card_dict, config)

                # Return the actual value, not TracedResult
                if isinstance(result, TracedResult):
                    return cast("R", result.value)
                return cast("R", result)

            return async_wrapper  # type: ignore[return-value]
        else:

            @functools.wraps(fn)
            def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                card_dict = get_card()
                start_time = datetime.now(timezone.utc)

                result = fn(*args, **kwargs)

                end_time = datetime.now(timezone.utc)

                trace = _build_trace(
                    fn, args, kwargs, result, config, card_dict, start_time, end_time
                )
                _write_trace(trace, config)

                if config.auto_verify:
                    _verify_and_handle(trace, card_dict, config)

                # Return the actual value, not TracedResult
                if isinstance(result, TracedResult):
                    return cast("R", result.value)
                return result

            return sync_wrapper

    # Handle @trace_decision without parentheses (requires card to be set elsewhere)
    if func is not None:
        return decorator(func)

    return decorator


def mcp_traced(
    *,
    card_path: str | None = None,
    card: dict[str, Any] | None = None,
    output_dir: str | Path = "./traces",
    handler: TraceHandler | None = None,
    auto_verify: bool = False,
    raise_on_violation: bool = False,
    default_values: list[str] | None = None,
    tool_name: str | None = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator for MCP tool functions.

    Similar to @trace_decision but tailored for MCP (Model Context Protocol)
    tool functions. Automatically extracts tool name and structures traces
    according to MCP conventions.

    Args:
        card_path: Path to Alignment Card JSON file.
        card: Alignment Card dict (alternative to card_path).
        output_dir: Directory to write trace files.
        handler: Custom trace handler.
        auto_verify: Verify each trace against the card.
        raise_on_violation: Raise on verification failure.
        default_values: Default values_applied.
        tool_name: Override tool name (defaults to function name).

    Returns:
        Decorated MCP tool function.

    Example:
        @mcp_traced(card_path="alignment-card.json", tool_name="search_files")
        async def search_files(query: str, path: str = ".") -> list[str]:
            return await perform_search(query, path)
    """
    config = TraceConfig(
        card_path=card_path,
        card=card,
        output_dir=output_dir,
        handler=handler,
        auto_verify=auto_verify,
        raise_on_violation=raise_on_violation,
        default_values=default_values or [],
        include_args=True,
    )

    def decorator(fn: Callable[P, R]) -> Callable[P, R]:
        loaded_card: dict[str, Any] | None = None

        def get_card() -> dict[str, Any]:
            nonlocal loaded_card
            if loaded_card is None:
                loaded_card = _load_card(config)
            return loaded_card

        # Use provided tool name or derive from function
        effective_tool_name = tool_name or fn.__name__

        if inspect.iscoroutinefunction(fn):

            @functools.wraps(fn)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                card_dict = get_card()
                start_time = datetime.now(timezone.utc)

                result = await fn(*args, **kwargs)

                end_time = datetime.now(timezone.utc)

                # Build MCP-specific trace
                trace = _build_mcp_trace(
                    fn,
                    effective_tool_name,
                    args,
                    kwargs,
                    result,
                    config,
                    card_dict,
                    start_time,
                    end_time,
                )
                _write_trace(trace, config)

                if config.auto_verify:
                    _verify_and_handle(trace, card_dict, config)

                return cast("R", result)

            return async_wrapper  # type: ignore[return-value]
        else:

            @functools.wraps(fn)
            def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                card_dict = get_card()
                start_time = datetime.now(timezone.utc)

                result = fn(*args, **kwargs)

                end_time = datetime.now(timezone.utc)

                trace = _build_mcp_trace(
                    fn,
                    effective_tool_name,
                    args,
                    kwargs,
                    result,
                    config,
                    card_dict,
                    start_time,
                    end_time,
                )
                _write_trace(trace, config)

                if config.auto_verify:
                    _verify_and_handle(trace, card_dict, config)

                return result

            return sync_wrapper

    return decorator


def _build_mcp_trace(
    func: Callable[..., Any],
    tool_name: str,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    result: Any,
    config: TraceConfig,
    card: dict[str, Any],
    start_time: datetime,
    end_time: datetime,
) -> dict[str, Any]:
    """Build an AP-Trace for an MCP tool call."""
    trace_id = f"tr-mcp-{uuid.uuid4().hex[:12]}"
    card_id = card.get("card_id", "")
    agent_id = config.agent_id or card.get("agent_id", f"mcp-agent-{uuid.uuid4().hex[:8]}")

    parameters = _extract_parameters(func, args, kwargs)

    trace: dict[str, Any] = {
        "trace_id": trace_id,
        "agent_id": agent_id,
        "card_id": card_id,
        "timestamp": end_time.isoformat(),
        "action": {
            "type": ActionType.EXECUTE.value,
            "name": tool_name,
            "category": ActionCategory.BOUNDED.value,
            "parameters": parameters,
        },
        "decision": {
            "alternatives_considered": [
                {
                    "option_id": "execute",
                    "description": f"Execute MCP tool: {tool_name}",
                }
            ],
            "selected": "execute",
            "selection_reasoning": f"MCP tool {tool_name} invoked by caller",
            "values_applied": config.default_values or [],
        },
        "escalation": {
            "evaluated": True,
            "required": False,
            "reason": "MCP tool execution does not require escalation",
        },
        "context": {
            "metadata": {
                "mcp_tool": True,
                "tool_name": tool_name,
                "execution_time_ms": round((end_time - start_time).total_seconds() * 1000, 2),
            }
        },
    }

    return trace
