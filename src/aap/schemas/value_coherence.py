"""Value Coherence Handshake messages — Agent-to-agent alignment verification.

Defines the message types for the Value Coherence Handshake protocol
per SPEC Section 6. This pre-coordination protocol verifies whether
two agents' declared values are compatible for a proposed task.

Protocol flow:
1. alignment_card_request - Initiator requests responder's card
2. alignment_card_response - Responder provides their card
3. value_coherence_check - Initiator proposes collaboration
4. coherence_result - Responder provides compatibility assessment

See SPEC.md Section 6 for complete specification.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Request/Response Messages
# ---------------------------------------------------------------------------


class RequesterInfo(BaseModel):
    """Information about the agent making a request."""

    agent_id: str = Field(..., description="Agent identifier (DID, URL, or UUID)")
    card_id: str = Field(..., description="Requester's Alignment Card ID")


class TaskContext(BaseModel):
    """Context about the task for which alignment is being checked."""

    task_type: str = Field(..., description="Type of task being proposed")
    values_required: list[str] | None = Field(None, description="Values required for this task")
    data_categories: list[str] | None = Field(None, description="Categories of data involved")


class AlignmentCardRequest(BaseModel):
    """Request for an agent's Alignment Card (SPEC Section 6.3.1).

    Sent by initiator to request responder's Alignment Card.

    Example:
        request = AlignmentCardRequest(
            request_id="req-12345",
            requester=RequesterInfo(
                agent_id="did:web:initiator.example.com",
                card_id="ac-initiator-123",
            ),
            task_context=TaskContext(
                task_type="product_comparison",
                values_required=["principal_benefit", "transparency"],
            ),
        )
    """

    message_type: str = Field(
        default="alignment_card_request",
        description="Message type identifier",
    )
    request_id: str = Field(..., description="Unique request identifier")
    requester: RequesterInfo = Field(..., description="Information about requesting agent")
    task_context: TaskContext | None = Field(None, description="Context about the proposed task")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When request was made",
    )


class Signature(BaseModel):
    """Cryptographic signature for authentication."""

    algorithm: str = Field(..., description="Signature algorithm (e.g., Ed25519)")
    value: str = Field(..., description="Base64-encoded signature")
    key_id: str = Field(..., description="Key identifier")


class AlignmentCardResponse(BaseModel):
    """Response with an agent's Alignment Card (SPEC Section 6.3.2).

    Sent by responder with their Alignment Card.

    Example:
        response = AlignmentCardResponse(
            request_id="req-12345",
            alignment_card=card.to_dict(),  # AlignmentCard serialized
        )
    """

    message_type: str = Field(
        default="alignment_card_response",
        description="Message type identifier",
    )
    request_id: str = Field(..., description="Request ID being responded to")
    alignment_card: dict[str, Any] = Field(..., description="Responder's Alignment Card")
    signature: Signature | None = Field(None, description="Optional signature for authentication")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When response was made",
    )


class DataSharing(BaseModel):
    """Data sharing specification for collaboration."""

    from_initiator: list[str] = Field(
        default_factory=list,
        description="Data categories initiator will share",
    )
    from_responder: list[str] = Field(
        default_factory=list,
        description="Data categories responder will share",
    )


class AutonomyScope(BaseModel):
    """Scope of autonomous actions for collaboration."""

    initiator_actions: list[str] = Field(
        default_factory=list,
        description="Actions initiator may take",
    )
    responder_actions: list[str] = Field(
        default_factory=list,
        description="Actions responder may take",
    )


class ProposedCollaboration(BaseModel):
    """Proposed collaboration details."""

    task_type: str = Field(..., description="Type of task")
    values_intersection: list[str] | None = Field(
        None, description="Values both agents should apply"
    )
    data_sharing: DataSharing | None = Field(None, description="Data sharing specification")
    autonomy_scope: AutonomyScope | None = Field(None, description="Scope of autonomous actions")


class ValueCoherenceCheck(BaseModel):
    """Value coherence check request (SPEC Section 6.3.3).

    Sent by initiator to perform coherence check.

    Example:
        check = ValueCoherenceCheck(
            request_id="req-12345",
            initiator_card_id="ac-initiator-123",
            responder_card_id="ac-responder-456",
            proposed_collaboration=ProposedCollaboration(
                task_type="product_comparison",
                values_intersection=["principal_benefit", "transparency"],
            ),
        )
    """

    message_type: str = Field(
        default="value_coherence_check",
        description="Message type identifier",
    )
    request_id: str = Field(..., description="Request ID")
    initiator_card_id: str = Field(..., description="Initiator's Alignment Card ID")
    responder_card_id: str = Field(..., description="Responder's Alignment Card ID")
    proposed_collaboration: ProposedCollaboration = Field(
        ..., description="Proposed collaboration details"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When check was requested",
    )


# ---------------------------------------------------------------------------
# Coherence Result (also used by verification API)
# ---------------------------------------------------------------------------


class ValueConflict(BaseModel):
    """A conflict between values declared by two agents."""

    initiator_value: str = Field(..., description="Value from initiating agent")
    responder_value: str = Field(..., description="Value from responding agent")
    conflict_type: str = Field(
        ..., description="Type of conflict (incompatible, priority_mismatch, etc.)"
    )
    description: str = Field(..., description="Human-readable explanation")


class ValueAlignmentDetail(BaseModel):
    """Detailed value alignment analysis."""

    matched: list[str] = Field(
        default_factory=list,
        description="Values present in both cards",
    )
    unmatched: list[str] = Field(
        default_factory=list,
        description="Values in one card but not the other",
    )
    conflicts: list[ValueConflict] = Field(
        default_factory=list,
        description="Direct value conflicts",
    )


class Coherence(BaseModel):
    """Coherence assessment."""

    compatible: bool = Field(..., description="Whether agents are compatible")
    score: float = Field(..., ge=0.0, le=1.0, description="Coherence score")
    value_alignment: ValueAlignmentDetail = Field(..., description="Detailed alignment analysis")


class ResolutionType(str, Enum):
    """Type of proposed conflict resolution."""

    ESCALATE_TO_PRINCIPALS = "escalate_to_principals"
    MODIFIED_SCOPE = "modified_scope"
    NEGOTIATED = "negotiated"


class ProposedResolution(BaseModel):
    """Proposed resolution for value conflicts."""

    type: str = Field(..., description="Resolution type")
    reason: str = Field(..., description="Why this resolution is proposed")
    alternative: dict[str, Any] | None = Field(
        None, description="Alternative proposal (if applicable)"
    )


class CoherenceResultMessage(BaseModel):
    """Coherence result message (SPEC Section 6.3.4).

    Sent by responder with coherence assessment.

    Example (compatible):
        result = CoherenceResultMessage(
            request_id="req-12345",
            coherence=Coherence(
                compatible=True,
                score=0.85,
                value_alignment=ValueAlignmentDetail(
                    matched=["principal_benefit", "transparency"],
                ),
            ),
            proceed=True,
        )

    Example (conflict):
        result = CoherenceResultMessage(
            request_id="req-12345",
            coherence=Coherence(
                compatible=False,
                score=0.45,
                value_alignment=ValueAlignmentDetail(
                    matched=["transparency"],
                    conflicts=[
                        ValueConflict(
                            initiator_value="minimal_data",
                            responder_value="comprehensive_analytics",
                            conflict_type="incompatible",
                            description="Data collection requirements conflict",
                        )
                    ],
                ),
            ),
            proceed=False,
            proposed_resolution=ProposedResolution(
                type="escalate_to_principals",
                reason="Value conflict requires human decision",
            ),
        )
    """

    message_type: str = Field(
        default="coherence_result",
        description="Message type identifier",
    )
    request_id: str = Field(..., description="Request ID being responded to")
    coherence: Coherence = Field(..., description="Coherence assessment")
    proceed: bool = Field(..., description="Whether to proceed with coordination")
    conditions: list[str] | None = Field(None, description="Conditions for proceeding (if any)")
    proposed_resolution: ProposedResolution | None = Field(
        None, description="Proposed resolution (if conflicts exist)"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When result was generated",
    )
