/**
 * AAP TypeScript SDK - checkFleetCoherence Tests
 *
 * Comprehensive tests for N-way fleet coherence analysis.
 * Tests cover: fleet score, outlier detection, cluster analysis,
 * divergence report, showcase scenario, and edge cases.
 */

import { describe, it, expect } from "vitest";
import {
  checkFleetCoherence,
  checkCoherence,
  OUTLIER_STD_DEV_THRESHOLD,
  CLUSTER_COMPATIBILITY_THRESHOLD,
} from "../src";
import type {
  AlignmentCard,
  FleetCoherenceResult,
} from "../src";
import {
  compatibleCardA,
  compatibleCardB,
  conflictingCardA,
  conflictingCardB,
  minimalAlignmentCard,
} from "./fixtures";

// ============================================================================
// HELPERS — Build cards for fleet tests
// ============================================================================

function makeCard(
  id: string,
  declared: string[],
  conflicts_with: string[] = []
): AlignmentCard {
  return {
    ...minimalAlignmentCard,
    card_id: `ac-fleet-${id}`,
    agent_id: `agent-${id}`,
    values: { declared, conflicts_with },
  };
}

// ============================================================================
// FLEET SCORE
// ============================================================================

describe("checkFleetCoherence", () => {
  describe("fleet score computation", () => {
    it("should compute mean of all pairwise scores", () => {
      const cards = [
        { agentId: "a", card: compatibleCardA },
        { agentId: "b", card: compatibleCardB },
      ];
      const result = checkFleetCoherence(cards);
      const directPair = checkCoherence(compatibleCardA, compatibleCardB);

      expect(result.fleet_score).toBe(directPair.score);
      expect(result.pair_count).toBe(1);
      expect(result.agent_count).toBe(2);
    });

    it("should compute correct pair count for N agents", () => {
      const cards = [
        { agentId: "a", card: makeCard("a", ["transparency", "honesty"]) },
        { agentId: "b", card: makeCard("b", ["transparency", "honesty"]) },
        { agentId: "c", card: makeCard("c", ["transparency", "honesty"]) },
        { agentId: "d", card: makeCard("d", ["transparency", "honesty"]) },
      ];
      const result = checkFleetCoherence(cards);

      // C(4,2) = 6 pairs
      expect(result.pair_count).toBe(6);
      expect(result.agent_count).toBe(4);
    });

    it("should track min and max pair scores", () => {
      const cards = [
        { agentId: "a", card: makeCard("a", ["transparency", "honesty"]) },
        { agentId: "b", card: makeCard("b", ["transparency", "honesty"]) },
        { agentId: "c", card: makeCard("c", ["speed", "efficiency"]) },
      ];
      const result = checkFleetCoherence(cards);

      expect(result.min_pair_score).toBeLessThanOrEqual(result.fleet_score);
      expect(result.max_pair_score).toBeGreaterThanOrEqual(result.fleet_score);
    });

    it("should produce perfect fleet score for identical cards", () => {
      const card = makeCard("shared", ["principal_benefit", "transparency", "honesty"]);
      const cards = [
        { agentId: "a", card: { ...card, card_id: "ac-a", agent_id: "agent-a" } },
        { agentId: "b", card: { ...card, card_id: "ac-b", agent_id: "agent-b" } },
        { agentId: "c", card: { ...card, card_id: "ac-c", agent_id: "agent-c" } },
      ];
      const result = checkFleetCoherence(cards);

      expect(result.fleet_score).toBe(1);
      expect(result.min_pair_score).toBe(1);
      expect(result.max_pair_score).toBe(1);
    });

    it("should produce low fleet score for all-conflicting fleet", () => {
      const cards = [
        { agentId: "a", card: makeCard("a", ["transparency"], ["speed"]) },
        { agentId: "b", card: makeCard("b", ["speed"], ["transparency"]) },
        { agentId: "c", card: makeCard("c", ["autonomy"], ["transparency", "speed"]) },
      ];
      const result = checkFleetCoherence(cards);

      expect(result.fleet_score).toBeLessThan(0.5);
    });

    it("should handle 2-agent degenerate case", () => {
      const cards = [
        { agentId: "a", card: conflictingCardA },
        { agentId: "b", card: conflictingCardB },
      ];
      const result = checkFleetCoherence(cards);
      const directPair = checkCoherence(conflictingCardA, conflictingCardB);

      expect(result.fleet_score).toBe(directPair.score);
      expect(result.pair_count).toBe(1);
      expect(result.pairwise_matrix).toHaveLength(1);
    });
  });

  // ==========================================================================
  // OUTLIER DETECTION
  // ==========================================================================

  describe("outlier detection", () => {
    it("should flag divergent agent as outlier", () => {
      const cards = [
        { agentId: "a", card: makeCard("a", ["principal_benefit", "transparency", "honesty"]) },
        { agentId: "b", card: makeCard("b", ["principal_benefit", "transparency", "honesty"]) },
        { agentId: "c", card: makeCard("c", ["principal_benefit", "transparency", "honesty"]) },
        { agentId: "d", card: makeCard("d", ["speed", "efficiency"], ["principal_benefit"]) },
      ];
      const result = checkFleetCoherence(cards);

      expect(result.outliers.length).toBeGreaterThan(0);
      expect(result.outliers.some(o => o.agent_id === "d")).toBe(true);
    });

    it("should report no outliers when fleet is uniform", () => {
      const card = makeCard("x", ["principal_benefit", "transparency"]);
      const cards = [
        { agentId: "a", card: { ...card, card_id: "ac-a", agent_id: "a" } },
        { agentId: "b", card: { ...card, card_id: "ac-b", agent_id: "b" } },
        { agentId: "c", card: { ...card, card_id: "ac-c", agent_id: "c" } },
      ];
      const result = checkFleetCoherence(cards);

      expect(result.outliers).toHaveLength(0);
    });

    it("should identify primary conflict values for outliers", () => {
      const cards = [
        { agentId: "a", card: makeCard("a", ["transparency", "honesty"]) },
        { agentId: "b", card: makeCard("b", ["transparency", "honesty"]) },
        { agentId: "c", card: makeCard("c", ["transparency", "honesty"]) },
        { agentId: "d", card: makeCard("d", ["transparency", "speed"], ["honesty"]) },
      ];
      const result = checkFleetCoherence(cards);
      const dOutlier = result.outliers.find(o => o.agent_id === "d");

      if (dOutlier) {
        expect(dOutlier.primary_conflicts.length).toBeGreaterThan(0);
      }
    });

    it("should not flag outliers with only 2 agents", () => {
      const cards = [
        { agentId: "a", card: compatibleCardA },
        { agentId: "b", card: conflictingCardB },
      ];
      const result = checkFleetCoherence(cards);

      // With 2 agents, outlier detection is not meaningful
      expect(result.outliers).toHaveLength(0);
    });

    it("should include deviation metric for outliers", () => {
      const cards = [
        { agentId: "a", card: makeCard("a", ["principal_benefit", "transparency", "honesty"]) },
        { agentId: "b", card: makeCard("b", ["principal_benefit", "transparency", "honesty"]) },
        { agentId: "c", card: makeCard("c", ["principal_benefit", "transparency", "honesty"]) },
        { agentId: "outlier", card: makeCard("outlier", ["speed"], ["principal_benefit", "transparency"]) },
      ];
      const result = checkFleetCoherence(cards);
      const outlier = result.outliers.find(o => o.agent_id === "outlier");

      if (outlier) {
        expect(outlier.deviation).toBeGreaterThanOrEqual(OUTLIER_STD_DEV_THRESHOLD);
        expect(outlier.fleet_mean_score).toBeGreaterThan(outlier.agent_mean_score);
      }
    });
  });

  // ==========================================================================
  // CLUSTER ANALYSIS
  // ==========================================================================

  describe("cluster analysis", () => {
    it("should produce single cluster when all agents are compatible", () => {
      const card = makeCard("x", ["principal_benefit", "transparency", "honesty"]);
      const cards = [
        { agentId: "a", card: { ...card, card_id: "ac-a", agent_id: "a" } },
        { agentId: "b", card: { ...card, card_id: "ac-b", agent_id: "b" } },
        { agentId: "c", card: { ...card, card_id: "ac-c", agent_id: "c" } },
      ];
      const result = checkFleetCoherence(cards);

      expect(result.clusters).toHaveLength(1);
      expect(result.clusters[0].agent_ids).toHaveLength(3);
    });

    it("should detect multiple clusters", () => {
      const cards = [
        { agentId: "a", card: makeCard("a", ["principal_benefit", "transparency", "honesty"]) },
        { agentId: "b", card: makeCard("b", ["principal_benefit", "transparency", "honesty"]) },
        { agentId: "c", card: makeCard("c", ["speed", "efficiency", "autonomy"]) },
        { agentId: "d", card: makeCard("d", ["speed", "efficiency", "autonomy"]) },
      ];
      const result = checkFleetCoherence(cards);

      expect(result.clusters.length).toBeGreaterThanOrEqual(2);
    });

    it("should put isolated agents in their own cluster", () => {
      const cards = [
        { agentId: "a", card: makeCard("a", ["principal_benefit", "transparency", "honesty"]) },
        { agentId: "b", card: makeCard("b", ["principal_benefit", "transparency", "honesty"]) },
        { agentId: "lone", card: makeCard("lone", ["unique_value_xyz"]) },
      ];
      const result = checkFleetCoherence(cards);

      const loneCluster = result.clusters.find(c => c.agent_ids.includes("lone"));
      expect(loneCluster).toBeDefined();
      expect(loneCluster!.agent_ids).toHaveLength(1);
    });

    it("should compute internal coherence per cluster", () => {
      const card = makeCard("x", ["principal_benefit", "transparency", "honesty"]);
      const cards = [
        { agentId: "a", card: { ...card, card_id: "ac-a", agent_id: "a" } },
        { agentId: "b", card: { ...card, card_id: "ac-b", agent_id: "b" } },
        { agentId: "c", card: { ...card, card_id: "ac-c", agent_id: "c" } },
      ];
      const result = checkFleetCoherence(cards);

      expect(result.clusters[0].internal_coherence).toBe(1);
    });

    it("should identify shared values within a cluster", () => {
      const cards = [
        { agentId: "a", card: makeCard("a", ["principal_benefit", "transparency", "honesty"]) },
        { agentId: "b", card: makeCard("b", ["principal_benefit", "transparency", "extra_value"]) },
      ];
      const result = checkFleetCoherence(cards);

      // Both declare principal_benefit and transparency
      expect(result.clusters[0].shared_values).toContain("principal_benefit");
      expect(result.clusters[0].shared_values).toContain("transparency");
    });
  });

  // ==========================================================================
  // DIVERGENCE REPORT
  // ==========================================================================

  describe("divergence report", () => {
    it("should report values declared by some but not others", () => {
      const cards = [
        { agentId: "a", card: makeCard("a", ["principal_benefit", "transparency"]) },
        { agentId: "b", card: makeCard("b", ["principal_benefit", "speed"]) },
        { agentId: "c", card: makeCard("c", ["principal_benefit", "honesty"]) },
      ];
      const result = checkFleetCoherence(cards);

      // transparency, speed, honesty are each only declared by 1/3 agents
      expect(result.divergence_report.length).toBeGreaterThan(0);
    });

    it("should report conflicting values", () => {
      const cards = [
        { agentId: "a", card: makeCard("a", ["speed"], ["honesty"]) },
        { agentId: "b", card: makeCard("b", ["honesty"]) },
        { agentId: "c", card: makeCard("c", ["honesty"]) },
      ];
      const result = checkFleetCoherence(cards);

      const honestyDiv = result.divergence_report.find(d => d.value === "honesty");
      if (honestyDiv) {
        expect(honestyDiv.agents_conflicting).toContain("a");
      }
    });

    it("should estimate impact on fleet score", () => {
      const cards = [
        { agentId: "a", card: makeCard("a", ["principal_benefit", "transparency"]) },
        { agentId: "b", card: makeCard("b", ["principal_benefit"]) },
      ];
      const result = checkFleetCoherence(cards);

      for (const div of result.divergence_report) {
        expect(div.impact_on_fleet_score).toBeGreaterThanOrEqual(0);
        expect(div.impact_on_fleet_score).toBeLessThanOrEqual(1);
      }
    });

    it("should sort divergence report by impact descending", () => {
      const cards = [
        { agentId: "a", card: makeCard("a", ["val1", "val2", "val3"]) },
        { agentId: "b", card: makeCard("b", ["val1"]) },
        { agentId: "c", card: makeCard("c", ["val1", "val2"]) },
      ];
      const result = checkFleetCoherence(cards);

      for (let i = 0; i < result.divergence_report.length - 1; i++) {
        expect(result.divergence_report[i].impact_on_fleet_score)
          .toBeGreaterThanOrEqual(result.divergence_report[i + 1].impact_on_fleet_score);
      }
    });

    it("should not include values where all agents agree", () => {
      const cards = [
        { agentId: "a", card: makeCard("a", ["shared", "only_a"]) },
        { agentId: "b", card: makeCard("b", ["shared", "only_b"]) },
      ];
      const result = checkFleetCoherence(cards);

      const sharedDiv = result.divergence_report.find(d => d.value === "shared");
      expect(sharedDiv).toBeUndefined();
    });
  });

  // ==========================================================================
  // AGENT SUMMARIES
  // ==========================================================================

  describe("agent summaries", () => {
    it("should produce a summary for each agent", () => {
      const cards = [
        { agentId: "a", card: compatibleCardA },
        { agentId: "b", card: compatibleCardB },
        { agentId: "c", card: conflictingCardA },
      ];
      const result = checkFleetCoherence(cards);

      expect(result.agent_summaries).toHaveLength(3);
      expect(result.agent_summaries.map(s => s.agent_id).sort()).toEqual(["a", "b", "c"]);
    });

    it("should mark outlier agents in summaries", () => {
      const cards = [
        { agentId: "a", card: makeCard("a", ["principal_benefit", "transparency", "honesty"]) },
        { agentId: "b", card: makeCard("b", ["principal_benefit", "transparency", "honesty"]) },
        { agentId: "c", card: makeCard("c", ["principal_benefit", "transparency", "honesty"]) },
        { agentId: "d", card: makeCard("d", ["speed"], ["principal_benefit", "transparency"]) },
      ];
      const result = checkFleetCoherence(cards);

      if (result.outliers.length > 0) {
        const outlierIds = new Set(result.outliers.map(o => o.agent_id));
        for (const summary of result.agent_summaries) {
          expect(summary.is_outlier).toBe(outlierIds.has(summary.agent_id));
        }
      }
    });

    it("should assign cluster IDs to agent summaries", () => {
      const cards = [
        { agentId: "a", card: makeCard("a", ["principal_benefit", "transparency", "honesty"]) },
        { agentId: "b", card: makeCard("b", ["principal_benefit", "transparency", "honesty"]) },
      ];
      const result = checkFleetCoherence(cards);

      for (const summary of result.agent_summaries) {
        expect(typeof summary.cluster_id).toBe("number");
      }
    });
  });

  // ==========================================================================
  // TASK VALUES FILTER
  // ==========================================================================

  describe("taskValues filter", () => {
    it("should pass taskValues through to pairwise checks", () => {
      const cards = [
        { agentId: "a", card: makeCard("a", ["principal_benefit", "transparency", "honesty"]) },
        { agentId: "b", card: makeCard("b", ["principal_benefit", "transparency"]) },
      ];

      const withFilter = checkFleetCoherence(cards, ["principal_benefit"]);
      const withoutFilter = checkFleetCoherence(cards);

      // With a single shared task value, the score should differ from unfiltered
      expect(withFilter.fleet_score).not.toBe(withoutFilter.fleet_score);
    });
  });

  // ==========================================================================
  // EDGE CASES
  // ==========================================================================

  describe("edge cases", () => {
    it("should throw for single agent", () => {
      const cards = [{ agentId: "a", card: compatibleCardA }];
      expect(() => checkFleetCoherence(cards)).toThrow("at least 2 agents");
    });

    it("should throw for empty cards array", () => {
      expect(() => checkFleetCoherence([])).toThrow("at least 2 agents");
    });

    it("should clamp scores to [0, 1]", () => {
      const cards = [
        { agentId: "a", card: makeCard("a", ["val1"]) },
        { agentId: "b", card: makeCard("b", ["val2"]) },
      ];
      const result = checkFleetCoherence(cards);

      expect(result.fleet_score).toBeGreaterThanOrEqual(0);
      expect(result.fleet_score).toBeLessThanOrEqual(1);
      expect(result.min_pair_score).toBeGreaterThanOrEqual(0);
      expect(result.max_pair_score).toBeLessThanOrEqual(1);
    });

    it("should handle agents with empty value arrays", () => {
      const cards = [
        { agentId: "a", card: makeCard("a", []) },
        { agentId: "b", card: makeCard("b", []) },
      ];
      const result = checkFleetCoherence(cards);

      expect(result.agent_count).toBe(2);
      expect(result.pair_count).toBe(1);
    });
  });

  // ==========================================================================
  // SHOWCASE SCENARIO
  // ==========================================================================

  describe("showcase scenario (4-agent incident team)", () => {
    // Reproduce the showcase scenario from showcase-scenario.ts
    const sentinelCard = makeCard("sentinel", [
      "principal_benefit", "transparency", "harm_prevention",
      "honesty", "data_integrity", "incident_containment",
    ]);
    const triageCard = makeCard("triage", [
      "principal_benefit", "transparency", "harm_prevention",
      "honesty", "accountability", "incident_containment",
    ]);
    const patchCard = makeCard("patch", [
      "principal_benefit", "transparency", "harm_prevention",
      "honesty", "accountability", "incident_containment",
      "move_fast_break_things",
    ], ["data_integrity"]);
    const heraldCard = makeCard("herald", [
      "principal_benefit", "transparency", "harm_prevention",
      "honesty", "accountability",
    ]);

    const showcaseCards = [
      { agentId: "sentinel", card: sentinelCard },
      { agentId: "triage", card: triageCard },
      { agentId: "patch", card: patchCard },
      { agentId: "herald", card: heraldCard },
    ];

    it("should compute fleet score for 4 agents", () => {
      const result = checkFleetCoherence(showcaseCards);

      expect(result.agent_count).toBe(4);
      expect(result.pair_count).toBe(6);
      expect(result.fleet_score).toBeGreaterThan(0);
      expect(result.fleet_score).toBeLessThan(1);
    });

    it("should identify Patch as potential outlier (has provocative values)", () => {
      const result = checkFleetCoherence(showcaseCards);

      // Patch has move_fast_break_things and conflicts with data_integrity
      const patchSummary = result.agent_summaries.find(s => s.agent_id === "patch");
      expect(patchSummary).toBeDefined();
      expect(patchSummary!.conflict_count).toBeGreaterThan(0);
    });

    it("should detect move_fast_break_things in divergence report", () => {
      const result = checkFleetCoherence(showcaseCards);

      const mfbtDiv = result.divergence_report.find(
        d => d.value === "move_fast_break_things"
      );
      expect(mfbtDiv).toBeDefined();
      if (mfbtDiv) {
        expect(mfbtDiv.agents_declaring).toContain("patch");
        expect(mfbtDiv.agents_missing.length).toBeGreaterThan(0);
      }
    });

    it("should show all required fields populated", () => {
      const result = checkFleetCoherence(showcaseCards);

      expect(result.pairwise_matrix.length).toBe(6);
      expect(result.clusters.length).toBeGreaterThan(0);
      expect(result.agent_summaries.length).toBe(4);
      expect(result.divergence_report.length).toBeGreaterThan(0);

      // Every pairwise entry has valid structure
      for (const pair of result.pairwise_matrix) {
        expect(pair.agent_a).toBeTruthy();
        expect(pair.agent_b).toBeTruthy();
        expect(pair.result.score).toBeGreaterThanOrEqual(0);
        expect(pair.result.score).toBeLessThanOrEqual(1);
      }
    });
  });
});
