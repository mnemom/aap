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

See docs/SPEC.md for the full protocol specification.
"""

__version__ = "0.1.0"

# Core verification API
# Schema models
from aap.schemas import (
    # AP-Trace
    Action,
    ActionCategory,
    ActionType,
    # Alignment Card
    AlignmentCard,
    # Value Coherence Handshake
    AlignmentCardRequest,
    AlignmentCardResponse,
    Alternative,
    APTrace,
    AuditCommitment,
    AutonomyEnvelope,
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

# Verification result models
from aap.verification import (
    CoherenceResult,
    DriftAlert,
    DriftAnalysis,
    DriftDirection,
    DriftIndicator,
    Severity,
    ValueAlignment,
    ValueConflict,
    VerificationMetadata,
    VerificationResult,
    Violation,
    ViolationType,
    Warning,
    check_coherence,
    detect_drift,
    verify_trace,
)

__all__ = [
    # Version
    "__version__",
    # Core API
    "verify_trace",
    "check_coherence",
    "detect_drift",
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
    "DriftAlert",
    "DriftAnalysis",
    "DriftDirection",
    "DriftIndicator",
    # Alignment Card
    "AlignmentCard",
    "Principal",
    "PrincipalType",
    "RelationshipType",
    "Values",
    "AutonomyEnvelope",
    "EscalationTrigger",
    "TriggerAction",
    "AuditCommitment",
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
]
