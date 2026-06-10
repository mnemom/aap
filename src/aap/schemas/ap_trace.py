"""AP-Trace schema — Audit log format for agent decisions.

Defines the AP-Trace structure per SPEC Section 5. An AP-Trace entry
records an agent's decision process:
- What action was taken or considered
- What alternatives were evaluated
- Why a particular choice was made
- Whether escalation was required

See SPEC.md Section 5 for complete specification.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class ActionType(str, Enum):
    """Type of action taken or considered."""

    RECOMMEND = "recommend"
    """Agent recommends an action to principal."""

    EXECUTE = "execute"
    """Agent executes an action."""

    ESCALATE = "escalate"
    """Agent escalates decision to principal."""

    DENY = "deny"
    """Agent denies/refuses an action."""


class ActionCategory(str, Enum):
    """How the action relates to the autonomy envelope."""

    BOUNDED = "bounded"
    """Action is within bounded_actions list."""

    ESCALATION_TRIGGER = "escalation_trigger"
    """Action triggered an escalation condition."""

    FORBIDDEN = "forbidden"
    """Action is in forbidden_actions list."""


class ActionTarget(BaseModel):
    """Resource affected by the action."""

    type: str = Field(..., description="Resource type")
    identifier: str = Field(..., description="Resource identifier")


class Action(BaseModel):
    """Action taken or considered (SPEC Section 5.4)."""

    type: ActionType = Field(..., description="Action type")
    name: str = Field(..., description="Human-readable action name")
    category: ActionCategory = Field(
        ..., description="How this action relates to autonomy envelope"
    )
    target: ActionTarget | None = Field(None, description="Resource affected")
    parameters: dict[str, Any] | None = Field(None, description="Action parameters")


class Alternative(BaseModel):
    """An alternative considered during decision-making."""

    option_id: str = Field(..., description="Unique identifier for this option")
    description: str = Field(..., description="Human-readable description")
    score: float | None = Field(None, ge=0.0, le=1.0, description="Computed score")
    scoring_factors: dict[str, float] | None = Field(
        None, description="Breakdown of score components"
    )
    flags: list[str] | None = Field(None, description="Concerns or flags about this option")


class ValueScore(BaseModel):
    """Per-value score from V2 observer scoring (Phase 3.3)."""

    score: Literal["on_track", "off_track", "not_applicable"] = Field(
        ..., description="Score against the catalog entry's observer_signals rubric"
    )
    rationale: str = Field(
        ...,
        description=("Free-form rationale citing one of the catalog observer_signals patterns"),
    )


class Decision(BaseModel):
    """Decision process record (SPEC Section 5.5)."""

    alternatives_considered: list[Alternative] = Field(
        ..., min_length=1, description="Options evaluated (minimum 1)"
    )
    selected: str = Field(..., description="Option ID selected")
    selection_reasoning: str = Field(
        ..., description="Human-readable explanation of why this was chosen"
    )
    values_applied: list[str] = Field(..., description="Values that influenced this decision")
    confidence: float | None = Field(None, ge=0.0, le=1.0, description="Decision confidence")
    value_scores: dict[str, ValueScore] | None = Field(
        None,
        description=(
            "Per-declared-value score against the alignment card's catalog "
            "observer_signals (Phase 3.3 V2 observer surface). Optional — "
            "present when the card declares catalog values with "
            "observer_signals defined; absent on V1 observer output. Keyed "
            "by catalog value id. `values_applied` is derived from "
            "`value_scores` entries whose score is 'on_track' to preserve "
            "the V1 surface contract for downstream consumers."
        ),
    )

    @model_validator(mode="after")
    def selected_must_be_in_alternatives(self) -> Decision:
        """Selected option must be one of the alternatives."""
        option_ids = [alt.option_id for alt in self.alternatives_considered]
        if self.selected not in option_ids:
            raise ValueError(f"Selected '{self.selected}' not in alternatives: {option_ids}")
        return self


class TriggerCheck(BaseModel):
    """Record of checking an escalation trigger."""

    trigger: str = Field(..., description="Trigger condition that was checked")
    matched: bool = Field(..., description="Whether the trigger matched")
    value_observed: Any | None = Field(None, description="Observed value (for comparison triggers)")


class EscalationStatus(str, Enum):
    """Status of an escalation."""

    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    TIMEOUT = "timeout"


class PrincipalResponse(BaseModel):
    """Response from principal to escalation."""

    decision: str = Field(..., description="Principal's decision")
    timestamp: datetime = Field(..., description="When decision was made")
    conditions: list[str] | None = Field(None, description="Conditions attached to approval")


class Escalation(BaseModel):
    """Escalation evaluation record (SPEC Section 5.6)."""

    evaluated: bool = Field(..., description="Whether escalation was evaluated")
    triggers_checked: list[TriggerCheck] | None = Field(
        None, description="Triggers that were evaluated"
    )
    required: bool = Field(..., description="Whether escalation is required")
    reason: str = Field(..., description="Human-readable explanation")
    escalation_id: str | None = Field(
        None, description="Escalation request ID (if escalation required)"
    )
    escalation_status: EscalationStatus | None = Field(
        None, description="Status of escalation (if escalation required)"
    )
    principal_response: PrincipalResponse | None = Field(
        None, description="Principal's response (if escalation required)"
    )


class TraceContext(BaseModel):
    """Additional context for the trace (SPEC Section 5.7)."""

    session_id: str | None = Field(None, description="Session identifier")
    conversation_turn: int | None = Field(None, description="Turn number in conversation")
    prior_trace_ids: list[str] | None = Field(None, description="IDs of related prior traces")
    environment: dict[str, Any] | None = Field(
        None, description="Environment metadata (client, locale, etc.)"
    )
    metadata: dict[str, Any] | None = Field(None, description="Additional arbitrary metadata")


class APTrace(BaseModel):
    """AP-Trace — Audit log entry for agent decisions (SPEC Section 5).

    An AP-Trace records an agent's decision process, enabling verification
    that observed behavior is consistent with declared alignment.

    Design principles (SPEC Section 5.2):
    1. Sampling, not completeness - captures significant decisions
    2. Structured reasoning - machine-parseable rationale
    3. Verifiable references - traces reference the Alignment Card in effect
    4. Append-only - traces MUST NOT be modified after creation

    Example:
        trace = APTrace(
            trace_id="tr-12345",
            agent_id="did:web:agent.example.com",
            card_id="ac-67890",
            timestamp=datetime.utcnow(),
            action=Action(
                type=ActionType.RECOMMEND,
                name="product_recommendation",
                category=ActionCategory.BOUNDED,
            ),
            decision=Decision(
                alternatives_considered=[
                    Alternative(option_id="A", description="Option A", score=0.85),
                    Alternative(option_id="B", description="Option B", score=0.72),
                ],
                selected="A",
                selection_reasoning="Highest score based on principal benefit.",
                values_applied=["principal_benefit"],
            ),
            escalation=Escalation(
                evaluated=True,
                required=False,
                reason="No escalation triggers matched",
            ),
        )
    """

    trace_id: str = Field(..., description="Unique identifier (UUID)")
    agent_id: str = Field(..., description="Agent that generated this trace")
    card_id: str = Field(..., description="Alignment Card in effect")
    timestamp: datetime = Field(..., description="When this trace was created")
    action: Action = Field(..., description="Action taken or considered")
    decision: Decision = Field(..., description="Decision process record")
    escalation: Escalation | None = Field(None, description="Escalation evaluation (if applicable)")
    context: TraceContext | None = Field(None, description="Additional context")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary suitable for JSON serialization."""
        return self.model_dump(mode="json", exclude_none=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> APTrace:
        """Create from dictionary."""
        return cls.model_validate(data)

    def get_selected_alternative(self) -> Alternative | None:
        """Get the selected alternative from the decision."""
        for alt in self.decision.alternatives_considered:
            if alt.option_id == self.decision.selected:
                return alt
        return None

    def was_escalated(self) -> bool:
        """Check if this decision was escalated."""
        return self.escalation is not None and self.escalation.required

    def had_violations(self) -> bool:
        """Check if the action was forbidden or triggered unhandled escalation."""
        return self.action.category == ActionCategory.FORBIDDEN
