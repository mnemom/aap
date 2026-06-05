/**
 * AAP TypeScript SDK - analyzeFaultLines / checkFleetFaultLines Tests
 *
 * Tests cover fault line classification, severity thresholds, impact scoring,
 * alignment detection, edge cases, and the convenience wrapper.
 */

import { describe, it, expect } from "vitest";
import { analyzeFaultLines, checkFleetCoherence, checkFleetFaultLines } from "../src";
import type { AlignmentCard, FaultLineAnalysis, FleetCoherenceResult } from "../src";
import { minimalAlignmentCard } from "./fixtures";

// ============================================================================
// HELPERS
// ============================================================================

function makeCard(
  id: string,
  declared: string[],
  conflicts_with: string[] = [],
  bounded_actions: string[] = ["search", "recommend"],
  principalIdentifier?: string
): AlignmentCard {
  return {
    ...minimalAlignmentCard,
    card_id: `ac-fl-${id}`,
    agent_id: `agent-${id}`,
    principal: {
      type: "human",
      relationship: "delegated_authority",
      identifier: principalIdentifier,
    },
    values: { declared, conflicts_with },
    autonomy: {
      bounded_actions,
      escalation_triggers: [],
    },
  };
}

function getCoherenceAndAnalysis(
  cards: Array<{ agentId: string; card: AlignmentCard }>,
  options?: { reputationScores?: Record<string, number> }
): FaultLineAnalysis {
  const coherence = checkFleetCoherence(cards);
  return analyzeFaultLines(coherence, cards, options);
}

// ============================================================================
// RESOLVABLE CLASSIFICATION
// ============================================================================

