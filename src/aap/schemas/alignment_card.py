"""Alignment Card schema — Agent alignment declaration.

Defines the Alignment Card structure per SPEC Section 4. An Alignment Card
is a structured document declaring an agent's alignment posture:
- Principal relationship
- Declared values
- Autonomy envelope
- Audit commitment

See SPEC.md Section 4 for complete specification.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator


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
    """Principal relationship declaration (SPEC Section 4.3)."""

    type: PrincipalType = Field(
        ..., description="Type of principal"
    )
    identifier: str | None = Field(
        None, description="Principal identifier (DID, email, org ID)"
    )
    relationship: RelationshipType = Field(
        ..., description="Nature of authority delegation"
    )
    escalation_contact: str | None = Field(
        None, description="Endpoint for escalation notifications"
    )


class HierarchyType(str, Enum):
    """How value conflicts are resolved."""

    LEXICOGRAPHIC = "lexicographic"
    """Values are ordered by priority; higher priority wins."""

    WEIGHTED = "weighted"
    """Values have weights; weighted sum determines outcome."""

    CONTEXTUAL = "contextual"
    """Resolution depends on context; no fixed rule."""


class ValueDefinition(BaseModel):
    """Definition of a custom value."""

    name: str = Field(..., description="Human-readable name")
    description: str = Field(..., description="What this value means operationally")
    priority: int = Field(
        default=0, description="Priority for lexicographic ordering (higher = more important)"
    )


class Values(BaseModel):
    """Value declarations (SPEC Section 4.4)."""

    declared: list[str] = Field(
        ..., description="List of value identifiers"
    )
    definitions: dict[str, ValueDefinition] | None = Field(
        None, description="Definitions for non-standard values"
    )
    conflicts_with: list[str] | None = Field(
        None, description="Values this agent refuses to coordinate with"
    )
    hierarchy: HierarchyType | None = Field(
        None, description="How value conflicts are resolved"
    )

    @model_validator(mode="after")
    def custom_values_must_be_defined(self) -> "Values":
        """Non-standard values must have definitions."""
        standard_values = {
            "principal_benefit", "transparency", "minimal_data",
            "harm_prevention", "honesty", "user_control", "privacy", "fairness",
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
    """Condition that triggers escalation (SPEC Section 4.5)."""

    condition: str = Field(
        ..., description="Condition expression (see SPEC Section 4.6)"
    )
    action: TriggerAction = Field(
        ..., description="Action to take when trigger matches"
    )
    reason: str = Field(
        ..., description="Human-readable explanation"
    )


class MonetaryValue(BaseModel):
    """Monetary value specification."""

    amount: float = Field(..., description="Numeric amount")
    currency: str = Field(default="USD", description="ISO 4217 currency code")


class AutonomyEnvelope(BaseModel):
    """Autonomy bounds and escalation triggers (SPEC Section 4.5)."""

    bounded_actions: list[str] = Field(
        ..., description="Actions permitted without escalation"
    )
    escalation_triggers: list[EscalationTrigger] = Field(
        ..., description="Conditions requiring escalation"
    )
    max_autonomous_value: MonetaryValue | None = Field(
        None, description="Maximum transaction value without escalation"
    )
    forbidden_actions: list[str] | None = Field(
        None, description="Actions never permitted"
    )


class StorageType(str, Enum):
    """Audit log storage type."""

    LOCAL = "local"
    REMOTE = "remote"
    DISTRIBUTED = "distributed"


class TamperEvidence(str, Enum):
    """Tamper-evidence mechanism for audit logs."""

    APPEND_ONLY = "append_only"
    SIGNED = "signed"
    MERKLE = "merkle"


class AuditStorage(BaseModel):
    """Audit log storage configuration."""

    type: StorageType = Field(..., description="Storage type")
    location: str | None = Field(None, description="Storage endpoint or location")


class AuditCommitment(BaseModel):
    """Audit trail commitments (SPEC Section 4.7)."""

    trace_format: str = Field(
        default="ap-trace-v1", description="Trace format identifier"
    )
    retention_days: int = Field(
        ..., ge=1, description="Minimum retention period in days"
    )
    storage: AuditStorage | None = Field(
        None, description="Storage configuration"
    )
    queryable: bool = Field(
        ..., description="Whether traces can be queried externally"
    )
    query_endpoint: str | None = Field(
        None, description="Endpoint for trace queries (required if queryable=true)"
    )
    tamper_evidence: TamperEvidence | None = Field(
        None, description="Tamper-evidence mechanism"
    )

    @model_validator(mode="after")
    def queryable_requires_endpoint(self) -> "AuditCommitment":
        """If queryable is true, query_endpoint is required."""
        if self.queryable and not self.query_endpoint:
            raise ValueError("query_endpoint is required when queryable is true")
        return self


class AlignmentCard(BaseModel):
    """Alignment Card — Agent alignment declaration (SPEC Section 4).

    A structured document declaring an agent's alignment posture. It MUST be
    machine-readable (JSON) and SHOULD be human-readable.

    Example:
        card = AlignmentCard(
            aap_version="0.1.0",
            card_id="ac-12345",
            agent_id="did:web:agent.example.com",
            issued_at=datetime.utcnow(),
            principal=Principal(type=PrincipalType.HUMAN, relationship=RelationshipType.DELEGATED_AUTHORITY),
            values=Values(declared=["principal_benefit", "transparency"]),
            autonomy_envelope=AutonomyEnvelope(
                bounded_actions=["search", "recommend"],
                escalation_triggers=[
                    EscalationTrigger(
                        condition='action_type == "purchase"',
                        action=TriggerAction.ESCALATE,
                        reason="Purchases require approval",
                    )
                ],
            ),
            audit_commitment=AuditCommitment(
                retention_days=90,
                queryable=True,
                query_endpoint="https://agent.example.com/api/traces",
            ),
        )
    """

    aap_version: str = Field(
        default="0.1.0", description="AAP specification version"
    )
    card_id: str = Field(
        ..., description="Unique identifier for this card (UUID or URI)"
    )
    agent_id: str = Field(
        ..., description="Identifier for the agent (DID, URL, or UUID)"
    )
    issued_at: datetime = Field(
        ..., description="When this card was issued"
    )
    expires_at: datetime | None = Field(
        None, description="When this card expires"
    )
    principal: Principal = Field(
        ..., description="Principal relationship declaration"
    )
    values: Values = Field(
        ..., description="Value declarations"
    )
    autonomy_envelope: AutonomyEnvelope = Field(
        ..., description="Autonomy bounds and escalation triggers"
    )
    audit_commitment: AuditCommitment = Field(
        ..., description="Audit trail commitments"
    )
    extensions: dict[str, Any] | None = Field(
        None, description="Protocol-specific extensions"
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary suitable for JSON serialization."""
        return self.model_dump(mode="json", exclude_none=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AlignmentCard":
        """Create from dictionary."""
        return cls.model_validate(data)

    def is_expired(self) -> bool:
        """Check if the card has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    def has_value(self, value: str) -> bool:
        """Check if a value is declared."""
        return value in self.values.declared

    def is_action_bounded(self, action: str) -> bool:
        """Check if an action is in the bounded actions list."""
        return action in self.autonomy_envelope.bounded_actions

    def is_action_forbidden(self, action: str) -> bool:
        """Check if an action is forbidden."""
        return action in (self.autonomy_envelope.forbidden_actions or [])
