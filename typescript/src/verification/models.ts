/**
 * Verification and drift detection models.
 *
 * Defines the result types for AAP verification operations as specified
 * in SPEC.md Sections 7 (Verification) and 8 (Drift Detection).
 */

/** Types of verification violations (SPEC Section 7.5). */
export type ViolationType =
  | "unbounded_action"
  | "forbidden_action"
  | "missed_escalation"
  | "undeclared_value"
  | "card_expired"
  | "card_mismatch";

/** Violation severity levels. */
export type Severity = "critical" | "high" | "medium" | "low";

/** Mapping of violation types to their severity */
export const VIOLATION_SEVERITY: Record<ViolationType, Severity> = {
  unbounded_action: "high",
  forbidden_action: "critical",
  missed_escalation: "high",
  undeclared_value: "medium",
  card_expired: "high",
  card_mismatch: "critical",
};

/** A single verification violation. */
export interface Violation {
  /** Type of violation */
  type: ViolationType;
  /** Severity level */
  severity: Severity;
  /** Human-readable description */
  description: string;
  /** JSON path to the violating field */
  trace_field?: string | null;
}

/** Create a violation with automatic severity lookup. */
export function createViolation(
  type: ViolationType,
  description: string,
  traceField?: string | null
): Violation {
  return {
    type,
    severity: VIOLATION_SEVERITY[type],
    description,
    trace_field: traceField,
  };
}

/** A verification warning (non-critical issue). */
export interface Warning {
  /** Warning type identifier */
  type: string;
  /** Human-readable description */
  description: string;
  /** JSON path to the relevant field */
  trace_field?: string | null;
}

/** Metadata about the verification process. */
export interface VerificationMetadata {
  /** Verification algorithm version */
  algorithm_version: string;
  /** List of checks that were performed */
  checks_performed: string[];
  /** Time taken to perform verification in milliseconds */
  duration_ms?: number | null;
}

/** Result of verifying an AP-Trace against an Alignment Card (SPEC Section 7.4). */
export interface VerificationResult {
  /** True if no violations were found */
  verified: boolean;
  /** ID of the verified trace */
  trace_id: string;
  /** ID of the Alignment Card used */
  card_id: string;
  /** When verification was performed (ISO 8601) */
  timestamp: string;
  /** List of violations found */
  violations: Violation[];
  /** List of non-critical warnings */
  warnings: Warning[];
  /** Metadata about the verification process */
  verification_metadata: VerificationMetadata;
}

/** Categories of behavioral drift (SPEC Section 8.5). */
export type DriftDirection =
  | "autonomy_expansion"
  | "value_drift"
  | "principal_misalignment"
  | "communication_drift"
  | "unknown";

/** A specific indicator of behavioral drift. */
export interface DriftIndicator {
  /** Indicator identifier */
  indicator: string;
  /** Expected/baseline value */
  baseline: number;
  /** Currently observed value */
  current: number;
  /** Human-readable explanation */
  description: string;
}

/** Detailed analysis of detected drift. */
export interface DriftAnalysis {
  /** Current similarity to declared alignment (0.0 to 1.0) */
  similarity_score: number;
  /** Number of consecutive low-similarity traces */
  sustained_traces: number;
  /** Similarity threshold used */
  threshold: number;
  /** Categorized direction of drift */
  drift_direction: DriftDirection;
  /** Specific drift indicators */
  specific_indicators: DriftIndicator[];
}

/** Alert generated when sustained drift is detected (SPEC Section 8.4). */
export interface DriftAlert {
  /** Type of alert */
  alert_type: "drift_detected";
  /** Agent exhibiting drift */
  agent_id: string;
  /** Alignment Card being drifted from */
  card_id: string;
  /** When drift was detected (ISO 8601) */
  detection_timestamp: string;
  /** Drift analysis details */
  analysis: DriftAnalysis;
  /** Recommended action */
  recommendation: string;
  /** IDs of traces exhibiting drift */
  trace_ids: string[];
}

/** Analysis of value alignment between two cards. */
export interface ValueAlignment {
  /** Values present in both cards */
  matched: string[];
  /** Values in one card but not the other */
  unmatched: string[];
  /** Direct value conflicts */
  conflicts: ValueConflictResult[];
}

/** A conflict between values declared by two agents. */
export interface ValueConflictResult {
  /** Value from initiating agent */
  initiator_value: string;
  /** Value from responding agent */
  responder_value: string;
  /** Type of conflict (incompatible, priority_mismatch, etc.) */
  conflict_type: string;
  /** Human-readable explanation */
  description: string;
}

/** Result of checking value coherence between two Alignment Cards. */
export interface CoherenceResult {
  /** Whether the cards are compatible for coordination */
  compatible: boolean;
  /** Coherence score (0.0 to 1.0) */
  score: number;
  /** Detailed value alignment analysis */
  value_alignment: ValueAlignment;
  /** Whether to proceed with coordination */
  proceed: boolean;
  /** Conditions for proceeding (if any) */
  conditions: string[];
  /** Proposed conflict resolution (if conflicts exist) */
  proposed_resolution?: { type: string; reason: string } | null;
}
