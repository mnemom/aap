/**
 * Alignment Card schema - Agent alignment declaration.
 *
 * Defines the Alignment Card structure per SPEC Section 4. An Alignment Card
 * is a structured document declaring an agent's alignment posture.
 *
 * @see SPEC.md Section 4 for complete specification.
 */

/** Type of principal the agent serves. */
export type PrincipalType = "human" | "organization" | "agent" | "unspecified";

/** Nature of authority delegation from principal to agent. */
export type RelationshipType = "delegated_authority" | "advisory" | "autonomous";

/** How value conflicts are resolved. */
export type HierarchyType = "lexicographic" | "weighted" | "contextual";

/** Action to take when escalation trigger matches. */
export type TriggerAction = "escalate" | "deny" | "log";

/** Audit log storage type. */
export type StorageType = "local" | "remote" | "distributed";

/** Tamper-evidence mechanism for audit logs. */
export type TamperEvidence = "append_only" | "signed" | "merkle";

/** Principal relationship declaration (SPEC Section 4.3). */
export interface Principal {
  /** Type of principal */
  type: PrincipalType;
  /** Principal identifier (DID, email, org ID) */
  identifier?: string | null;
  /** Nature of authority delegation */
  relationship: RelationshipType;
  /** Endpoint for escalation notifications */
  escalation_contact?: string | null;
}

/** Definition of a custom value. */
export interface ValueDefinition {
  /** Human-readable name */
  name: string;
  /** What this value means operationally */
  description: string;
  /** Priority for lexicographic ordering (higher = more important) */
  priority?: number;
}

/** Value declarations (SPEC Section 4.4). */
export interface Values {
  /** List of value identifiers */
  declared: string[];
  /** Definitions for non-standard values */
  definitions?: Record<string, ValueDefinition> | null;
  /** Values this agent refuses to coordinate with */
  conflicts_with?: string[] | null;
  /** How value conflicts are resolved */
  hierarchy?: HierarchyType | null;
}

/** Condition that triggers escalation (SPEC Section 4.5). */
export interface EscalationTrigger {
  /** Condition expression (see SPEC Section 4.6) */
  condition: string;
  /** Action to take when trigger matches */
  action: TriggerAction;
  /** Human-readable explanation */
  reason: string;
}

/** Monetary value specification. */
export interface MonetaryValue {
  /** Numeric amount */
  amount: number;
  /** ISO 4217 currency code */
  currency?: string;
}

/** Autonomy bounds and escalation triggers (SPEC Section 4.5). */
export interface AutonomyEnvelope {
  /** Actions permitted without escalation */
  bounded_actions: string[];
  /** Conditions requiring escalation */
  escalation_triggers: EscalationTrigger[];
  /** Maximum transaction value without escalation */
  max_autonomous_value?: MonetaryValue | null;
  /** Actions never permitted */
  forbidden_actions?: string[] | null;
}

/** Audit log storage configuration. */
export interface AuditStorage {
  /** Storage type */
  type: StorageType;
  /** Storage endpoint or location */
  location?: string | null;
}

/** Audit trail commitments (SPEC Section 4.7). */
export interface AuditCommitment {
  /** Trace format identifier */
  trace_format?: string;
  /** Minimum retention period in days */
  retention_days: number;
  /** Storage configuration */
  storage?: AuditStorage | null;
  /** Whether traces can be queried externally */
  queryable: boolean;
  /** Endpoint for trace queries (required if queryable=true) */
  query_endpoint?: string | null;
  /** Tamper-evidence mechanism */
  tamper_evidence?: TamperEvidence | null;
}

/**
 * Alignment Card - Agent alignment declaration (SPEC Section 4).
 *
 * A structured document declaring an agent's alignment posture. It MUST be
 * machine-readable (JSON) and SHOULD be human-readable.
 */
export interface AlignmentCard {
  /** AAP specification version */
  aap_version?: string;
  /** Unique identifier for this card (UUID or URI) */
  card_id: string;
  /** Identifier for the agent (DID, URL, or UUID) */
  agent_id: string;
  /** When this card was issued (ISO 8601) */
  issued_at: string;
  /** When this card expires (ISO 8601) */
  expires_at?: string | null;
  /** Principal relationship declaration */
  principal: Principal;
  /** Value declarations */
  values: Values;
  /** Autonomy bounds and escalation triggers */
  autonomy_envelope: AutonomyEnvelope;
  /** Audit trail commitments */
  audit_commitment: AuditCommitment;
  /** Protocol-specific extensions */
  extensions?: Record<string, unknown> | null;
}

// Utility functions

/** Check if an alignment card has expired. */
export function isCardExpired(card: AlignmentCard): boolean {
  if (!card.expires_at) return false;
  return new Date() > new Date(card.expires_at);
}

/** Check if a value is declared in the card. */
export function hasValue(card: AlignmentCard, value: string): boolean {
  return card.values.declared.includes(value);
}

/** Check if an action is in the bounded actions list. */
export function isActionBounded(card: AlignmentCard, action: string): boolean {
  return card.autonomy_envelope.bounded_actions.includes(action);
}

/** Check if an action is forbidden. */
export function isActionForbidden(card: AlignmentCard, action: string): boolean {
  return (card.autonomy_envelope.forbidden_actions ?? []).includes(action);
}
