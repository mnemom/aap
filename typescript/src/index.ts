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
export { verifyTrace, checkCoherence, detectDrift } from "./verification/api";

// Schema types
export type {
  // Alignment Card
  AlignmentCard,
  Principal,
  PrincipalType,
  RelationshipType,
  Values,
  ValueDefinition,
  HierarchyType,
  AutonomyEnvelope,
  EscalationTrigger,
  TriggerAction,
  MonetaryValue,
  AuditCommitment,
  AuditStorage,
  StorageType,
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
