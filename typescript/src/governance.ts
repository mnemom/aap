/**
 * Governance signal types — ADR-048.
 *
 * Operator-actionable observations produced by Mnemom platform detectors
 * (sideband.coherence, sideband.fault_line, sideband.fleet, sideband.drift,
 * future protection.* / posture.*). Surfaced via:
 *
 *   - REST: GET /v1/{orgs,teams,agents}/.../governance/signals
 *   - Webhook: governance.signal.{fired,acknowledged,resolved,dismissed}
 *
 * These types mirror the platform schema so operator-shaped consumers
 * (dashboards, webhook subscribers, alerting tools, audit pipelines)
 * can type-check against a stable contract.
 *
 * IMPORTANT: governance signals are operator-facing observations. The
 * platform never injects them into agent prompts and offers no surface
 * for prompt-time composition. (ADR-048's 2026-05-07 amendment retracted
 * the earlier "application-owned sovereign-agent composer" carve-out.)
 *
 * @see https://docs.mnemom.ai/concepts/governance-signals
 */

// ────────────────────────────────────────────────────────────────────────────
// Closed enums (mirror platform DB CHECK constraints)
// ────────────────────────────────────────────────────────────────────────────

export type GovernanceSignalScope = "platform" | "org" | "team" | "agent";

/**
 * Closed source enum per ADR-048 §1. Future protection.* / posture.* sources
 * land via ADR-048 amendment + platform migration.
 */
export type GovernanceSignalSource =
  | "sideband.drift"
  | "sideband.coherence"
  | "sideband.fault_line"
  | "sideband.fleet";

export type GovernanceSignalSeverity = "info" | "warn" | "high" | "critical";

export type GovernanceSignalStatus =
  | "open"
  | "acknowledged"
  | "resolved"
  | "dismissed"
  | "expired";

/**
 * Closed actor-role enum per ADR-046 (audit-actor model). Captured at
 * acknowledge/resolve/dismiss time so operator audit can reconstruct the
 * highest-applicable role of the acknowledging actor.
 */
export type GovernanceActorRole =
  | "platform_admin"
  | "org_owner"
  | "org_admin"
  | "team_admin"
  | "member"
  | "system";

export type GovernanceResolutionStatus =
  | "action_taken"
  | "wont_fix"
  | "duplicate"
  | "false_positive"
  | "self_resolved";

export type GovernanceNotificationChannel =
  | "webhook"
  | "slack"
  | "email"
  | "pagerduty";

// ────────────────────────────────────────────────────────────────────────────
// Pattern-type taxonomy per source
// ────────────────────────────────────────────────────────────────────────────

/**
 * For sideband.fleet: three pattern types ratified at ADR-048 amendment
 * time (mirroring observer's sweepFleet). Future fleet patterns land
 * additively.
 */
export type GovernanceFleetPatternType =
  | "cluster_partition"
  | "outliers"
  | "min_pair_score";

/** For sideband.coherence: three trigger conditions from sweepCoherence. */
export type GovernanceCoherencePatternType =
  | "pairwise_governance_floor"
  | "conflict_edge_count"
  | "outlier_agents_count";

// ────────────────────────────────────────────────────────────────────────────
// Source_ref shapes (per-source structured payload)
// ────────────────────────────────────────────────────────────────────────────

export interface GovernanceSourceRefBase {
  /** Sweep ID from the observer cron tick. */
  sweep_id?: string;
  /** Cadence (in seconds) the sweep was running on at detection time. */
  cadence_seconds?: number;
  /** Posture revision active at detection time, for compliance audit. */
  posture_revision?: string;
}

export interface GovernanceFleetSourceRef extends GovernanceSourceRefBase {
  pattern_type: GovernanceFleetPatternType;
  cluster_count?: number;
  cluster_ids?: string[];
  min_pair_score?: number;
  threshold?: number;
  weakest_pair?: [string, string];
  outlier_agent_ids?: string[];
}

export interface GovernanceCoherenceSourceRef extends GovernanceSourceRefBase {
  pattern_type: GovernanceCoherencePatternType;
  pairwise_governance_floor?: number;
  conflict_edge_count?: number;
  outlier_agent_ids?: string[];
}

