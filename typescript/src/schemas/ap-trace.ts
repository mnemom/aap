/**
 * AP-Trace schema - Audit log format for agent decisions.
 *
 * Defines the AP-Trace structure per SPEC Section 5. An AP-Trace entry
 * records an agent's decision process.
 *
 * @see SPEC.md Section 5 for complete specification.
 */

/** Type of action taken or considered. */
export type ActionType = "recommend" | "execute" | "escalate" | "deny";

/** How the action relates to the autonomy envelope. */
export type ActionCategory = "bounded" | "escalation_trigger" | "forbidden";

/** Status of an escalation. */
export type EscalationStatus = "pending" | "approved" | "denied" | "timeout";

/** Resource affected by the action. */
export interface ActionTarget {
  /** Resource type */
  type: string;
  /** Resource identifier */
  identifier: string;
}

/** Action taken or considered (SPEC Section 5.4). */
export interface Action {
  /** Action type */
  type: ActionType;
  /** Human-readable action name */
  name: string;
  /** How this action relates to autonomy envelope */
  category: ActionCategory;
  /** Resource affected */
  target?: ActionTarget | null;
  /** Action parameters */
  parameters?: Record<string, unknown> | null;
}

/** An alternative considered during decision-making. */
export interface Alternative {
  /** Unique identifier for this option */
  option_id: string;
  /** Human-readable description */
  description: string;
  /** Computed score (0.0 to 1.0) */
  score?: number | null;
  /** Breakdown of score components */
  scoring_factors?: Record<string, number> | null;
  /** Concerns or flags about this option */
  flags?: string[] | null;
}

/** Decision process record (SPEC Section 5.5). */
export interface Decision {
  /** Options evaluated (minimum 1) */
  alternatives_considered: Alternative[];
  /** Option ID selected */
  selected: string;
  /** Human-readable explanation of why this was chosen */
  selection_reasoning: string;
  /** Values that influenced this decision */
  values_applied: string[];
  /** Decision confidence (0.0 to 1.0) */
  confidence?: number | null;
}

/** Record of checking an escalation trigger. */
export interface TriggerCheck {
  /** Trigger condition that was checked */
  trigger: string;
  /** Whether the trigger matched */
  matched: boolean;
  /** Observed value (for comparison triggers) */
  value_observed?: unknown | null;
}

/** Response from principal to escalation. */
export interface PrincipalResponse {
  /** Principal's decision */
  decision: string;
  /** When decision was made (ISO 8601) */
  timestamp: string;
  /** Conditions attached to approval */
  conditions?: string[] | null;
}

/** Escalation evaluation record (SPEC Section 5.6). */
export interface Escalation {
  /** Whether escalation was evaluated */
  evaluated: boolean;
  /** Triggers that were evaluated */
  triggers_checked?: TriggerCheck[] | null;
  /** Whether escalation is required */
  required: boolean;
  /** Human-readable explanation */
  reason: string;
  /** Escalation request ID (if escalation required) */
  escalation_id?: string | null;
  /** Status of escalation (if escalation required) */
  escalation_status?: EscalationStatus | null;
  /** Principal's response (if escalation required) */
  principal_response?: PrincipalResponse | null;
}

/** Additional context for the trace (SPEC Section 5.7). */
export interface TraceContext {
  /** Session identifier */
  session_id?: string | null;
  /** Turn number in conversation */
  conversation_turn?: number | null;
  /** IDs of related prior traces */
  prior_trace_ids?: string[] | null;
  /** Environment metadata (client, locale, etc.) */
  environment?: Record<string, unknown> | null;
  /** Additional arbitrary metadata */
  metadata?: Record<string, unknown> | null;
}

/**
 * AP-Trace - Audit log entry for agent decisions (SPEC Section 5).
 *
 * An AP-Trace records an agent's decision process, enabling verification
 * that observed behavior is consistent with declared alignment.
 */
export interface APTrace {
  /** Unique identifier (UUID) */
  trace_id: string;
  /** Agent that generated this trace */
  agent_id: string;
  /** Alignment Card in effect */
  card_id: string;
  /** When this trace was created (ISO 8601) */
  timestamp: string;
  /** Action taken or considered */
  action: Action;
  /** Decision process record */
  decision: Decision;
  /** Escalation evaluation (if applicable) */
  escalation?: Escalation | null;
  /** Additional context */
  context?: TraceContext | null;
}

// Utility functions

/** Get the selected alternative from the decision. */
export function getSelectedAlternative(trace: APTrace): Alternative | undefined {
  return trace.decision.alternatives_considered.find(
    (alt) => alt.option_id === trace.decision.selected
  );
}

/** Check if this decision was escalated. */
export function wasEscalated(trace: APTrace): boolean {
  return trace.escalation != null && trace.escalation.required;
}

/** Check if the action was forbidden or triggered unhandled escalation. */
export function hadViolations(trace: APTrace): boolean {
  return trace.action.category === "forbidden";
}