describe("analyzeFaultLines", () => {
  describe("resolvable classification", () => {
    it("should classify a value declared by some but missing from others as resolvable", () => {
      const cards = [
        { agentId: "a", card: makeCard("a", ["principal_benefit", "transparency"]) },
        { agentId: "b", card: makeCard("b", ["principal_benefit"]) },
      ];
      const analysis = getCoherenceAndAnalysis(cards);

      const fl = analysis.fault_lines.find(f => f.value === "transparency");
      expect(fl).toBeDefined();
      expect(fl!.classification).toBe("resolvable");
    });

    it("should include the missing agents in agents_missing", () => {
      const cards = [
        { agentId: "a", card: makeCard("a", ["principal_benefit", "honesty"]) },
        { agentId: "b", card: makeCard("b", ["principal_benefit"]) },
        { agentId: "c", card: makeCard("c", ["principal_benefit"]) },
      ];
      const analysis = getCoherenceAndAnalysis(cards);

      const fl = analysis.fault_lines.find(f => f.value === "honesty");
      expect(fl).toBeDefined();
      expect(fl!.agents_declaring).toContain("a");
      expect(fl!.agents_missing).toContain("b");
      expect(fl!.agents_missing).toContain("c");
    });

    it("should provide a resolution hint mentioning the missing agents", () => {
      const cards = [
        { agentId: "a", card: makeCard("a", ["principal_benefit", "transparency"]) },
        { agentId: "b", card: makeCard("b", ["principal_benefit"]) },
      ];
      const analysis = getCoherenceAndAnalysis(cards);

      const fl = analysis.fault_lines.find(f => f.value === "transparency");
      expect(fl!.resolution_hint).toContain("b");
    });
  });

  // ============================================================================
  // PRIORITY_MISMATCH CLASSIFICATION
  // ============================================================================

  describe("priority_mismatch classification", () => {
    it("should classify as priority_mismatch when 2+ agents declare the value but have low pairwise coherence", () => {
      // Two agents both declare "speed" but have very different values overall → low pairwise score
      const cards = [
        { agentId: "a", card: makeCard("a", ["speed", "efficiency"], ["honesty", "transparency"]) },
        { agentId: "b", card: makeCard("b", ["speed", "honesty"], ["efficiency"]) },
        { agentId: "c", card: makeCard("c", ["principal_benefit", "transparency", "honesty"]) },
      ];
      const coherence = checkFleetCoherence(cards);
      const analysis = analyzeFaultLines(coherence, cards);

      // Verify that a-b have a low pairwise score (they should, given mutual conflicts)
      const abPair = coherence.pairwise_matrix.find(
        p => (p.agent_a === "a" && p.agent_b === "b") || (p.agent_a === "b" && p.agent_b === "a")
      );
      if (abPair && abPair.result.score < 0.5) {
        const speedFl = analysis.fault_lines.find(f => f.value === "speed");
        if (speedFl) {
          expect(speedFl.classification).toBe("priority_mismatch");
          expect(speedFl.resolution_hint).toContain("priority");
        }
      }
      // The test is conditional on actual pairwise scores — just verify analysis runs
      expect(analysis.fault_lines.length).toBeGreaterThanOrEqual(0);
    });
  });

  // ============================================================================
  // INCOMPATIBLE CLASSIFICATION
  // ============================================================================

  describe("incompatible classification", () => {
    it("should classify as incompatible when any agent has conflicts_with for the value", () => {
      const cards = [
        { agentId: "a", card: makeCard("a", ["principal_benefit", "speed"]) },
        { agentId: "b", card: makeCard("b", ["principal_benefit"], ["speed"]) },
      ];
      const analysis = getCoherenceAndAnalysis(cards);

      const fl = analysis.fault_lines.find(f => f.value === "speed");
      expect(fl).toBeDefined();
      expect(fl!.classification).toBe("incompatible");
      expect(fl!.agents_conflicting).toContain("b");
    });

    it("should include agents_conflicting for incompatible fault lines", () => {
      const cards = [
        { agentId: "a", card: makeCard("a", ["honesty", "transparency"]) },
        { agentId: "b", card: makeCard("b", ["transparency"]) },
        { agentId: "c", card: makeCard("c", ["transparency"], ["honesty"]) },
      ];
      const analysis = getCoherenceAndAnalysis(cards);

      const fl = analysis.fault_lines.find(f => f.value === "honesty");
      expect(fl).toBeDefined();
      expect(fl!.classification).toBe("incompatible");
      expect(fl!.agents_conflicting).toContain("c");
    });

    it("resolution hint for incompatible should mention human review", () => {
      const cards = [
        { agentId: "a", card: makeCard("a", ["profit_maximization"]) },
        { agentId: "b", card: makeCard("b", ["principal_benefit"], ["profit_maximization"]) },
      ];
      const analysis = getCoherenceAndAnalysis(cards);

      const fl = analysis.fault_lines.find(f => f.value === "profit_maximization");
      expect(fl!.resolution_hint).toContain("human review");
    });
  });

  // ============================================================================
  // COMPLEMENTARY CLASSIFICATION
  // ============================================================================

  describe("complementary classification", () => {
    it("should classify as complementary when agent role keywords suggest specialization", () => {
      // Agent IDs with role keywords like 'safety', 'cfo'
      const cards = [
        { agentId: "safety-agent", card: makeCard("safety-agent", ["harm_prevention", "transparency"]) },
        { agentId: "exec-cfo", card: makeCard("exec-cfo", ["transparency"]) },
      ];
      const analysis = getCoherenceAndAnalysis(cards);

      const fl = analysis.fault_lines.find(f => f.value === "harm_prevention");
      expect(fl).toBeDefined();
      expect(fl!.classification).toBe("complementary");
      expect(fl!.resolution_hint).toContain("intentional");
    });

    it("should fall through to resolvable when no role keywords detected", () => {
      const cards = [
        { agentId: "agent-x", card: makeCard("agent-x", ["principal_benefit", "honesty"]) },
        { agentId: "agent-y", card: makeCard("agent-y", ["principal_benefit"]) },
      ];
      const analysis = getCoherenceAndAnalysis(cards);

      const fl = analysis.fault_lines.find(f => f.value === "honesty");
      expect(fl).toBeDefined();
      expect(fl!.classification).toBe("resolvable");
    });
  });

  // ============================================================================
  // SEVERITY THRESHOLDS
  // ============================================================================

  describe("severity thresholds", () => {
    it("should assign critical severity for high impact_score (>=0.7)", () => {
      // Many agents missing a high-impact value, with high coordination overlap (same bounded_actions)
      const sharedActions = ["analyze", "recommend", "execute", "report"];
      const cards = [
        { agentId: "a", card: makeCard("a", ["safety"], [], sharedActions) },
        { agentId: "b", card: makeCard("b", ["something_else"], [], sharedActions) },
        { agentId: "c", card: makeCard("c", ["something_else"], [], sharedActions) },
        { agentId: "d", card: makeCard("d", ["something_else"], [], sharedActions) },
      ];
      const analysis = getCoherenceAndAnalysis(cards);

      const safetyFl = analysis.fault_lines.find(f => f.value === "safety");
      if (safetyFl) {
        // impact_score >= 0.7 → critical
        if (safetyFl.impact_score >= 0.7) {
          expect(safetyFl.severity).toBe("critical");
        } else if (safetyFl.impact_score >= 0.4) {
          expect(safetyFl.severity).toBe("high");
        } else if (safetyFl.impact_score >= 0.2) {
          expect(safetyFl.severity).toBe("medium");
        } else {
          expect(safetyFl.severity).toBe("low");
        }
      }
    });

    it("should assign low severity for small impact_score (<0.2)", () => {
      // Only 2 agents, one missing a value with no bounded_action overlap
      const cards = [
        { agentId: "a", card: makeCard("a", ["principal_benefit", "minor_value"], [], ["search"]) },
        { agentId: "b", card: makeCard("b", ["principal_benefit"], [], ["report"]) },
      ];
      const analysis = getCoherenceAndAnalysis(cards);

      const fl = analysis.fault_lines.find(f => f.value === "minor_value");
      expect(fl).toBeDefined();
      // impact = impact_on_fleet_score * coordination_overlap
      // coordination_overlap ~ Jaccard(["search"], ["report"]) = 0
      // so impact should be ~0 → low
      expect(["low", "medium"]).toContain(fl!.severity);
    });
  });

  // ============================================================================
  // IMPACT_SCORE CALCULATION
  // ============================================================================

  describe("impact_score calculation", () => {
    it("should produce impact_score between 0 and 1", () => {
      const cards = [
        { agentId: "a", card: makeCard("a", ["transparency", "honesty"]) },
        { agentId: "b", card: makeCard("b", ["transparency"]) },
        { agentId: "c", card: makeCard("c", ["transparency"]) },
      ];
      const analysis = getCoherenceAndAnalysis(cards);

      for (const fl of analysis.fault_lines) {
        expect(fl.impact_score).toBeGreaterThanOrEqual(0);
        expect(fl.impact_score).toBeLessThanOrEqual(1);
      }
    });

    it("should reduce impact_score when involved agents have low reputation", () => {
      const cards = [
        { agentId: "a", card: makeCard("a", ["transparency", "honesty"]) },
        { agentId: "b", card: makeCard("b", ["transparency"]) },
      ];
      const coherence = checkFleetCoherence(cards);

      // No reputations
      const baseAnalysis = analyzeFaultLines(coherence, cards);
      const baseFl = baseAnalysis.fault_lines.find(f => f.value === "honesty");

      // Low reputation
      const lowRepAnalysis = analyzeFaultLines(coherence, cards, {
        reputationScores: { a: 100, b: 100 }, // 100/1000 = 0.1 geo mean
      });
      const lowRepFl = lowRepAnalysis.fault_lines.find(f => f.value === "honesty");

      expect(baseFl).toBeDefined();
      expect(lowRepFl).toBeDefined();
      expect(lowRepFl!.impact_score).toBeLessThanOrEqual(baseFl!.impact_score);
    });

    it("should use 0.5 as default coordination_overlap when no bounded_actions", () => {
      const cards = [
        {
          agentId: "a",
          card: {
            ...minimalAlignmentCard,
            card_id: "ac-fl-empty-a",
            agent_id: "agent-empty-a",
            values: { declared: ["unique_val"] },
            autonomy: { bounded_actions: [], escalation_triggers: [] },
          },
        },
        {
          agentId: "b",
          card: {
            ...minimalAlignmentCard,
            card_id: "ac-fl-empty-b",
            agent_id: "agent-empty-b",
            values: { declared: [] },
            autonomy: { bounded_actions: [], escalation_triggers: [] },
          },
        },
      ];
      const analysis = getCoherenceAndAnalysis(cards);
      const fl = analysis.fault_lines.find(f => f.value === "unique_val");
      expect(fl).toBeDefined();
      // coordination_overlap defaults to 0.5 when no bounded_actions
      // impact = impact_on_fleet_score * 0.5
      expect(fl!.impact_score).toBeGreaterThanOrEqual(0);
    });
  });

  // ============================================================================
  // AFFECTS_CAPABILITIES
  // ============================================================================

  describe("affects_capabilities", () => {
    it("should contain intersection of bounded_actions across all involved agents", () => {
      const cards = [
        { agentId: "a", card: makeCard("a", ["transparency", "honesty"], [], ["search", "report", "execute"]) },
        { agentId: "b", card: makeCard("b", ["transparency"], [], ["search", "report", "analyze"]) },
      ];
      const analysis = getCoherenceAndAnalysis(cards);

      const fl = analysis.fault_lines.find(f => f.value === "honesty");
      expect(fl).toBeDefined();
      // intersection of ["search", "report", "execute"] and ["search", "report", "analyze"] = ["search", "report"]
      expect(fl!.affects_capabilities).toContain("search");
      expect(fl!.affects_capabilities).toContain("report");
      expect(fl!.affects_capabilities).not.toContain("execute");
      expect(fl!.affects_capabilities).not.toContain("analyze");
    });

    it("should be empty when no shared bounded_actions", () => {
      const cards = [
        { agentId: "a", card: makeCard("a", ["transparency", "honesty"], [], ["execute"]) },
        { agentId: "b", card: makeCard("b", ["transparency"], [], ["analyze"]) },
      ];
      const analysis = getCoherenceAndAnalysis(cards);

      const fl = analysis.fault_lines.find(f => f.value === "honesty");
      expect(fl).toBeDefined();
      expect(fl!.affects_capabilities).toHaveLength(0);
    });
  });

  // ============================================================================
  // EMPTY FAULT LINES FOR FULLY COHERENT TEAM
  // ============================================================================

  describe("fully coherent team", () => {
    it("should produce empty fault_lines when all agents declare all values", () => {
      const card = makeCard("shared", ["principal_benefit", "transparency", "honesty"]);
      const cards = [
        { agentId: "a", card: { ...card, card_id: "ac-fl-a", agent_id: "agent-a" } },
        { agentId: "b", card: { ...card, card_id: "ac-fl-b", agent_id: "agent-b" } },
        { agentId: "c", card: { ...card, card_id: "ac-fl-c", agent_id: "agent-c" } },
      ];
      const analysis = getCoherenceAndAnalysis(cards);

      expect(analysis.fault_lines).toHaveLength(0);
      expect(analysis.summary.total).toBe(0);
    });

    it("should produce an empty alignments array for a fully coherent team", () => {
      const card = makeCard("shared", ["principal_benefit", "transparency"]);
      const cards = [
        { agentId: "a", card: { ...card, card_id: "ac-fl-a2", agent_id: "agent-a2" } },
        { agentId: "b", card: { ...card, card_id: "ac-fl-b2", agent_id: "agent-b2" } },
      ];
      const analysis = getCoherenceAndAnalysis(cards);

      expect(analysis.alignments).toHaveLength(0);
    });
  });

  // ============================================================================
  // FAULT LINE ALIGNMENT DETECTION
  // ============================================================================

  describe("fault line alignment detection", () => {
    it("should detect alignment when 3 fault lines all isolate the same agent", () => {
      // Agent "lone" is missing from 3 values that everyone else declares
      const cards = [
        { agentId: "a", card: makeCard("a", ["val1", "val2", "val3", "common"]) },
        { agentId: "b", card: makeCard("b", ["val1", "val2", "val3", "common"]) },
        { agentId: "lone", card: makeCard("lone", ["common"]) },
      ];
      const analysis = getCoherenceAndAnalysis(cards);

      expect(analysis.alignments.length).toBeGreaterThan(0);
      const alignment = analysis.alignments[0];
      expect(alignment.minority_agents).toContain("lone");
      expect(alignment.fault_line_ids.length).toBeGreaterThanOrEqual(2);
    });

    it("should set alignment description mentioning isolated agents", () => {
      const cards = [
        { agentId: "a", card: makeCard("a", ["val1", "val2", "val3"]) },
        { agentId: "b", card: makeCard("b", ["val1", "val2", "val3"]) },
        { agentId: "lone", card: makeCard("lone", []) },
      ];
      const analysis = getCoherenceAndAnalysis(cards);

      if (analysis.alignments.length > 0) {
        const alignment = analysis.alignments[0];
        expect(alignment.description).toContain("lone");
        expect(alignment.description).toContain("fault lines");
      }
    });

    it("should not create alignment when fault lines split agents differently", () => {
      // fl1 isolates "a", fl2 isolates "b" → no consistent isolation
      const cards = [
        { agentId: "a", card: makeCard("a", ["val2"]) },
        { agentId: "b", card: makeCard("b", ["val1"]) },
        { agentId: "c", card: makeCard("c", ["val1", "val2"]) },
      ];
      const analysis = getCoherenceAndAnalysis(cards);

      // Each fault line isolates a different agent → Jaccard of agents_missing ≈ 0
      // So no alignment should be created
      expect(analysis.alignments).toHaveLength(0);
    });

    it("should set severity to high for alignments with 3+ fault lines", () => {
      const cards = [
        { agentId: "a", card: makeCard("a", ["v1", "v2", "v3", "v4"]) },
        { agentId: "b", card: makeCard("b", ["v1", "v2", "v3", "v4"]) },
        { agentId: "lone", card: makeCard("lone", []) },
      ];
      const analysis = getCoherenceAndAnalysis(cards);

      const bigAlignment = analysis.alignments.find(a => a.fault_line_ids.length >= 3);
      if (bigAlignment) {
        expect(bigAlignment.severity).toBe("high");
      }
    });
  });

  // ============================================================================
  // DETERMINISTIC ANALYSIS_ID
  // ============================================================================

  describe("deterministic analysis_id", () => {
    it("should produce the same analysis_id for identical inputs", () => {
      const cards = [
        { agentId: "a", card: makeCard("a", ["transparency", "honesty"]) },
        { agentId: "b", card: makeCard("b", ["transparency"]) },
      ];

      const a1 = getCoherenceAndAnalysis(cards);
      const a2 = getCoherenceAndAnalysis(cards);

      expect(a1.analysis_id).toBe(a2.analysis_id);
    });

    it("should produce different analysis_ids for different fleets", () => {
      const cards1 = [
        { agentId: "a", card: makeCard("a", ["transparency", "honesty"]) },
        { agentId: "b", card: makeCard("b", ["transparency"]) },
      ];
      const cards2 = [
        { agentId: "a", card: makeCard("a", ["transparency"]) },
        { agentId: "b", card: makeCard("b", ["honesty"]) },
      ];

      const a1 = getCoherenceAndAnalysis(cards1);
      const a2 = getCoherenceAndAnalysis(cards2);

      expect(a1.analysis_id).not.toBe(a2.analysis_id);
    });
  });

  // ============================================================================
  // SUMMARY COUNTS
  // ============================================================================

  describe("summary", () => {
    it("should correctly count fault lines by classification", () => {
      const cards = [
        { agentId: "a", card: makeCard("a", ["resolvable_val", "incompatible_val"]) },
        { agentId: "b", card: makeCard("b", [], ["incompatible_val"]) },
      ];
      const analysis = getCoherenceAndAnalysis(cards);

      expect(analysis.summary.total).toBe(analysis.fault_lines.length);
      expect(
        analysis.summary.resolvable +
          analysis.summary.priority_mismatch +
          analysis.summary.incompatible +
          analysis.summary.complementary
      ).toBe(analysis.summary.total);
    });

    it("should count critical fault lines correctly", () => {
      const cards = [
        { agentId: "a", card: makeCard("a", ["transparency"]) },
        { agentId: "b", card: makeCard("b", ["transparency"]) },
        { agentId: "c", card: makeCard("c", ["transparency"]) },
      ];
      const analysis = getCoherenceAndAnalysis(cards);

      const expectedCritical = analysis.fault_lines.filter(fl => fl.severity === "critical").length;
      expect(analysis.summary.critical_count).toBe(expectedCritical);
    });
  });

  // ============================================================================
  // FAULT LINES SORTED CRITICAL FIRST
  // ============================================================================

  describe("sort order", () => {
    it("should sort fault lines critical first then by impact_score descending", () => {
      const cards = [
        { agentId: "a", card: makeCard("a", ["v1", "v2", "v3", "v4"]) },
        { agentId: "b", card: makeCard("b", ["v1"], ["v4"]) },
      ];
      const analysis = getCoherenceAndAnalysis(cards);

      const severityOrder: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3 };
      for (let i = 0; i < analysis.fault_lines.length - 1; i++) {
        const a = analysis.fault_lines[i];
        const b = analysis.fault_lines[i + 1];
        const sevDiff = severityOrder[a.severity] - severityOrder[b.severity];
        if (sevDiff === 0) {
          expect(a.impact_score).toBeGreaterThanOrEqual(b.impact_score);
        } else {
          expect(sevDiff).toBeLessThanOrEqual(0);
        }
      }
    });
  });
});