export interface GovernanceFaultLineSourceRef extends GovernanceSourceRefBase {
  fault_line_id: string;
  value: string;
  severity: GovernanceSignalSeverity;
  impact_score: number;
  classification?: string;
}

export interface GovernanceDriftSourceRef extends GovernanceSourceRefBase {
  drift_alert_id: string;
  direction?: string;
  similarity?: number;
}

export type GovernanceSourceRef =
  | GovernanceFleetSourceRef
  | GovernanceCoherenceSourceRef
  | GovernanceFaultLineSourceRef
  | GovernanceDriftSourceRef;

// ────────────────────────────────────────────────────────────────────────────
// Notification dispatch state
// ────────────────────────────────────────────────────────────────────────────

export type GovernanceNotificationDispatchState =
  | "queued"
  | "delivered"
  | "failed"
  | "skipped";

export interface GovernanceNotificationChannelState {
  state: GovernanceNotificationDispatchState;
  attempts: number;
  destination_id?: string;
  delivered_at?: string;
  last_error?: string;
}

export type GovernanceNotificationState = Partial<
  Record<GovernanceNotificationChannel, GovernanceNotificationChannelState>
> & {
  /** Set true on backfilled rows to suppress dispatch (cutover guard). */
  skipped?: boolean;
};

// ────────────────────────────────────────────────────────────────────────────
// Core row + webhook event shapes
// ────────────────────────────────────────────────────────────────────────────

export interface GovernanceSignal {
  id: string;
  scope: GovernanceSignalScope;
  scope_id: string;
  source: GovernanceSignalSource;
  pattern_type: string;
  severity: GovernanceSignalSeverity;

  detected_at: string;
  detected_by: string;

  org_id: string;
  team_id: string | null;
  agent_ids: string[];

  detail: Record<string, unknown>;
  source_ref: GovernanceSourceRef | Record<string, unknown>;

  status: GovernanceSignalStatus;
  acknowledged_by: string | null;
  acknowledged_at: string | null;
  acknowledged_actor_role: GovernanceActorRole | null;

  resolution_status: GovernanceResolutionStatus | null;
  action_taken: string | null;
  resolved_by: string | null;
  resolved_at: string | null;

  expires_at: string | null;

  webhook_delivery_id: string | null;
  notification_state: GovernanceNotificationState;

  created_at: string;
  updated_at: string;
}

/**
 * Webhook event taxonomy (per ADR-048 §4). Subscribers receive these
 * over HTTP POST with X-Mnemom-Signature: sha256=... HMAC headers.
 */
export type GovernanceWebhookEventType =
  | "governance.signal.fired"
  | "governance.signal.acknowledged"
  | "governance.signal.resolved"
  | "governance.signal.dismissed"
  | "governance.escalation.triggered";

export interface GovernanceWebhookEnvelope {
  event: GovernanceWebhookEventType;
  signal_id: string;
  delivered_at: string;
  payload: GovernanceSignal;
}

// ────────────────────────────────────────────────────────────────────────────
// Type guards (helpful for source-ref narrowing)
// ────────────────────────────────────────────────────────────────────────────

export function isFleetSignal(
  signal: GovernanceSignal,
): signal is GovernanceSignal & { source: "sideband.fleet" } {
  return signal.source === "sideband.fleet";
}

export function isCoherenceSignal(
  signal: GovernanceSignal,
): signal is GovernanceSignal & { source: "sideband.coherence" } {
  return signal.source === "sideband.coherence";
}

export function isFaultLineSignal(
  signal: GovernanceSignal,
): signal is GovernanceSignal & { source: "sideband.fault_line" } {
  return signal.source === "sideband.fault_line";
}

export function isDriftSignal(
  signal: GovernanceSignal,
): signal is GovernanceSignal & { source: "sideband.drift" } {
  return signal.source === "sideband.drift";
}

// ────────────────────────────────────────────────────────────────────────────
// Severity helpers
// ────────────────────────────────────────────────────────────────────────────

export const SEVERITY_ORDER: Record<GovernanceSignalSeverity, number> = {
  info: 0,
  warn: 1,
  high: 2,
  critical: 3,
};

export function severityAtLeast(
  observed: GovernanceSignalSeverity,
  floor: GovernanceSignalSeverity,
): boolean {
  return SEVERITY_ORDER[observed] >= SEVERITY_ORDER[floor];
}
