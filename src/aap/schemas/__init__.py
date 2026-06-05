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

    # Create an Alignment Card (unified / ADR-039 shape)
    card = AlignmentCard(
        card_id="ac-12345",
        agent_id="did:web:agent.example.com",
        issued_at=datetime.now(timezone.utc),
        principal=Principal(
            type=PrincipalType.HUMAN,
            identifier="did:web:user.example.com",
            relationship=RelationshipType.DELEGATED_AUTHORITY,
        ),
        values=Values(declared=["principal_benefit", "transparency"]),
        autonomy=Autonomy(...),
        audit=Audit(...),
    )

    # Serialize to JSON
    card_json = card.to_dict()

    # Validate and parse JSON
    card = AlignmentCard.from_dict(card_json)
"""

from aap.schemas.alignment_card import (
    AlignmentCard,
    AlignmentMode,
    Audit,
    Autonomy,
    EscalationTrigger,
    HierarchyType,
    MonetaryValue,
    Principal,
    PrincipalType,
    RelationshipType,
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
    ValueScore,
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
    # Alignment Card (unified / ADR-039)
    "AlignmentCard",
    "AlignmentMode",
    "Principal",
    "PrincipalType",
    "RelationshipType",
    "Values",
    "ValueDefinition",
    "HierarchyType",
    "Autonomy",
    "EscalationTrigger",
    "TriggerAction",
    "MonetaryValue",
    "Audit",
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
    "ValueScore",
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