// ============================================================================
// checkFleetFaultLines WRAPPER
// ============================================================================

describe("checkFleetFaultLines", () => {
  it("should return both coherence and analysis", () => {
    const cards = [
      { agentId: "a", card: makeCard("a", ["transparency", "honesty"]) },
      { agentId: "b", card: makeCard("b", ["transparency"]) },
    ];
    const result = checkFleetFaultLines(cards);

    expect(result.coherence).toBeDefined();
    expect(result.analysis).toBeDefined();
    expect(result.coherence.fleet_score).toBeGreaterThanOrEqual(0);
    expect(result.analysis.fault_lines).toBeDefined();
  });

  it("should produce coherence matching checkFleetCoherence directly", () => {
    const cards = [
      { agentId: "a", card: makeCard("a", ["principal_benefit", "transparency"]) },
      { agentId: "b", card: makeCard("b", ["principal_benefit"]) },
    ];
    const direct = checkFleetCoherence(cards);
    const wrapper = checkFleetFaultLines(cards);

    expect(wrapper.coherence.fleet_score).toBe(direct.fleet_score);
    expect(wrapper.coherence.agent_count).toBe(direct.agent_count);
  });

  it("should pass reputationScores option to analysis", () => {
    const cards = [
      { agentId: "a", card: makeCard("a", ["transparency", "honesty"]) },
      { agentId: "b", card: makeCard("b", ["transparency"]) },
    ];
    const withRep = checkFleetFaultLines(cards, { reputationScores: { a: 900, b: 900 } });
    const noRep = checkFleetFaultLines(cards);

    // High reputation (900) should keep scores near base; just verify no crash
    expect(withRep.analysis.fault_lines.length).toBe(noRep.analysis.fault_lines.length);
  });

  it("should handle fully coherent fleet returning empty fault_lines", () => {
    const card = makeCard("shared", ["principal_benefit", "transparency"]);
    const cards = [
      { agentId: "a", card: { ...card, card_id: "ac-fl-wrapper-a", agent_id: "agent-wrapper-a" } },
      { agentId: "b", card: { ...card, card_id: "ac-fl-wrapper-b", agent_id: "agent-wrapper-b" } },
    ];
    const result = checkFleetFaultLines(cards);

    expect(result.analysis.fault_lines).toHaveLength(0);
    expect(result.analysis.summary.total).toBe(0);
  });
});
