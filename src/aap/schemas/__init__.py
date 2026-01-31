"""AAP Schemas — Pydantic models for the Agent Alignment Protocol.

This module provides validated Pydantic models for:
- AlignmentCard: Agent alignment declaration (SPEC Section 4)
- APTrace: Audit log entry (SPEC Section 5)
- Value Coherence messages: Handshake protocol (SPEC Section 6)

All models support:
- JSON serialization via .to_dict() / .from_dict()
- JSON Schema generation via .model_json_schema()
- Validation via Pydantic

Example:
    from aap.schemas import AlignmentCard, APTrace

    # Create an Alignment Card
    card = AlignmentCard(
        card_id="ac-12345",
        agent_id="did:web:agent.example.com",
        issued_at=datetime.utcnow(),
        principal=Principal(type=PrincipalType.HUMAN, relationship=RelationshipType.DELEGATED_AUTHORITY),
        values=Values(declared=["principal_benefit", "transparency"]),
        autonomy_envelope=AutonomyEnvelope(...),
        audit_commitment=AuditCommitment(...),
    )

    # Serialize to JSON
    card_json = card.to_dict()

    # Validate and parse JSON
    card = AlignmentCard.from_dict(card_json)
"""

from aap.schemas.alignment_card import (
    AlignmentCard,
    AuditCommitment,
    AuditStorage,
    AutonomyEnvelope,
    EscalationTrigger,
    HierarchyType,
    MonetaryValue,
    Principal,
    PrincipalType,
    RelationshipType,
    StorageType,
    TamperEvidence,
    TriggerAction,
    ValueDefinition,
    Values,
)
from aap.schemas.ap_trace import (
    Action,
    ActionCategory,
    ActionTarget,
    ActionType,
    Alternative,
    APTrace,
    Decision,
    Escalation,
    EscalationStatus,
    PrincipalResponse,
    TraceContext,
    TriggerCheck,
)
from aap.schemas.value_coherence import (
    AlignmentCardRequest,
    AlignmentCardResponse,
    AutonomyScope,
    Coherence,
    CoherenceResultMessage,
    DataSharing,
    ProposedCollaboration,
    ProposedResolution,
    RequesterInfo,
    Signature,
    TaskContext,
    ValueAlignmentDetail,
    ValueCoherenceCheck,
    ValueConflict,
)

__all__ = [
    # Alignment Card (SPEC Section 4)
    "AlignmentCard",
    "Principal",
    "PrincipalType",
    "RelationshipType",
    "Values",
    "ValueDefinition",
    "HierarchyType",
    "AutonomyEnvelope",
    "EscalationTrigger",
    "TriggerAction",
    "MonetaryValue",
    "AuditCommitment",
    "AuditStorage",
    "StorageType",
    "TamperEvidence",
    # AP-Trace (SPEC Section 5)
    "APTrace",
    "Action",
    "ActionType",
    "ActionCategory",
    "ActionTarget",
    "Alternative",
    "Decision",
    "Escalation",
    "EscalationStatus",
    "TriggerCheck",
    "PrincipalResponse",
    "TraceContext",
    # Value Coherence (SPEC Section 6)
    "AlignmentCardRequest",
    "AlignmentCardResponse",
    "ValueCoherenceCheck",
    "CoherenceResultMessage",
    "RequesterInfo",
    "TaskContext",
    "Signature",
    "ProposedCollaboration",
    "DataSharing",
    "AutonomyScope",
    "Coherence",
    "ValueAlignmentDetail",
    "ValueConflict",
    "ProposedResolution",
]
