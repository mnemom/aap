"""Verification and drift detection models.

Defines the result types for AAP verification operations as specified
in SPEC.md Sections 7 (Verification) and 8 (Drift Detection).
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ViolationType(str, Enum):
    """Types of verification violations (SPEC Section 7.5)."""

    UNBOUNDED_ACTION = "unbounded_action"
    """Action not in bounded_actions list. Severity: HIGH"""

    FORBIDDEN_ACTION = "forbidden_action"
    """Action in forbidden_actions list. Severity: CRITICAL"""

    MISSED_ESCALATION = "missed_escalation"
    """Escalation trigger matched but not escalated. Severity: HIGH"""

    UNDECLARED_VALUE = "undeclared_value"
    """Applied value not in declared values. Severity: MEDIUM"""

    CARD_EXPIRED = "card_expired"
    """Alignment Card has expired. Severity: HIGH"""

    CARD_MISMATCH = "card_mismatch"
    """Trace references different card than provided. Severity: CRITICAL"""


class Severity(str, Enum):
    """Violation severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# Mapping of violation types to their severity
VIOLATION_SEVERITY: dict[ViolationType, Severity] = {
    ViolationType.UNBOUNDED_ACTION: Severity.HIGH,
    ViolationType.FORBIDDEN_ACTION: Severity.CRITICAL,
    ViolationType.MISSED_ESCALATION: Severity.HIGH,
    ViolationType.UNDECLARED_VALUE: Severity.MEDIUM,
    ViolationType.CARD_EXPIRED: Severity.HIGH,
    ViolationType.CARD_MISMATCH: Severity.CRITICAL,
}


class Violation(BaseModel):
    """A single verification violation."""

    type: ViolationType = Field(..., description="Type of violation")
    severity: Severity = Field(..., description="Severity level")
    description: str = Field(..., description="Human-readable description")
    trace_field: str | None = Field(
        None, description="JSON path to the violating field"
    )

    @classmethod
    def create(
        cls,
        violation_type: ViolationType,
        description: str,
        trace_field: str | None = None,
    ) -> Violation:
        """Create a violation with automatic severity lookup."""
        return cls(
            type=violation_type,
            severity=VIOLATION_SEVERITY[violation_type],
            description=description,
            trace_field=trace_field,
        )


class Warning(BaseModel):
    """A verification warning (non-critical issue)."""

    type: str = Field(..., description="Warning type identifier")
    description: str = Field(..., description="Human-readable description")
    trace_field: str | None = Field(
        None, description="JSON path to the relevant field"
    )


class VerificationMetadata(BaseModel):
    """Metadata about the verification process."""

    algorithm_version: str = Field(..., description="Verification algorithm version")
    checks_performed: list[str] = Field(
        default_factory=list, description="List of checks that were performed"
    )
    duration_ms: float | None = Field(
        None, description="Time taken to perform verification in milliseconds"
    )


class VerificationResult(BaseModel):
    """Result of verifying an AP-Trace against an Alignment Card (SPEC Section 7.4)."""

    verified: bool = Field(
        ..., description="True if no violations were found"
    )
    trace_id: str = Field(..., description="ID of the verified trace")
    card_id: str = Field(..., description="ID of the Alignment Card used")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When verification was performed",
    )
    violations: list[Violation] = Field(
        default_factory=list, description="List of violations found"
    )
    warnings: list[Warning] = Field(
        default_factory=list, description="List of non-critical warnings"
    )
    verification_metadata: VerificationMetadata = Field(
        ..., description="Metadata about the verification process"
    )


class DriftDirection(str, Enum):
    """Categories of behavioral drift (SPEC Section 8.5)."""

    AUTONOMY_EXPANSION = "autonomy_expansion"
    """Agent acting outside declared bounds."""

    VALUE_DRIFT = "value_drift"
    """Applied values diverging from declared."""

    PRINCIPAL_MISALIGNMENT = "principal_misalignment"
    """Decisions not serving principal interests."""

    COMMUNICATION_DRIFT = "communication_drift"
    """Explanations becoming inconsistent with values."""

    UNKNOWN = "unknown"
    """Drift detected but direction unclear."""


class DriftIndicator(BaseModel):
    """A specific indicator of behavioral drift."""

    indicator: str = Field(..., description="Indicator identifier")
    baseline: float = Field(..., description="Expected/baseline value")
    current: float = Field(..., description="Currently observed value")
    description: str = Field(..., description="Human-readable explanation")


class DriftAlert(BaseModel):
    """Alert generated when sustained drift is detected (SPEC Section 8.4)."""

    alert_type: str = Field(
        default="drift_detected", description="Type of alert"
    )
    agent_id: str = Field(..., description="Agent exhibiting drift")
    card_id: str = Field(..., description="Alignment Card being drifted from")
    detection_timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When drift was detected",
    )
    analysis: DriftAnalysis = Field(..., description="Drift analysis details")
    recommendation: str = Field(
        default="Review recent decisions for alignment drift",
        description="Recommended action",
    )
    trace_ids: list[str] = Field(
        default_factory=list,
        description="IDs of traces exhibiting drift",
    )


class DriftAnalysis(BaseModel):
    """Detailed analysis of detected drift."""

    similarity_score: float = Field(
        ..., ge=0.0, le=1.0, description="Current similarity to declared alignment"
    )
    sustained_traces: int = Field(
        ..., ge=1, description="Number of consecutive low-similarity traces"
    )
    threshold: float = Field(
        ..., ge=0.0, le=1.0, description="Similarity threshold used"
    )
    drift_direction: DriftDirection = Field(
        ..., description="Categorized direction of drift"
    )
    specific_indicators: list[DriftIndicator] = Field(
        default_factory=list, description="Specific drift indicators"
    )


# Re-export DriftAlert with analysis as a nested model
DriftAlert.model_rebuild()


class CoherenceResult(BaseModel):
    """Result of checking value coherence between two Alignment Cards."""

    compatible: bool = Field(
        ..., description="Whether the cards are compatible for coordination"
    )
    score: float = Field(
        ..., ge=0.0, le=1.0, description="Coherence score"
    )
    value_alignment: ValueAlignment = Field(
        ..., description="Detailed value alignment analysis"
    )
    proceed: bool = Field(
        ..., description="Whether to proceed with coordination"
    )
    conditions: list[str] = Field(
        default_factory=list,
        description="Conditions for proceeding (if any)",
    )
    proposed_resolution: dict[str, Any] | None = Field(
        None, description="Proposed conflict resolution (if conflicts exist)"
    )


class ValueAlignment(BaseModel):
    """Analysis of value alignment between two cards."""

    matched: list[str] = Field(
        default_factory=list, description="Values present in both cards"
    )
    unmatched: list[str] = Field(
        default_factory=list, description="Values in one card but not the other"
    )
    conflicts: list[ValueConflict] = Field(
        default_factory=list, description="Direct value conflicts"
    )


class ValueConflict(BaseModel):
    """A conflict between values declared by two agents."""

    initiator_value: str = Field(..., description="Value from initiating agent")
    responder_value: str = Field(..., description="Value from responding agent")
    conflict_type: str = Field(
        ..., description="Type of conflict (incompatible, priority_mismatch, etc.)"
    )
    description: str = Field(..., description="Human-readable explanation")


# Rebuild models with forward references
CoherenceResult.model_rebuild()
