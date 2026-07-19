/**
 * Agent Alignment Protocol (AAP) - TypeScript SDK
 *
 * This package provides the core verification functionality for AAP:
 * - verifyTrace: Verify a single AP-Trace against an Alignment Card
 * - checkCoherence: Check value coherence between two Alignment Cards
 * - detectDrift: Detect behavioral drift from declared alignment over time
 *
 * @example
 * ```typescript
 * import { verifyTrace, checkCoherence, detectDrift } from 'agent-alignment-protocol';
 * import type { AlignmentCard, APTrace } from 'agent-alignment-protocol';
 *
 * // Verify a trace
 * const result = verifyTrace(trace, card);
 * if (!result.verified) {
 *   console.log('Violations:', result.violations);
 * }
 *
 * // Check coherence between two cards
 * const coherence = checkCoherence(myCard, theirCard);
 * if (!coherence.compatible) {
 *   console.log('Value conflicts:', coherence.value_alignment.conflicts);
 * }
 *
 * // Detect drift over time
 * const alerts = detectDrift(card, recentTraces);
 * for (const alert of alerts) {
 *   console.log('Drift detected:', alert.analysis.drift_direction);
 * }
 * ```
 *
 * @see https://aap.dev for documentation
 * @see SPEC.md for protocol specification
 */

// Main API exports
export { verifyTrace, checkCoherence, checkFleetCoherence, detectDrift, analyzeFaultLines, checkFleetFaultLines } from "./verification/api";

// Schema types
export type {
  // Alignment Card (unified / ADR-039)
  AlignmentCard,
  AlignmentMode,
  Principal,
  PrincipalType,
  RelationshipType,
  Values,
  ValueDefinition,
  ParameterizedValue,
  HierarchyType,
  Autonomy,
  EscalationTrigger,
  TriggerAction,
  MonetaryValue,
  Audit,
  TamperEvidence,
} from "./schemas/alignment-card";

export type {
  // AP-Trace
  APTrace,
  Action,
  ActionType,
  ActionCategory,
  ActionTarget,
  Decision,
  Alternative,
  ValueScore,
  Escalation,
  EscalationStatus,
  TriggerCheck,
  PrincipalResponse,
  TraceContext,
} from "./schemas/ap-trace";

export type {
  // Value Coherence
  AlignmentCardRequest,
  AlignmentCardResponse,
  ValueCoherenceCheck,
  CoherenceResultMessage,
  ValueCoherenceMessage,
  RequesterInfo,
  TaskContext,
  Signature,
  ProposedCollaboration,
  DataSharing,
  AutonomyScope,
  Coherence,
  ValueAlignmentDetail,
  ValueConflict,
  ProposedResolution,
} from "./schemas/value-coherence";

// Result types
export type {
  VerificationResult,
  VerificationRecommendation,
  Violation,
  ViolationType,
  Severity,
  Warning,
  VerificationMetadata,
  CoherenceResult,
  ValueAlignment,
  ValueConflictResult,
  DriftAlert,
  DriftAnalysis,
  DriftDirection,
  DriftIndicator,
  // Fleet Coherence (E-05)
  FleetCoherenceResult,
  PairwiseEntry,
  FleetOutlier,
  FleetCluster,
  ValueDivergence,
  AgentCoherenceSummary,
  // Fault Line Analysis (E-06)
  FaultLineClassification,
  FaultLine,
  FaultLineSummary,
  FaultLineAlignment,
  FaultLineAnalysis,
} from "./verification/models";

// Utility exports
export {
  isCardExpired,
  hasValue,
  isActionBounded,
  isActionForbidden,
} from "./schemas/alignment-card";

export {
  getSelectedAlternative,
  wasEscalated,
  hadViolations,
} from "./schemas/ap-trace";

export {
  computeCentroid,
  extractCardFeatures,
  extractTraceFeatures,
  cosineSimilarity,
} from "./verification/features";

export { createViolation, VIOLATION_SEVERITY } from "./verification/models";

// Constants
export * from "./constants";

// EU AI Act compliance presets
export {
  EU_COMPLIANCE_AUDIT,
  EU_COMPLIANCE_EXTENSIONS,
  EU_COMPLIANCE_VALUES,
} from "./compliance";

// Governance signals — operator-actionable observations (ADR-048).
// Types are consumed by operator-shaped clients: dashboards, webhook
// subscribers, alerting tools, audit pipelines. The platform never
// injects governance signals into agent prompts; ADR-048's 2026-05-07
// amendment retracted the earlier "application-owned sovereign-agent
// composer" carve-out, including the example file removed in 1.2.0.
export type {
  GovernanceSignal,
  GovernanceSignalScope,
  GovernanceSignalSource,
  GovernanceSignalSeverity,
  GovernanceSignalStatus,
  GovernanceActorRole,
  GovernanceResolutionStatus,
  GovernanceNotificationChannel,
  GovernanceFleetPatternType,
  GovernanceCoherencePatternType,
  GovernanceSourceRef,
  GovernanceFleetSourceRef,
  GovernanceCoherenceSourceRef,
  GovernanceFaultLineSourceRef,
  GovernanceDriftSourceRef,
  GovernanceSourceRefBase,
  GovernanceNotificationDispatchState,
  GovernanceNotificationChannelState,
  GovernanceNotificationState,
  GovernanceWebhookEventType,
  GovernanceWebhookEnvelope,
} from "./governance";

export {
  isFleetSignal,
  isCoherenceSignal,
  isFaultLineSignal,
  isDriftSignal,
  severityAtLeast,
  SEVERITY_ORDER,
} from "./governance";
