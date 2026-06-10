"""Alignment Card schema — Agent alignment declaration (unified / ADR-039).

Defines the unified Alignment Card structure accepted by the Mnemom platform
and `mnemom card validate`. An Alignment Card is a structured document
declaring an agent's alignment posture:
- Principal relationship
- Declared values
- Autonomy bounds (`autonomy`)
- Audit commitments (`audit`)
- Two top-level master switches (`autonomy_mode`, `integrity_mode`)

This is the unified shape. It renames the legacy AAP 0.5.0
`autonomy_envelope`→`autonomy` and `audit_commitment`→`audit`, replaces
`aap_version` with the date-anchored `card_version`, and adds the top-level
master switches. Semantics are preserved; the migration is largely a rename.

See https://docs.mnemom.ai/specifications/alignment-card-schema for the
normative reference.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator

#: Current unified alignment-card schema version (date-anchored identifier).
CARD_VERSION = "unified/2026-04-26"


class AlignmentMode(str, Enum):
    """Master-switch mode shared by ``autonomy_mode`` and ``integrity_mode``.

    Strictest wins on composition: ``enforce > nudge > observe > off``.
    """

    OFF = "off"
    """Pipeline disabled."""

    OBSERVE = "observe"
    """Log results; do not block."""

    NUDGE = "nudge"
    """Inject advisory annotation; do not block."""

    ENFORCE = "enforce"
    """Block violations and escalate."""


class PrincipalType(str, Enum):
    """Type of principal the agent serves."""

    HUMAN = "human"
    ORGANIZATION = "organization"
    AGENT = "agent"
    UNSPECIFIED = "unspecified"


class RelationshipType(str, Enum):
    """Nature of authority delegation from principal to agent."""

    DELEGATED_AUTHORITY = "delegated_authority"
    """Agent acts within bounds set by principal."""

    ADVISORY = "advisory"
    """Agent provides recommendations; principal makes decisions."""

    AUTONOMOUS = "autonomous"
    """Agent operates independently within declared values."""


class Principal(BaseModel):
    """Principal relationship declaration (unified / ADR-039 §principal)."""

    type: PrincipalType = Field(..., description="Type of principal")
    identifier: str | None = Field(
        None,
        description="Principal identifier (DID, email, org ID). Required when type != 'unspecified'.",
    )
    relationship: RelationshipType = Field(..., description="Nature of authority delegation")
    escalation_contact: str | None = Field(
        None, description="Endpoint for escalation notifications"
    )

    @model_validator(mode="after")
    def identifier_required_when_typed(self) -> Principal:
        """`identifier` is required when `type` is not 'unspecified' (ADR-039)."""
        if self.type != PrincipalType.UNSPECIFIED and not self.identifier:
            raise ValueError(
                "principal.identifier is required when principal.type is not 'unspecified'"
            )
        return self


class HierarchyType(str, Enum):
    """How value conflicts are resolved."""

    LEXICOGRAPHIC = "lexicographic"
    """Values are ordered by priority; higher priority wins."""

    WEIGHTED = "weighted"
    """Values have weights; weighted sum determines outcome."""

    CONTEXTUAL = "contextual"
    """Resolution depends on context; no fixed rule."""


class ValueDefinition(BaseModel):
    """Definition of a custom value (unified / ADR-039 §values).

    Per the unified spec a definition carries a ``description`` and optional
    ``priority``; ``name`` is optional (the value's identifier is the
    ``definitions`` map key).
    """

    name: str | None = Field(None, description="Human-readable name (optional)")
    description: str = Field(..., description="What this value means operationally")
    priority: float = Field(
        default=0,
        description="Priority for lexicographic/weighted ordering (higher = more important)",
    )


class Values(BaseModel):
    """Value declarations (unified / ADR-039 §values)."""

    declared: list[str] = Field(..., description="List of value identifiers")
    definitions: dict[str, ValueDefinition] | None = Field(
        None, description="Definitions for non-standard values"
    )
    conflicts_with: list[str] | None = Field(
        None, description="Values this agent refuses to coordinate with"
    )
    hierarchy: HierarchyType | None = Field(None, description="How value conflicts are resolved")

    @model_validator(mode="after")
    def custom_values_must_be_defined(self) -> Values:
        """Non-standard values must have definitions."""
        standard_values = {
            "principal_benefit",
            "transparency",
            "minimal_data",
            "harm_prevention",
            "honesty",
            "user_control",
            "privacy",
            "fairness",
        }
        if self.definitions:
            for value in self.declared:
                if value not in standard_values and value not in self.definitions:
                    raise ValueError(f"Custom value '{value}' must be defined in definitions")
        return self


class TriggerAction(str, Enum):
    """Action to take when escalation trigger matches."""

    ESCALATE = "escalate"
    """Defer decision to principal."""

    DENY = "deny"
    """Refuse to take the action."""

    LOG = "log"
    """Log the action but proceed."""


class EscalationTrigger(BaseModel):
    """Condition that triggers escalation (unified / ADR-039 §autonomy)."""

    condition: str = Field(..., description="Condition expression")
    action: TriggerAction = Field(..., description="Action to take when trigger matches")
    reason: str = Field(..., description="Human-readable explanation")


class MonetaryValue(BaseModel):
    """Monetary value specification."""

    amount: float = Field(..., description="Numeric amount")
    currency: str = Field(default="USD", description="ISO 4217 currency code")


class Autonomy(BaseModel):
    """Autonomy bounds and escalation triggers (unified / ADR-039 §autonomy).

    Renamed from the legacy AAP 0.5.0 ``autonomy_envelope``; semantics
    preserved. ``escalation_triggers`` is now optional (defaults to an empty
    list) to match the unified spec, where only ``bounded_actions`` is required.
    """

    bounded_actions: list[str] = Field(..., description="Actions permitted without escalation")
    escalation_triggers: list[EscalationTrigger] = Field(
        default_factory=list, description="Conditions requiring escalation"
    )
    max_autonomous_value: MonetaryValue | None = Field(
        None, description="Maximum transaction value without escalation"
    )
    forbidden_actions: list[str] | None = Field(None, description="Actions never permitted")

    @model_validator(mode="after")
    def bounded_and_forbidden_disjoint(self) -> Autonomy:
        """`bounded_actions` and `forbidden_actions` must be disjoint (ADR-039)."""
        if self.forbidden_actions:
            overlap = set(self.bounded_actions) & set(self.forbidden_actions)
            if overlap:
                raise ValueError(
                    "autonomy.bounded_actions and forbidden_actions must be disjoint; "
                    f"both contain: {', '.join(sorted(overlap))}"
                )
        return self


class TamperEvidence(str, Enum):
    """Tamper-evidence mechanism for audit logs."""

    APPEND_ONLY = "append_only"
    SIGNED = "signed"
    MERKLE = "merkle"


class Audit(BaseModel):
    """Audit trail commitments (unified / ADR-039 §audit).

    Renamed from the legacy AAP 0.5.0 ``audit_commitment``; semantics
    preserved. The legacy ``storage`` sub-object is no longer part of the
    unified shape (the platform validator rejects ``audit.storage``).
    """

    trace_format: str = Field(default="ap-trace-v1", description="Trace format identifier")
    retention_days: int = Field(..., ge=0, description="Minimum retention period in days")
    queryable: bool = Field(..., description="Whether traces can be queried externally")
    query_endpoint: str | None = Field(
        None, description="Endpoint for trace queries (required if queryable=true)"
    )
    tamper_evidence: TamperEvidence | None = Field(None, description="Tamper-evidence mechanism")

    @model_validator(mode="after")
    def queryable_requires_endpoint(self) -> Audit:
        """If queryable is true, query_endpoint is required."""
        if self.queryable and not self.query_endpoint:
            raise ValueError("query_endpoint is required when queryable is true")
        return self


class AlignmentCard(BaseModel):
    """Alignment Card — Agent alignment declaration (unified / ADR-039).

    A structured document declaring an agent's alignment posture. It MUST be
    machine-readable (JSON) and SHOULD be human-readable. This is the unified
    card shape accepted by `mnemom card validate` and the Mnemom platform.

    Example:
        card = AlignmentCard(
            card_version="unified/2026-04-26",
            card_id="ac-12345",
            agent_id="did:web:agent.example.com",
            issued_at=datetime.now(timezone.utc),
            autonomy_mode=AlignmentMode.OBSERVE,
            integrity_mode=AlignmentMode.OBSERVE,
            principal=Principal(
                type=PrincipalType.HUMAN,
                identifier="did:web:user.example.com",
                relationship=RelationshipType.DELEGATED_AUTHORITY,
            ),
            values=Values(declared=["principal_benefit", "transparency"]),
            autonomy=Autonomy(
                bounded_actions=["search", "recommend"],
                escalation_triggers=[
                    EscalationTrigger(
                        condition='action_type == "purchase"',
                        action=TriggerAction.ESCALATE,
                        reason="Purchases require approval",
                    )
                ],
            ),
            audit=Audit(
                retention_days=90,
                queryable=True,
                query_endpoint="https://agent.example.com/api/traces",
            ),
        )
    """

    card_version: str = Field(
        default=CARD_VERSION,
        description="Unified alignment-card schema version (date-anchored identifier)",
    )
    card_id: str = Field(..., description="Unique identifier for this card (UUID or URI)")
    agent_id: str = Field(..., description="Identifier for the agent (DID, URL, or UUID)")
    issued_at: datetime = Field(..., description="When this card was issued")
    expires_at: datetime | None = Field(None, description="When this card expires")
    autonomy_mode: AlignmentMode = Field(
        default=AlignmentMode.OBSERVE,
        description="Master switch for the action-policing pipeline",
    )
    integrity_mode: AlignmentMode = Field(
        default=AlignmentMode.OBSERVE,
        description="Master switch for the values/conscience pipeline",
    )
    principal: Principal = Field(..., description="Principal relationship declaration")
    values: Values = Field(..., description="Value declarations")
    autonomy: Autonomy = Field(..., description="Autonomy bounds and escalation triggers")
    audit: Audit = Field(..., description="Audit trail commitments")
    extensions: dict[str, Any] | None = Field(None, description="Protocol-specific extensions")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary suitable for JSON serialization."""
        return self.model_dump(mode="json", exclude_none=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AlignmentCard:
        """Create from dictionary."""
        return cls.model_validate(data)

    def is_expired(self) -> bool:
        """Check if the card has expired.

        Handles both timezone-aware and naive ``expires_at`` values: the
        comparison ``now`` is built to match the awareness of ``expires_at``.
        """
        if self.expires_at is None:
            return False
        if self.expires_at.tzinfo is None:
            # Naive expiry — compare against naive UTC now.
            return datetime.utcnow() > self.expires_at
        # Aware expiry — compare against aware now in the same tz.
        return datetime.now(self.expires_at.tzinfo) > self.expires_at

    def has_value(self, value: str) -> bool:
        """Check if a value is declared."""
        return value in self.values.declared

    def is_action_bounded(self, action: str) -> bool:
        """Check if an action is in the bounded actions list."""
        return action in self.autonomy.bounded_actions

    def is_action_forbidden(self, action: str) -> bool:
        """Check if an action is forbidden."""
        return action in (self.autonomy.forbidden_actions or [])
