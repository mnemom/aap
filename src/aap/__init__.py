"""Agent Alignment Protocol (AAP) — The missing alignment layer for the agent protocol stack.

AAP provides three core capabilities:
1. Alignment Card: Declare alignment posture (values, autonomy, audit commitment)
2. AP-Trace: Audit agent decisions (alternatives, reasoning, escalation)
3. Verification: Verify behavior against declarations, detect drift

Quick Start:
    from aap import AlignmentCard, APTrace, verify_trace, detect_drift

    # Verify a trace against a card
    result = verify_trace(trace_dict, card_dict)
    if not result.verified:
        for violation in result.violations:
            print(f"VIOLATION: {violation.type}")

    # Check coherence between two agents
    from aap import check_coherence
    coherence = check_coherence(my_card_dict, their_card_dict)
    if coherence.proceed:
        # Safe to coordinate
        pass

    # Detect drift over time
    alerts = detect_drift(card_dict, list_of_traces)
    for alert in alerts:
        print(f"DRIFT: {alert.analysis.drift_direction}")

    # Instrument your agent with automatic tracing
    from aap import trace_decision, TracedResult

    @trace_decision(card_path="alignment-card.json")
    def recommend_product(query: str) -> Product:
        return find_best_product(query)

See docs/SPEC.md for the full protocol specification.
"""

from importlib import metadata as _metadata

try:
    # Single source of truth: the installed distribution version (pyproject.toml).
    __version__ = _metadata.version("agent-alignment-protocol")
except _metadata.PackageNotFoundError:  # pragma: no cover - editable/source tree fallback
    __version__ = "2.0.0"

# EU AI Act compliance presets
from aap.compliance import (
    EU_COMPLIANCE_AUDIT,
    EU_COMPLIANCE_EXTENSIONS,
    EU_COMPLIANCE_VALUES,
)

# Schema models
from aap.schemas import (
    Action,
    ActionCategory,
    ActionType,
    AlignmentCard,
    AlignmentCardRequest,
    AlignmentCardResponse,
    AlignmentMode,
    Alternative,
    APTrace,
    Audit,
    Autonomy,
    CoherenceResultMessage,
    Decision,
    Escalation,
    EscalationTrigger,
    Principal,
    PrincipalType,
    ProposedCollaboration,
    RelationshipType,
    TraceContext,
    TriggerAction,
    ValueCoherenceCheck,
    Values,
)

# Tracing decorators
from aap.tracing import (
    AlignmentViolationError,
    TraceConfig,
    TracedResult,
    TraceHandler,
    clear_trace_store,
    get_trace_store,
    mcp_traced,
    trace_decision,
)

# Verification result models
from aap.verification import (
    AgentCoherenceSummary,
    CoherenceResult,
    DriftAlert,
    DriftAnalysis,
    DriftDirection,
    DriftIndicator,
    FleetCluster,
    FleetCoherenceResult,
    FleetOutlier,
    PairwiseEntry,
    Severity,
    ValueAlignment,
    ValueConflict,
    ValueDivergence,
    VerificationMetadata,
    VerificationResult,
    Violation,
    ViolationType,
    Warning,
    check_coherence,
    check_fleet_coherence,
    detect_drift,
    verify_trace,
)

__all__ = [
    # Version
    "__version__",
    # Core API
    "verify_trace",
    "check_coherence",
    "check_fleet_coherence",
    "detect_drift",
    # Tracing Decorators
    "trace_decision",
    "mcp_traced",
    "TracedResult",
    "TraceConfig",
    "TraceHandler",
    "AlignmentViolationError",
    "get_trace_store",
    "clear_trace_store",
    # Verification Results
    "VerificationResult",
    "Violation",
    "ViolationType",
    "Warning",
    "Severity",
    "VerificationMetadata",
    "CoherenceResult",
    "ValueAlignment",
    "ValueConflict",
    # Fleet Coherence (E-05)
    "FleetCoherenceResult",
    "PairwiseEntry",
    "FleetOutlier",
    "FleetCluster",
    "ValueDivergence",
    "AgentCoherenceSummary",
    "DriftAlert",
    "DriftAnalysis",
    "DriftDirection",
    "DriftIndicator",
    # Alignment Card (unified / ADR-039)
    "AlignmentCard",
    "AlignmentMode",
    "Principal",
    "PrincipalType",
    "RelationshipType",
    "Values",
    "Autonomy",
    "EscalationTrigger",
    "TriggerAction",
    "Audit",
    # AP-Trace
    "APTrace",
    "Action",
    "ActionType",
    "ActionCategory",
    "Alternative",
    "Decision",
    "Escalation",
    "TraceContext",
    # Value Coherence
    "AlignmentCardRequest",
    "AlignmentCardResponse",
    "ValueCoherenceCheck",
    "CoherenceResultMessage",
    "ProposedCollaboration",
    # EU AI Act Compliance
    "EU_COMPLIANCE_AUDIT",
    "EU_COMPLIANCE_EXTENSIONS",
    "EU_COMPLIANCE_VALUES",
]
