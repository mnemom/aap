/**
 * Alignment Card schema - Agent alignment declaration (unified / ADR-039).
 *
 * Defines the unified Alignment Card structure accepted by the Mnemom platform
 * and `mnemom card validate`. It renames the legacy AAP 0.5.0
 * `autonomy_envelope`->`autonomy` and `audit_commitment`->`audit`, replaces
 * `aap_version` with the date-anchored `card_version`, and adds the two
 * top-level master switches `autonomy_mode` + `integrity_mode`. Semantics are
 * preserved; the migration is largely a rename.
 *
 * @see https://docs.mnemom.ai/specifications/alignment-card-schema
 */

/**
 * Master-switch mode shared by `autonomy_mode` and `integrity_mode`
 * (unified / ADR-039). Strictest wins on composition:
 * `enforce > nudge > observe > off`.
 */
export type AlignmentMode = "off" | "observe" | "nudge" | "enforce";

/** Current unified alignment-card schema version (date-anchored identifier). */
export const CARD_VERSION = "unified/2026-04-26";

/** Type of principal the agent serves. */
export type PrincipalType = "human" | "organization" | "agent" | "unspecified";

/** Nature of authority delegation from principal to agent. */
export type RelationshipType =
  | "delegated_authority"
  | "advisory"
  | "autonomous";

/** How value conflicts are resolved. */
export type HierarchyType = "lexicographic" | "weighted" | "contextual";

/** Action to take when escalation trigger matches. */
export type TriggerAction = "escalate" | "deny" | "log";

/** Tamper-evidence mechanism for audit logs. */
export type TamperEvidence = "append_only" | "signed" | "merkle";

/** Runtime-accessible AlignmentMode values (mirrors the schema $def). */
export const ALIGNMENT_MODES = [
  "off",
  "observe",
  "nudge",
  "enforce",
] as const satisfies ReadonlyArray<AlignmentMode>;

/** Runtime-accessible PrincipalType values (mirrors the schema $def). */
export const PRINCIPAL_TYPES = [
  "human",
  "organization",
  "agent",
  "unspecified",
] as const satisfies ReadonlyArray<PrincipalType>;

/** Runtime-accessible RelationshipType values (mirrors the schema $def). */
export const RELATIONSHIP_TYPES = [
  "delegated_authority",
  "advisory",
  "autonomous",
] as const satisfies ReadonlyArray<RelationshipType>;

/** Runtime-accessible HierarchyType values (mirrors the schema $def). */
export const HIERARCHY_TYPES = [
  "lexicographic",
  "weighted",
  "contextual",
] as const satisfies ReadonlyArray<HierarchyType>;

/** Runtime-accessible TriggerAction values (mirrors the schema $def). */
export const TRIGGER_ACTIONS = [
  "escalate",
  "deny",
  "log",
] as const satisfies ReadonlyArray<TriggerAction>;

/** Runtime-accessible TamperEvidence values (mirrors the schema $def). */
export const TAMPER_EVIDENCES = [
  "append_only",
  "signed",
  "merkle",
] as const satisfies ReadonlyArray<TamperEvidence>;

/** Principal relationship declaration (unified / ADR-039 §principal). */
export interface Principal {
  /** Type of principal */
  type: PrincipalType;
  /** Principal identifier (DID, email, org ID). Required when type != "unspecified". */
  identifier?: string | null;
  /** Nature of authority delegation */
  relationship: RelationshipType;
  /** Endpoint for escalation notifications */
  escalation_contact?: string | null;
}

/** Definition of a custom value (unified / ADR-039 §values). */
export interface ValueDefinition {
  /** Human-readable name (optional; the definitions map key is the value id) */
  name?: string;
  /** What this value means operationally */
  description: string;
  /** Priority for lexicographic/weighted ordering (higher = more important) */
  priority?: number;
}

