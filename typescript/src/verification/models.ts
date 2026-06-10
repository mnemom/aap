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
  /** SSM analysis details when behavioral similarity is computed */
  similarity_details?: Record<string, unknown> | null;
}

/**
 * What a consumer should do based on verification outcome.
 * - `"proceed"` — no violations, no warnings; continue normally
 * - `"review"` — no violations, but warnings present; log and proceed with care
 * - `"deny"` — violations found; block the action and surface to operator
 */
export type VerificationRecommendation = "proceed" | "review" | "deny";

/** Result of verifying an AP-Trace against an Alignment Card (SPEC Section 7.4). */
export interface VerificationResult {
  /** True if no violations were found */
  verified: boolean;
  /**
   * Explicit action recommendation derived from violations and warnings.
   * Prefer this over branching on `verified` alone — it distinguishes
   * warning-only results ("review") from clean results ("proceed").
   */
  recommended_action: VerificationRecommendation;
  /** ID of the verified trace */
  trace_id: string;
  /** ID of the Alignment Card used */
  card_id: string;
  /** When verification was performed (ISO 8601 UTC) */
  timestamp: string;
  /** List of violations found */
  violations: Violation[];
  /** List of non-critical warnings */
  warnings: Warning[];
  /** Behavioral similarity to Alignment Card (0.0–1.0) */
  similarity_score: number;
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

// --- Fleet Coherence Types (E-05: N-Way Value Coherence) ---

/** A single pairwise coherence entry in the fleet matrix. */
export interface PairwiseEntry {
  /** First agent ID */
  agent_a: string;
  /** Second agent ID */
  agent_b: string;
  /** Pairwise coherence result */
  result: CoherenceResult;
}

/** An agent flagged as an outlier in fleet coherence. */
export interface FleetOutlier {
  /** Agent ID */
  agent_id: string;
  /** Agent's mean pairwise score */
  agent_mean_score: number;
  /** Fleet-wide mean score */
  fleet_mean_score: number;
  /** Standard deviations below fleet mean */
  deviation: number;
  /** Values causing primary conflicts */
  primary_conflicts: string[];
}

/** A cluster of compatible agents. */
export interface FleetCluster {
  /** Cluster identifier */
  cluster_id: number;
  /** Agent IDs in this cluster */
  agent_ids: string[];
  /** Mean coherence score within the cluster */
  internal_coherence: number;
  /** Values shared by all agents in the cluster */
  shared_values: string[];
  /** Values that distinguish this cluster from others */
  distinguishing_values: string[];
}

/** A value dimension where agents diverge. */
export interface ValueDivergence {
  /** The value in question */
  value: string;
  /** Agent IDs that declare this value */
  agents_declaring: string[];
  /** Agent IDs missing this value */
  agents_missing: string[];
  /** Agent IDs whose conflicts_with includes this value */
  agents_conflicting: string[];
  /** Estimated impact on fleet score if resolved */
  impact_on_fleet_score: number;
}

/** Summary of one agent's position in the fleet. */
export interface AgentCoherenceSummary {
  /** Agent ID */
  agent_id: string;
  /** Mean pairwise score with all other agents */
  mean_score: number;
  /** Number of compatible pairs */
  compatible_count: number;
  /** Number of conflicting pairs */
  conflict_count: number;
  /** Cluster this agent belongs to */
  cluster_id: number;
  /** Whether this agent is flagged as an outlier */
  is_outlier: boolean;
}

/** Result of N-way fleet coherence analysis. */
export interface FleetCoherenceResult {
  /** Mean of all pairwise coherence scores */
  fleet_score: number;
  /** Minimum pairwise score (weakest link) */
  min_pair_score: number;
  /** Maximum pairwise score */
  max_pair_score: number;
  /** Number of agents analyzed */
  agent_count: number;
  /** Number of pairwise comparisons */
  pair_count: number;
  /** All pairwise coherence results */
  pairwise_matrix: PairwiseEntry[];
  /** Agents flagged as outliers */
  outliers: FleetOutlier[];
  /** Clusters of compatible agents */
  clusters: FleetCluster[];
  /** Value dimensions where agents diverge */
  divergence_report: ValueDivergence[];
  /** Per-agent coherence summaries */
  agent_summaries: AgentCoherenceSummary[];
}

// --- Fault Line Analysis Types (E-06: Fault Line Detection) ---

/** Classification of a fault line's nature. */
export type FaultLineClassification =
  | 'resolvable'
  | 'priority_mismatch'
  | 'incompatible'
  | 'complementary';

/** A single fault line — a value dimension that splits the fleet. */
export interface FaultLine {
  /** Deterministic ID for this fault line */
  id: string;
  /** The value in question */
  value: string;
  /** How the fault line is classified */
  classification: FaultLineClassification;
  /** Severity based on impact_score */
  severity: Severity;
  /** Agent IDs that declare this value */
  agents_declaring: string[];
  /** Agent IDs missing this value */
  agents_missing: string[];
  /** Agent IDs whose conflicts_with includes this value */
  agents_conflicting: string[];
  /** Weighted impact score (0.0 to 1.0) */
  impact_score: number;
  /** Plain-English resolution hint */
  resolution_hint: string;
  /** Bounded actions shared by all involved agents */
  affects_capabilities: string[];
}

/** Aggregated summary of fault lines by classification. */
export interface FaultLineSummary {
  /** Total number of fault lines */
  total: number;
  /** Count of resolvable fault lines */
  resolvable: number;
  /** Count of priority_mismatch fault lines */
  priority_mismatch: number;
  /** Count of incompatible fault lines */
  incompatible: number;
  /** Count of complementary fault lines */
  complementary: number;
  /** Count of critical-severity fault lines */
  critical_count: number;
}

/** A pattern where the same set of agents is consistently isolated across multiple fault lines. */
export interface FaultLineAlignment {
  /** Deterministic ID */
  id: string;
  /** IDs of the fault lines that form this alignment */
  fault_line_ids: string[];
  /** Agents consistently missing from this group of fault lines */
  minority_agents: string[];
  /** Agents consistently declaring this group of fault lines */
  majority_agents: string[];
  /** Mean Jaccard similarity within the alignment group */
  alignment_score: number;
  /** Severity of the alignment pattern */
  severity: Severity;
  /** Human-readable description */
  description: string;
}

/** Full fault line analysis result. */
export interface FaultLineAnalysis {
  /** Deterministic analysis identifier */
  analysis_id: string;
  /** Fleet coherence score (from FleetCoherenceResult) */
  fleet_score: number;
  /** Detected fault lines, sorted by severity then impact_score desc */
  fault_lines: FaultLine[];
  /** Detected alignment patterns */
  alignments: FaultLineAlignment[];
  /** Counts by classification */
  summary: FaultLineSummary;
}
