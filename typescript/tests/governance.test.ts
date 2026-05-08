/**
 * Tests for governance signal types + helpers (ADR-048).
 *
 * Pure-logic coverage of severity ordering and source-narrowing type
 * guards. Operator-shaped consumers (dashboards, webhook subscribers,
 * alerting tools) use these types; the platform never injects
 * governance signals into agent prompts (ADR-048's 2026-05-07
 * amendment retracted the earlier sovereign-composer carve-out).
 */

import { describe, it, expect } from "vitest";
import {
  isCoherenceSignal,
  isDriftSignal,
  isFaultLineSignal,
  isFleetSignal,
  SEVERITY_ORDER,
  severityAtLeast,
  type GovernanceSignal,
} from "../src/governance";

function makeSignal(overrides: Partial<GovernanceSignal> = {}): GovernanceSignal {
  return {
    id: "gs-test01",
    scope: "team",
    scope_id: "team-1",
    source: "sideband.fleet",
    pattern_type: "cluster_partition",
    severity: "high",
    detected_at: "2026-05-07T00:00:00Z",
    detected_by: "observer.sweepFleet",
    org_id: "org-1",
    team_id: "team-1",
    agent_ids: ["agent-1", "agent-2"],
    detail: {},
    source_ref: {},
    status: "open",
    acknowledged_by: null,
    acknowledged_at: null,
    acknowledged_actor_role: null,
    resolution_status: null,
    action_taken: null,
    resolved_by: null,
    resolved_at: null,
    expires_at: null,
    webhook_delivery_id: null,
    notification_state: {},
    created_at: "2026-05-07T00:00:00Z",
    updated_at: "2026-05-07T00:00:00Z",
    ...overrides,
  };
}

describe("severity helpers", () => {
  it("orders info < warn < high < critical", () => {
    expect(SEVERITY_ORDER.info).toBeLessThan(SEVERITY_ORDER.warn);
    expect(SEVERITY_ORDER.warn).toBeLessThan(SEVERITY_ORDER.high);
    expect(SEVERITY_ORDER.high).toBeLessThan(SEVERITY_ORDER.critical);
  });

  it("severityAtLeast", () => {
    expect(severityAtLeast("critical", "high")).toBe(true);
    expect(severityAtLeast("high", "high")).toBe(true);
    expect(severityAtLeast("warn", "high")).toBe(false);
  });
});

describe("source-narrowing type guards", () => {
  it("isFleetSignal narrows correctly", () => {
    expect(isFleetSignal(makeSignal({ source: "sideband.fleet" }))).toBe(true);
    expect(isFleetSignal(makeSignal({ source: "sideband.coherence" }))).toBe(false);
  });

  it("isCoherenceSignal narrows correctly", () => {
    expect(isCoherenceSignal(makeSignal({ source: "sideband.coherence" }))).toBe(true);
    expect(isCoherenceSignal(makeSignal({ source: "sideband.fleet" }))).toBe(false);
  });

  it("isFaultLineSignal narrows correctly", () => {
    expect(isFaultLineSignal(makeSignal({ source: "sideband.fault_line" }))).toBe(true);
    expect(isFaultLineSignal(makeSignal({ source: "sideband.fleet" }))).toBe(false);
  });

  it("isDriftSignal narrows correctly", () => {
    expect(isDriftSignal(makeSignal({ source: "sideband.drift" }))).toBe(true);
    expect(isDriftSignal(makeSignal({ source: "sideband.fleet" }))).toBe(false);
  });

  it("Wintermute cluster_partition shape narrows to fleet", () => {
    const wintermuteSignal = makeSignal({
      source: "sideband.fleet",
      pattern_type: "cluster_partition",
      severity: "high",
      team_id: "12ad0b6b-caba-41fd-991f-ab6b2bd0c395",
      agent_ids: ["agent-wintermute", "agent-2", "agent-3", "agent-4", "agent-5"],
    });
    expect(isFleetSignal(wintermuteSignal)).toBe(true);
  });
});