/**
 * A declared value in parameterized form (SPEC Section 4.4, Phase-3.2+):
 * `id` is the value name, `domain`/`intensity` qualify how it applies.
 * `declared` accepts either this object form or a bare-string id.
 */
export interface ParameterizedValue {
  id: string;
  domain?: string;
  intensity?: string;
}

/** Value declarations (SPEC Section 4.4). */
export interface Values {
  /**
   * Behavioral and ethical values the agent applies in its decision-making.
   *
   * This field is actively monitored by AIP at runtime: every value listed here
   * is expected to appear in AP-Trace `values_applied` fields when it influences
   * a decision. Declaring a value the agent never applies produces verification
   * warnings and degrades trust scoring.
   *
   * **Include**: Ethical and behavioral commitments — e.g. `transparency`,
   * `honesty`, `accuracy`, `safety`, `accountability`, `helpfulness`,
   * `deliberation_before_action`. These describe HOW the agent reasons.
   *
   * **Do not include**: Role capabilities, operational principles, or job-function
   * descriptors — e.g. `fiduciary_precision`, `organizational_clarity`. These
   * describe WHAT the agent is in its role and belong in `extensions.clpi.role`
   * or other `extensions` metadata. Capability names (e.g. `read_documents`)
   * belong in `autonomy.bounded_actions`.
   *
   * Each entry is either a bare-string id (`"honesty"`) or a parameterized
   * object (`{id, domain?, intensity?}`). Use {@link declaredValueIds} to
   * compare against AP-Trace `values_applied` (which are always bare ids) —
   * NEVER `.includes()` raw, or object-form declarations silently mismatch.
   */
  declared: Array<string | ParameterizedValue>;
  /** Definitions for non-standard values */
  definitions?: Record<string, ValueDefinition> | null;
  /** Values this agent refuses to coordinate with */
  conflicts_with?: string[] | null;
  /** How value conflicts are resolved */
  hierarchy?: HierarchyType | null;
}

