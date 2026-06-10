"""Verification and drift detection models.

Defines the result types for AAP verification operations as specified
in SPEC.md Sections 7 (Verification) and 8 (Drift Detection).
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

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
    trace_field: str | None = Field(None, description="JSON path to the violating field")

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
    trace_field: str | None = Field(None, description="JSON path to the relevant field")


class VerificationMetadata(BaseModel):
    """Metadata about the verification process."""

    algorithm_version: str = Field(..., description="Verification algorithm version")
    checks_performed: list[str] = Field(
        default_factory=list, description="List of checks that were performed"
    )
    duration_ms: float | None = Field(
        None, description="Time taken to perform verification in milliseconds"
    )
    similarity_details: dict[str, Any] | None = Field(
        None, description="SSM analysis details when behavioral similarity is computed"
    )


VerificationRecommendation = Literal["proceed", "review", "deny"]


class VerificationResult(BaseModel):
    """Result of verifying an AP-Trace against an Alignment Card (SPEC Section 7.4)."""

    verified: bool = Field(..., description="True if no violations were found")
    recommended_action: VerificationRecommendation = Field(
        ...,
        description=(
            "Explicit action recommendation derived from violations and warnings. "
            "Prefer this over branching on `verified` alone — it distinguishes "
            "warning-only results ('review') from clean results ('proceed')."
        ),
    )
    trace_id: str = Field(..., description="ID of the verified trace")
    card_id: str = Field(..., description="ID of the Alignment Card used")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When verification was performed (UTC)",
    )
    violations: list[Violation] = Field(
        default_factory=list, description="List of violations found"
    )
    warnings: list[Warning] = Field(
        default_factory=list, description="List of non-critical warnings"
    )
    similarity_score: float = Field(
        ..., description="Behavioral similarity to Alignment Card (0.0-1.0)"
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

    alert_type: str = Field(default="drift_detected", description="Type of alert")
    agent_id: str = Field(..., description="Agent exhibiting drift")
    card_id: str = Field(..., description="Alignment Card being drifted from")
    detection_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When drift was detected (UTC)",
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
    threshold: float = Field(..., ge=0.0, le=1.0, description="Similarity threshold used")
    drift_direction: DriftDirection = Field(..., description="Categorized direction of drift")
    specific_indicators: list[DriftIndicator] = Field(
        default_factory=list, description="Specific drift indicators"
    )


# Re-export DriftAlert with analysis as a nested model
DriftAlert.model_rebuild()


class CoherenceResult(BaseModel):
    """Result of checking value coherence between two Alignment Cards."""

    compatible: bool = Field(..., description="Whether the cards are compatible for coordination")
    score: float = Field(..., ge=0.0, le=1.0, description="Coherence score")
    value_alignment: ValueAlignment = Field(..., description="Detailed value alignment analysis")
    proceed: bool = Field(..., description="Whether to proceed with coordination")
    conditions: list[str] = Field(
        default_factory=list,
        description="Conditions for proceeding (if any)",
    )
    proposed_resolution: dict[str, Any] | None = Field(
        None, description="Proposed conflict resolution (if conflicts exist)"
    )


class ValueAlignment(BaseModel):
    """Analysis of value alignment between two cards."""

    matched: list[str] = Field(default_factory=list, description="Values present in both cards")
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


# --- Fleet Coherence Types (E-05: N-Way Value Coherence) ---


class PairwiseEntry(BaseModel):
    """A single pairwise coherence entry in the fleet matrix."""

    agent_a: str = Field(..., description="First agent ID")
    agent_b: str = Field(..., description="Second agent ID")
    result: CoherenceResult = Field(..., description="Pairwise coherence result")


class FleetOutlier(BaseModel):
    """An agent flagged as an outlier in fleet coherence."""

    agent_id: str = Field(..., description="Agent ID")
    agent_mean_score: float = Field(..., description="Agent's mean pairwise score")
    fleet_mean_score: float = Field(..., description="Fleet-wide mean score")
    deviation: float = Field(..., description="Standard deviations below fleet mean")
    primary_conflicts: list[str] = Field(
        default_factory=list, description="Values causing primary conflicts"
    )


class FleetCluster(BaseModel):
    """A cluster of compatible agents."""

    cluster_id: int = Field(..., description="Cluster identifier")
    agent_ids: list[str] = Field(..., description="Agent IDs in this cluster")
    internal_coherence: float = Field(..., description="Mean coherence score within the cluster")
    shared_values: list[str] = Field(
        default_factory=list,
        description="Values shared by all agents in the cluster",
    )
    distinguishing_values: list[str] = Field(
        default_factory=list,
        description="Values that distinguish this cluster from others",
    )


class ValueDivergence(BaseModel):
    """A value dimension where agents diverge."""

    value: str = Field(..., description="The value in question")
    agents_declaring: list[str] = Field(
        default_factory=list, description="Agent IDs that declare this value"
    )
    agents_missing: list[str] = Field(
        default_factory=list, description="Agent IDs missing this value"
    )
    agents_conflicting: list[str] = Field(
        default_factory=list,
        description="Agent IDs whose conflicts_with includes this value",
    )
    impact_on_fleet_score: float = Field(
        ..., description="Estimated impact on fleet score if resolved"
    )


class AgentCoherenceSummary(BaseModel):
    """Summary of one agent's position in the fleet."""

    agent_id: str = Field(..., description="Agent ID")
    mean_score: float = Field(..., description="Mean pairwise score with all other agents")
    compatible_count: int = Field(..., description="Number of compatible pairs")
    conflict_count: int = Field(..., description="Number of conflicting pairs")
    cluster_id: int = Field(..., description="Cluster this agent belongs to")
    is_outlier: bool = Field(..., description="Whether this agent is flagged as an outlier")


class FleetCoherenceResult(BaseModel):
    """Result of N-way fleet coherence analysis."""

    fleet_score: float = Field(..., description="Mean of all pairwise coherence scores")
    min_pair_score: float = Field(..., description="Minimum pairwise score (weakest link)")
    max_pair_score: float = Field(..., description="Maximum pairwise score")
    agent_count: int = Field(..., description="Number of agents analyzed")
    pair_count: int = Field(..., description="Number of pairwise comparisons")
    pairwise_matrix: list[PairwiseEntry] = Field(..., description="All pairwise coherence results")
    outliers: list[FleetOutlier] = Field(
        default_factory=list, description="Agents flagged as outliers"
    )
    clusters: list[FleetCluster] = Field(
        default_factory=list, description="Clusters of compatible agents"
    )
    divergence_report: list[ValueDivergence] = Field(
        default_factory=list,
        description="Value dimensions where agents diverge",
    )
    agent_summaries: list[AgentCoherenceSummary] = Field(
        default_factory=list, description="Per-agent coherence summaries"
    )