/** Condition that triggers escalation (unified / ADR-039 §autonomy). */
export interface EscalationTrigger {
  /** Condition expression */
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

/**
 * Autonomy bounds and escalation triggers (unified / ADR-039 §autonomy).
 *
 * Renamed from the legacy AAP 0.5.0 `autonomy_envelope`; semantics preserved.
 * Only `bounded_actions` is required in the unified shape.
 */
export interface Autonomy {
  /** Actions permitted without escalation */
  bounded_actions: string[];
  /** Conditions requiring escalation */
  escalation_triggers?: EscalationTrigger[];
  /** Maximum transaction value without escalation */
  max_autonomous_value?: MonetaryValue | null;
  /** Actions never permitted */
  forbidden_actions?: string[] | null;
}

/**
 * Audit trail commitments (unified / ADR-039 §audit).
 *
 * Renamed from the legacy AAP 0.5.0 `audit_commitment`; semantics preserved.
 * The legacy `storage` sub-object is not part of the unified shape.
 */
export interface Audit {
  /** Trace format identifier */
  trace_format?: string;
  /** Minimum retention period in days */
  retention_days: number;
  /** Whether traces can be queried externally */
  queryable: boolean;
  /** Endpoint for trace queries (required if queryable=true) */
  query_endpoint?: string | null;
  /** Tamper-evidence mechanism */
  tamper_evidence?: TamperEvidence | null;
}

/**
 * Alignment Card - Agent alignment declaration (unified / ADR-039).
 *
 * A structured document declaring an agent's alignment posture. It MUST be
 * machine-readable (JSON) and SHOULD be human-readable. This is the unified
 * card shape accepted by `mnemom card validate` and the Mnemom platform.
 */
export interface AlignmentCard {
  /** Unified alignment-card schema version (date-anchored identifier) */
  card_version?: string;
  /** Unique identifier for this card (UUID or URI) */
  card_id: string;
  /** Identifier for the agent (DID, URL, or UUID) */
  agent_id: string;
  /** When this card was issued (ISO 8601) */
  issued_at: string;
  /** When this card expires (ISO 8601) */
  expires_at?: string | null;
  /** Master switch for the action-policing pipeline */
  autonomy_mode?: AlignmentMode;
  /** Master switch for the values/conscience pipeline */
  integrity_mode?: AlignmentMode;
  /** Principal relationship declaration */
  principal: Principal;
  /** Value declarations */
  values: Values;
  /** Autonomy bounds and escalation triggers */
  autonomy: Autonomy;
  /** Audit trail commitments */
  audit: Audit;
  /** Protocol-specific extensions */
  extensions?: Record<string, unknown> | null;
}

// Utility functions

/**
 * Read the autonomy section from a card. Prefers the unified / ADR-039
 * `autonomy` key, falling back to the legacy AAP 0.5.0 `autonomy_envelope`
 * for interop with older card objects.
 */
export function cardAutonomy(card: AlignmentCard): Autonomy {
  const c = card as AlignmentCard & {
    autonomy_envelope?: Autonomy;
  };
  return c.autonomy ?? c.autonomy_envelope ?? { bounded_actions: [] };
}

/**
 * Read the audit section from a card. Prefers the unified / ADR-039 `audit`
 * key, falling back to the legacy AAP 0.5.0 `audit_commitment` for interop
 * with older card objects.
 */
export function cardAudit(card: AlignmentCard): Audit | undefined {
  const c = card as AlignmentCard & {
    audit_commitment?: Audit;
  };
  return c.audit ?? c.audit_commitment;
}

/** Check if an alignment card has expired. */
export function isCardExpired(card: AlignmentCard): boolean {
  if (!card.expires_at) return false;
  return new Date() > new Date(card.expires_at);
}

/**
 * Normalize a `values.declared` list to bare-string value ids. Declared entries
 * may be bare strings OR parameterized objects (`{id, domain?, intensity?}`);
 * AP-Trace `values_applied` are always bare ids. Compare via this — a raw
 * `.includes()` would silently fail to match an object-form declaration against
 * a bare applied id, falsely flagging it `undeclared_value`.
 */
export function declaredValueIds(
  declared: ReadonlyArray<string | ParameterizedValue> | null | undefined,
): string[] {
  if (!Array.isArray(declared)) return [];
  const ids: string[] = [];
  for (const d of declared) {
    if (typeof d === "string") ids.push(d);
    else if (d && typeof d === "object" && typeof d.id === "string")
      ids.push(d.id);
  }
  return ids;
}

/** Check if a value is declared in the card (id-aware; handles parameterized form). */
export function hasValue(card: AlignmentCard, value: string): boolean {
  return declaredValueIds(card.values.declared).includes(value);
}

/**
 * Normalize `decision.values_applied` to bare string ids (ADR-065 #16).
 *
 * `values_applied` is TYPED `string[]`, but real producers (e.g. the Mnemom
 * observer's fallback/passthrough paths) emit parameterized OBJECTS
 * (`{id, intensity?, domain?}`) — the same shape declared values can take. The
 * undeclared_value check and drift value-usage tallies must compare ids, not
 * raw entries, else an object string-coerces to `'[object Object]'` and either
 * (a) never matches the declared id set → spurious `undeclared_value` deny, or
 * (b) pollutes value-usage maps with a bogus key. Reuses {@link declaredValueIds}
 * (identical string|object→id coercion); accepts the looser runtime shape.
 */
export function appliedValueIds(
  applied: ReadonlyArray<string | ParameterizedValue> | null | undefined,
): string[] {
  return declaredValueIds(applied);
}

/** Check if an action is in the bounded actions list. */
export function isActionBounded(card: AlignmentCard, action: string): boolean {
  return cardAutonomy(card).bounded_actions.includes(action);
}

/** Check if an action is forbidden. */
export function isActionForbidden(
  card: AlignmentCard,
  action: string,
): boolean {
  return (cardAutonomy(card).forbidden_actions ?? []).includes(action);
}
