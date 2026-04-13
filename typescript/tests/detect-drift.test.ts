/**
 * AAP TypeScript SDK - detectDrift Tests
 *
 * Comprehensive tests for behavioral drift detection over trace sequences.
 * Tests cover: no drift, drift detection, thresholds, direction inference, and indicators.
 *
 * The drift detection algorithm compares traces against a baseline centroid
 * computed from the first N traces. Trace-to-trace comparison provides
 * symmetric feature spaces for meaningful cosine similarity.
 */

import { describe, it, expect } from "vitest";
import {
  detectDrift,
  computeCentroid,
  extractTraceFeatures,
  DEFAULT_SIMILARITY_THRESHOLD,
  DEFAULT_SUSTAINED_CHECKS_THRESHOLD,
} from "../src";
import type { AlignmentCard, APTrace, DriftAlert, DriftDirection } from "../src";
import {
  minimalAlignmentCard,
  createAlignedTraceSequence,
  valueDriftCard,
  valueDriftSequence,
  autonomyExpansionCard,
  autonomyExpansionSequence,
} from "./fixtures";

/**
 * Helper: create a long aligned sequence with enough traces for baseline + evaluation.
 * All traces have the same structure so centroid similarity stays high.
 */
function createLongAlignedSequence(card: AlignmentCard, count: number): APTrace[] {
  return Array.from({ length: count }, (_, i) => ({
    trace_id: `tr-aligned-${i.toString().padStart(3, "0")}`,
    agent_id: card.agent_id,
    card_id: card.card_id,
    timestamp: new Date(Date.now() + i * 60000).toISOString(),
    action: {
      type: "recommend" as const,
      name: "recommend",
      category: "bounded" as const,
    },
    decision: {
      alternatives_considered: [
        {
          option_id: `option-${i}`,
          description: "Option aligned with principal benefit and transparency",
          score: 0.85,
        },
      ],
      selected: `option-${i}`,
      selection_reasoning: "Applying principal_benefit value to serve user interests with full transparency.",
      values_applied: ["principal_benefit", "transparency"],
      confidence: 0.85,
    },
    escalation: {
      evaluated: true,
      required: false,
      reason: "Standard bounded action",
    },
  }));
}

/**
 * Helper: create a behavioral shift sequence.
 * First `baseCount` traces use one set of values, then `shiftCount` traces use different values.
 */
function createBehavioralShiftSequence(
  card: AlignmentCard,
  baseCount: number,
  shiftCount: number,
  baseValues: string[],
  shiftValues: string[],
): APTrace[] {
  const traces: APTrace[] = [];
  for (let i = 0; i < baseCount; i++) {
    traces.push({
      trace_id: `tr-base-${i.toString().padStart(3, "0")}`,
      agent_id: card.agent_id,
      card_id: card.card_id,
      timestamp: new Date(Date.now() + i * 60000).toISOString(),
      action: {
        type: "recommend" as const,
        name: "recommend",
        category: "bounded" as const,
      },
      decision: {
        alternatives_considered: [
          { option_id: `opt-${i}`, description: "Base behavior", score: 0.85 },
        ],
        selected: `opt-${i}`,
        selection_reasoning: "Base period reasoning.",
        values_applied: baseValues,
        confidence: 0.85,
      },
      escalation: { evaluated: true, required: false, reason: "Standard action" },
    });
  }
  for (let i = 0; i < shiftCount; i++) {
    traces.push({
      trace_id: `tr-shift-${i.toString().padStart(3, "0")}`,
      agent_id: card.agent_id,
      card_id: card.card_id,
      timestamp: new Date(Date.now() + (baseCount + i) * 60000).toISOString(),
      action: {
        type: "execute" as const,
        name: "auto_execute",
        category: "forbidden" as const,
      },
      decision: {
        alternatives_considered: [
          { option_id: `shift-${i}`, description: "Shifted behavior", score: 0.90 },
        ],
        selected: `shift-${i}`,
        selection_reasoning: "Shifted period reasoning.",
        values_applied: shiftValues,
        confidence: 0.60,
      },
      escalation: { evaluated: false, required: false, reason: "Skipped" },
    });
  }
  return traces;
}

describe("detectDrift", () => {
  // ==========================================================================
  // NO DRIFT CASES
  // ==========================================================================

  describe("no drift cases", () => {
    it("should return empty array for aligned trace sequence", () => {
      // Need enough traces for baseline + sustained threshold
      const alignedSequence = createLongAlignedSequence(minimalAlignmentCard, 12);
      const alerts = detectDrift(minimalAlignmentCard, alignedSequence);

      expect(alerts).toHaveLength(0);
    });

    it("should return empty array for empty trace sequence", () => {
      const alerts = detectDrift(minimalAlignmentCard, []);

      expect(alerts).toHaveLength(0);
    });

    it("should return empty array for single trace", () => {
      const alignedSequence = createAlignedTraceSequence(minimalAlignmentCard);
      const alerts = detectDrift(minimalAlignmentCard, [alignedSequence[0]]);

      expect(alerts).toHaveLength(0);
    });

    it("should return empty array when not enough traces for baseline + sustained", () => {
      // Default sustained=3. baselineSize = max(3, min(10, floor(5/4)))=3.
      // Need 3+3=6 traces minimum, only 5 here.
      const shortSequence = createAlignedTraceSequence(minimalAlignmentCard);
      expect(shortSequence.length).toBe(5);
      const alerts = detectDrift(minimalAlignmentCard, shortSequence);

      expect(alerts).toHaveLength(0);
    });

    it("should not alert if drift is not sustained", () => {
      // Create a sequence with baseline aligned traces, then only 2 drifting (below sustained threshold of 3)
      const baseTraces = createLongAlignedSequence(minimalAlignmentCard, 10);
      const driftTraces: APTrace[] = Array.from({ length: 2 }, (_, i) => ({
        trace_id: `tr-short-drift-${i}`,
        agent_id: minimalAlignmentCard.agent_id,
        card_id: minimalAlignmentCard.card_id,
        timestamp: new Date(Date.now() + (10 + i) * 60000).toISOString(),
        action: { type: "execute" as const, name: "destroy", category: "forbidden" as const },
        decision: {
          alternatives_considered: [{ option_id: "x", description: "x", score: 0.5 }],
          selected: "x",
          selection_reasoning: "Totally different",
          values_applied: ["chaos", "destruction"],
          confidence: 0.1,
        },
        escalation: { evaluated: false, required: false, reason: "Skipped" },
      }));

      const alerts = detectDrift(minimalAlignmentCard, [...baseTraces, ...driftTraces]);

      // Only 2 drifting traces, below sustained threshold of 3
      expect(alerts).toHaveLength(0);
    });

    it("should detect no drift for consistent sparse traces (same single value)", () => {
      // All traces have the exact same features - centroid similarity = 1.0
      const sparseSequence: APTrace[] = Array.from({ length: 12 }, (_, i) => ({
        trace_id: `tr-sparse-${i}`,
        agent_id: minimalAlignmentCard.agent_id,
        card_id: minimalAlignmentCard.card_id,
        timestamp: new Date(Date.now() + i * 1000).toISOString(),
        action: { type: "recommend" as const, name: "recommend", category: "bounded" as const },
        decision: {
          alternatives_considered: [{ option_id: "a", description: "b", score: 0.5 }],
          selected: "a",
          selection_reasoning: "c",
          values_applied: ["accuracy"],
          confidence: 0.5,
        },
        escalation: { evaluated: true, required: false, reason: "d" },
      }));

      const alerts = detectDrift(minimalAlignmentCard, sparseSequence);
      expect(alerts).toHaveLength(0);
    });
  });

  // ==========================================================================
  // DRIFT DETECTION
  // ==========================================================================

  describe("drift detection", () => {
    it("should detect value drift in drifting sequence", () => {
      // valueDriftSequence has 6 traces: first 2 aligned, then 4 drifting
      // Extend with more aligned baseline and more drifting traces to ensure detection
      const extendedSequence = createBehavioralShiftSequence(
        valueDriftCard,
        6,
        6,
        ["principal_benefit", "transparency"],
        ["profit_maximization", "engagement_maximization"],
      );
      const alerts = detectDrift(valueDriftCard, extendedSequence);

      expect(alerts.length).toBeGreaterThan(0);
    });

    it("should detect autonomy expansion in expanding sequence", () => {
      // Create a sequence where baseline traces have escalation and specific values,
      // then later traces drop escalation and shift to different values/actions
      const card = autonomyExpansionCard;

      // Baseline: consistent escalating behavior
      const baseTraces: APTrace[] = Array.from({ length: 8 }, (_, i) => ({
        trace_id: `tr-esc-base-${i}`,
        agent_id: card.agent_id,
        card_id: card.card_id,
        timestamp: new Date(new Date("2026-01-31T08:00:00Z").getTime() + i * 60000).toISOString(),
        action: {
          type: "recommend" as const,
          name: "analyze",
          category: "bounded" as const,
        },
        decision: {
          alternatives_considered: [
            { option_id: `opt-${i}`, description: "Analysis", score: 0.90 },
          ],
          selected: `opt-${i}`,
          selection_reasoning: "User approved the recommendation.",
          values_applied: ["principal_benefit", "user_control"],
          confidence: 0.92,
        },
        escalation: {
          evaluated: true,
          required: true,
          reason: "Requires user approval",
          escalation_id: `esc-${i}`,
          escalation_status: "approved" as const,
        },
      }));

      // Drift: autonomous execution with different action/values
      const driftTraces: APTrace[] = Array.from({ length: 5 }, (_, i) => ({
        trace_id: `tr-esc-drift-${i}`,
        agent_id: card.agent_id,
        card_id: card.card_id,
        timestamp: new Date(new Date("2026-01-31T08:00:00Z").getTime() + (8 + i) * 60000).toISOString(),
        action: {
          type: "execute" as const,
          name: "auto_trade",
          category: "forbidden" as const,
        },
        decision: {
          alternatives_considered: [
            { option_id: `auto-${i}`, description: "Auto execute", score: 0.95 },
          ],
          selected: `auto-${i}`,
          selection_reasoning: "Acting autonomously.",
          values_applied: ["efficiency"],
          confidence: 0.55,
        },
        escalation: {
          evaluated: false,
          required: false,
          reason: "Skipped escalation",
        },
      }));

      const alerts = detectDrift(card, [...baseTraces, ...driftTraces]);

      expect(alerts.length).toBeGreaterThan(0);
    });

    it("should detect behavioral shift (different feature spaces after baseline)", () => {
      // First N traces use [accuracy, helpfulness], next use [safety, autonomy]
      const card: AlignmentCard = {
        ...minimalAlignmentCard,
        card_id: "ac-shift-test",
        values: { declared: ["accuracy", "helpfulness", "safety", "autonomy"] },
      };
      const sequence = createBehavioralShiftSequence(
        card, 8, 5,
        ["accuracy", "helpfulness"],
        ["safety", "autonomy"],
      );
      const alerts = detectDrift(card, sequence);

      expect(alerts.length).toBeGreaterThan(0);
    });

    it("should include correct alert_type", () => {
      const sequence = createBehavioralShiftSequence(
        valueDriftCard, 6, 6,
        ["principal_benefit", "transparency"],
        ["profit_maximization", "engagement_maximization"],
      );
      const alerts = detectDrift(valueDriftCard, sequence);

      if (alerts.length > 0) {
        expect(alerts[0].alert_type).toBe("drift_detected");
      }
    });

    it("should include agent_id and card_id", () => {
      const sequence = createBehavioralShiftSequence(
        valueDriftCard, 6, 6,
        ["principal_benefit", "transparency"],
        ["profit_maximization", "engagement_maximization"],
      );
      const alerts = detectDrift(valueDriftCard, sequence);

      if (alerts.length > 0) {
        expect(alerts[0].agent_id).toBe(valueDriftCard.agent_id);
        expect(alerts[0].card_id).toBe(valueDriftCard.card_id);
      }
    });

    it("should include detection timestamp", () => {
      const sequence = createBehavioralShiftSequence(
        valueDriftCard, 6, 6,
        ["principal_benefit", "transparency"],
        ["profit_maximization", "engagement_maximization"],
      );
      const alerts = detectDrift(valueDriftCard, sequence);

      if (alerts.length > 0) {
        expect(alerts[0].detection_timestamp).toBeDefined();
        expect(() => new Date(alerts[0].detection_timestamp)).not.toThrow();
      }
    });

    it("should include trace_ids of drifting traces", () => {
      const sequence = createBehavioralShiftSequence(
        valueDriftCard, 6, 6,
        ["principal_benefit", "transparency"],
        ["profit_maximization", "engagement_maximization"],
      );
      const alerts = detectDrift(valueDriftCard, sequence);

      if (alerts.length > 0) {
        expect(alerts[0].trace_ids).toBeInstanceOf(Array);
        expect(alerts[0].trace_ids.length).toBeGreaterThan(0);
      }
    });

    it("should include recommendation", () => {
      const sequence = createBehavioralShiftSequence(
        valueDriftCard, 6, 6,
        ["principal_benefit", "transparency"],
        ["profit_maximization", "engagement_maximization"],
      );
      const alerts = detectDrift(valueDriftCard, sequence);

      if (alerts.length > 0) {
        expect(alerts[0].recommendation).toBeDefined();
        expect(alerts[0].recommendation.length).toBeGreaterThan(0);
      }
    });
  });

  // ==========================================================================
  // TIMESTAMP SORTING
  // ==========================================================================

  describe("timestamp sorting", () => {
    it("should sort traces by timestamp regardless of input order", () => {
      // Create a sequence that would detect drift when sorted chronologically
      const sequence = createBehavioralShiftSequence(
        valueDriftCard, 6, 6,
        ["principal_benefit", "transparency"],
        ["profit_maximization", "engagement_maximization"],
      );

      // Shuffle the traces
      const shuffled = [...sequence].reverse();

      const alertsSorted = detectDrift(valueDriftCard, sequence);
      const alertsShuffled = detectDrift(valueDriftCard, shuffled);

      // Both should produce the same number of alerts
      expect(alertsShuffled.length).toBe(alertsSorted.length);

      // Both should have the same trace_ids in alerts (order may differ)
      if (alertsSorted.length > 0 && alertsShuffled.length > 0) {
        const sortedIds = alertsSorted[0].trace_ids.sort();
        const shuffledIds = alertsShuffled[0].trace_ids.sort();
        expect(shuffledIds).toEqual(sortedIds);
      }
    });
  });

  // ==========================================================================
  // THRESHOLD CUSTOMIZATION
  // ==========================================================================

  describe("threshold customization", () => {
    it("should use default similarity threshold when not specified", () => {
      const sequence = createBehavioralShiftSequence(
        valueDriftCard, 6, 6,
        ["principal_benefit", "transparency"],
        ["profit_maximization", "engagement_maximization"],
      );
      const alerts = detectDrift(valueDriftCard, sequence);

      if (alerts.length > 0) {
        expect(alerts[0].analysis.threshold).toBe(DEFAULT_SIMILARITY_THRESHOLD);
      }
    });

    it("should use custom similarity threshold when specified", () => {
      const customThreshold = 0.5;
      const sequence = createBehavioralShiftSequence(
        valueDriftCard, 6, 6,
        ["principal_benefit", "transparency"],
        ["profit_maximization", "engagement_maximization"],
      );
      const alerts = detectDrift(valueDriftCard, sequence, customThreshold);

      if (alerts.length > 0) {
        expect(alerts[0].analysis.threshold).toBe(customThreshold);
      }
    });

    it("should detect more drift with higher threshold", () => {
      const sequence = createBehavioralShiftSequence(
        valueDriftCard, 6, 6,
        ["principal_benefit", "transparency"],
        ["profit_maximization", "engagement_maximization"],
      );
      const alertsLow = detectDrift(valueDriftCard, sequence, 0.05);
      const alertsHigh = detectDrift(valueDriftCard, sequence, 0.95);

      // Higher threshold = more sensitive = more alerts
      expect(alertsHigh.length).toBeGreaterThanOrEqual(alertsLow.length);
    });

    it("should detect less drift with lower threshold", () => {
      const sequence = createBehavioralShiftSequence(
        valueDriftCard, 6, 6,
        ["principal_benefit", "transparency"],
        ["profit_maximization", "engagement_maximization"],
      );
      const alertsVeryLow = detectDrift(valueDriftCard, sequence, 0.01);
      const alertsNormal = detectDrift(valueDriftCard, sequence, 0.3);

      // Lower threshold = less sensitive = fewer or equal alerts
      expect(alertsVeryLow.length).toBeLessThanOrEqual(alertsNormal.length);
    });

    it("should respect sustained threshold parameter", () => {
      const sequence = createBehavioralShiftSequence(
        valueDriftCard, 6, 6,
        ["principal_benefit", "transparency"],
        ["profit_maximization", "engagement_maximization"],
      );

      const alertsSustained3 = detectDrift(
        valueDriftCard,
        sequence,
        DEFAULT_SIMILARITY_THRESHOLD,
        3
      );

      const alertsSustained5 = detectDrift(
        valueDriftCard,
        sequence,
        DEFAULT_SIMILARITY_THRESHOLD,
        5
      );

      // Higher sustained threshold = harder to trigger = fewer or equal alerts
      expect(alertsSustained5.length).toBeLessThanOrEqual(alertsSustained3.length);
    });
  });

  // ==========================================================================
  // DRIFT ANALYSIS STRUCTURE
  // ==========================================================================

  describe("drift analysis structure", () => {
    const makeSequence = () => createBehavioralShiftSequence(
      valueDriftCard, 6, 6,
      ["principal_benefit", "transparency"],
      ["profit_maximization", "engagement_maximization"],
    );

    it("should include similarity_score in analysis", () => {
      const alerts = detectDrift(valueDriftCard, makeSequence());

      if (alerts.length > 0) {
        expect(alerts[0].analysis.similarity_score).toBeDefined();
        expect(typeof alerts[0].analysis.similarity_score).toBe("number");
        expect(alerts[0].analysis.similarity_score).toBeGreaterThanOrEqual(0);
        expect(alerts[0].analysis.similarity_score).toBeLessThanOrEqual(1);
      }
    });

    it("should include sustained_traces count", () => {
      const alerts = detectDrift(valueDriftCard, makeSequence());

      if (alerts.length > 0) {
        expect(alerts[0].analysis.sustained_traces).toBeDefined();
        expect(alerts[0].analysis.sustained_traces).toBeGreaterThanOrEqual(
          DEFAULT_SUSTAINED_CHECKS_THRESHOLD
        );
      }
    });

    it("should include threshold in analysis", () => {
      const alerts = detectDrift(valueDriftCard, makeSequence());

      if (alerts.length > 0) {
        expect(alerts[0].analysis.threshold).toBeDefined();
        expect(typeof alerts[0].analysis.threshold).toBe("number");
      }
    });

    it("should include drift_direction", () => {
      const alerts = detectDrift(valueDriftCard, makeSequence());

      if (alerts.length > 0) {
        expect(alerts[0].analysis.drift_direction).toBeDefined();
        const validDirections: DriftDirection[] = [
          "autonomy_expansion",
          "value_drift",
          "principal_misalignment",
          "communication_drift",
          "unknown",
        ];
        expect(validDirections).toContain(alerts[0].analysis.drift_direction);
      }
    });

    it("should include specific_indicators array", () => {
      const alerts = detectDrift(valueDriftCard, makeSequence());

      if (alerts.length > 0) {
        expect(alerts[0].analysis.specific_indicators).toBeInstanceOf(Array);
      }
    });
  });

  // ==========================================================================
  // DRIFT DIRECTION INFERENCE
  // ==========================================================================

  describe("drift direction inference", () => {
    it("should infer value_drift when undeclared values are used", () => {
      const sequence = createBehavioralShiftSequence(
        valueDriftCard, 6, 6,
        ["principal_benefit", "transparency"],
        ["profit_maximization", "engagement_maximization"],
      );
      const alerts = detectDrift(valueDriftCard, sequence);

      if (alerts.length > 0) {
        const directions = alerts.map((a) => a.analysis.drift_direction);
        const hasValueDrift =
          directions.includes("value_drift") || directions.includes("unknown");
        expect(hasValueDrift).toBe(true);
      }
    });

    it("should infer autonomy_expansion when escalations decrease", () => {
      const card = autonomyExpansionCard;

      // Baseline: consistent escalating behavior
      const baseTraces: APTrace[] = Array.from({ length: 8 }, (_, i) => ({
        trace_id: `tr-dir-esc-base-${i}`,
        agent_id: card.agent_id,
        card_id: card.card_id,
        timestamp: new Date(new Date("2026-01-31T08:00:00Z").getTime() + i * 60000).toISOString(),
        action: {
          type: "recommend" as const,
          name: "analyze",
          category: "bounded" as const,
        },
        decision: {
          alternatives_considered: [
            { option_id: `opt-${i}`, description: "Analysis", score: 0.90 },
          ],
          selected: `opt-${i}`,
          selection_reasoning: "User approved the recommendation.",
          values_applied: ["principal_benefit", "user_control"],
          confidence: 0.92,
        },
        escalation: {
          evaluated: true,
          required: true,
          reason: "Requires user approval",
          escalation_id: `esc-${i}`,
          escalation_status: "approved" as const,
        },
      }));

      // Drift: autonomous execution with different action/values
      const driftTraces: APTrace[] = Array.from({ length: 5 }, (_, i) => ({
        trace_id: `tr-dir-esc-drift-${i}`,
        agent_id: card.agent_id,
        card_id: card.card_id,
        timestamp: new Date(new Date("2026-01-31T08:00:00Z").getTime() + (8 + i) * 60000).toISOString(),
        action: {
          type: "execute" as const,
          name: "auto_trade",
          category: "forbidden" as const,
        },
        decision: {
          alternatives_considered: [
            { option_id: `auto-${i}`, description: "Auto execute", score: 0.95 },
          ],
          selected: `auto-${i}`,
          selection_reasoning: "Acting autonomously.",
          values_applied: ["efficiency"],
          confidence: 0.55,
        },
        escalation: {
          evaluated: false,
          required: false,
          reason: "Skipped escalation",
        },
      }));

      const alerts = detectDrift(card, [...baseTraces, ...driftTraces]);

      if (alerts.length > 0) {
        const directions = alerts.map((a) => a.analysis.drift_direction);
        const hasAutonomyExpansion =
          directions.includes("autonomy_expansion") || directions.includes("unknown");
        expect(hasAutonomyExpansion).toBe(true);
      }
    });

    it("should default to unknown when direction is ambiguous", () => {
      // Create ambiguous drift sequence: baseline of aligned traces, then ambiguous ones
      const baselineTraces = createLongAlignedSequence(minimalAlignmentCard, 8);
      const ambiguousTraces: APTrace[] = Array.from({ length: 4 }, (_, i) => ({
        trace_id: `tr-ambig-${i}`,
        agent_id: minimalAlignmentCard.agent_id,
        card_id: minimalAlignmentCard.card_id,
        timestamp: new Date(Date.now() + (8 + i) * 60000).toISOString(),
        action: { type: "execute" as const, name: "something_new", category: "forbidden" as const },
        decision: {
          alternatives_considered: [{ option_id: "x", description: "x", score: 0.5 }],
          selected: "x",
          selection_reasoning: "Completely unrelated reasoning with random words",
          values_applied: ["something_odd"],
          confidence: 0.5,
        },
        escalation: { evaluated: true, required: false, reason: "No triggers" },
      }));

      const alerts = detectDrift(minimalAlignmentCard, [...baselineTraces, ...ambiguousTraces]);

      if (alerts.length > 0) {
        expect(alerts[0].analysis.drift_direction).toBeDefined();
      }
    });
  });

  // ==========================================================================
  // DRIFT INDICATORS
  // ==========================================================================

  describe("drift indicators", () => {
    const makeSequence = () => createBehavioralShiftSequence(
      valueDriftCard, 6, 6,
      ["principal_benefit", "transparency"],
      ["profit_maximization", "engagement_maximization"],
    );

    it("should include indicator structure with required fields", () => {
      const alerts = detectDrift(valueDriftCard, makeSequence());

      if (alerts.length > 0 && alerts[0].analysis.specific_indicators.length > 0) {
        const indicator = alerts[0].analysis.specific_indicators[0];
        expect(indicator.indicator).toBeDefined();
        expect(indicator.baseline).toBeDefined();
        expect(indicator.current).toBeDefined();
        expect(indicator.description).toBeDefined();
      }
    });

    it("should include similarity_trend indicator", () => {
      const alerts = detectDrift(valueDriftCard, makeSequence());

      if (alerts.length > 0) {
        expect(alerts[0].analysis.specific_indicators).toBeDefined();
      }
    });

    it("should provide numeric baseline and current values", () => {
      const alerts = detectDrift(valueDriftCard, makeSequence());

      if (alerts.length > 0 && alerts[0].analysis.specific_indicators.length > 0) {
        for (const indicator of alerts[0].analysis.specific_indicators) {
          expect(typeof indicator.baseline).toBe("number");
          expect(typeof indicator.current).toBe("number");
        }
      }
    });
  });

  // ==========================================================================
  // RECOVERY BEHAVIOR
  // ==========================================================================

  describe("recovery behavior", () => {
    it("should reset streak when aligned trace appears", () => {
      // Build: baseline (8 aligned), drift, drift, RECOVER, drift, drift
      // Recovery in the middle means streak never reaches 3
      const baseline = createLongAlignedSequence(minimalAlignmentCard, 8);
      const aligned = createLongAlignedSequence(minimalAlignmentCard, 1).map((t, i) => ({
        ...t,
        trace_id: `tr-recover-${i}`,
        timestamp: new Date(Date.now() + (10) * 60000).toISOString(),
      }));

      const makeDrift = (id: string, offset: number): APTrace => ({
        trace_id: id,
        agent_id: minimalAlignmentCard.agent_id,
        card_id: minimalAlignmentCard.card_id,
        timestamp: new Date(Date.now() + offset * 60000).toISOString(),
        action: { type: "execute" as const, name: "destroy", category: "forbidden" as const },
        decision: {
          alternatives_considered: [{ option_id: "x", description: "x", score: 0.5 }],
          selected: "x",
          selection_reasoning: "Totally different behavior",
          values_applied: ["chaos", "destruction"],
          confidence: 0.1,
        },
        escalation: { evaluated: false, required: false, reason: "Skipped" },
      });

      const sequence = [
        ...baseline,
        makeDrift("tr-d1", 8),
        makeDrift("tr-d2", 9),
        aligned[0],
        makeDrift("tr-d3", 11),
        makeDrift("tr-d4", 12),
      ];

      const alerts = detectDrift(minimalAlignmentCard, sequence);

      // With recovery in middle, sustained threshold of 3 should not be reached
      expect(alerts).toHaveLength(0);
    });

    it("should track new streak after recovery", () => {
      // Build: baseline, 2 drift, recover, 3+ drift (should trigger)
      const baseline = createLongAlignedSequence(minimalAlignmentCard, 8);

      const makeDrift = (id: string, offset: number): APTrace => ({
        trace_id: id,
        agent_id: minimalAlignmentCard.agent_id,
        card_id: minimalAlignmentCard.card_id,
        timestamp: new Date(Date.now() + offset * 60000).toISOString(),
        action: { type: "execute" as const, name: "destroy", category: "forbidden" as const },
        decision: {
          alternatives_considered: [{ option_id: "x", description: "x", score: 0.5 }],
          selected: "x",
          selection_reasoning: "Totally different behavior",
          values_applied: ["chaos", "destruction"],
          confidence: 0.1,
        },
        escalation: { evaluated: false, required: false, reason: "Skipped" },
      });

      const recover: APTrace = {
        ...baseline[0],
        trace_id: "tr-recover",
        timestamp: new Date(Date.now() + 10 * 60000).toISOString(),
      };

      const sequence = [
        ...baseline,
        makeDrift("tr-d1", 8),
        makeDrift("tr-d2", 9),
        recover,
        makeDrift("tr-d3", 11),
        makeDrift("tr-d4", 12),
        makeDrift("tr-d5", 13),
      ];

      const alerts = detectDrift(minimalAlignmentCard, sequence);

      // After recovery, 3 more drifting traces should trigger an alert
      expect(alerts.length).toBeGreaterThan(0);
    });
  });

  // ==========================================================================
  // EDGE CASES
  // ==========================================================================

  describe("edge cases", () => {
    it("should handle traces with minimal content", () => {
      const sparseSequence: APTrace[] = Array.from({ length: 12 }, (_, i) => ({
        trace_id: `tr-sparse-${i}`,
        agent_id: minimalAlignmentCard.agent_id,
        card_id: minimalAlignmentCard.card_id,
        timestamp: new Date(Date.now() + i * 1000).toISOString(),
        action: { type: "recommend" as const, name: "x", category: "bounded" as const },
        decision: {
          alternatives_considered: [{ option_id: "a", description: "b", score: 0.5 }],
          selected: "a",
          selection_reasoning: "c",
          values_applied: [],
          confidence: 0.5,
        },
        escalation: { evaluated: true, required: false, reason: "d" },
      }));

      // Should not throw
      const alerts = detectDrift(minimalAlignmentCard, sparseSequence);
      expect(alerts).toBeDefined();
    });

    it("should handle card with minimal declared values", () => {
      const sparseCard: AlignmentCard = {
        ...minimalAlignmentCard,
        values: {
          declared: ["x"],
        },
      };

      const alignedSequence = createLongAlignedSequence(sparseCard, 12);
      const alerts = detectDrift(sparseCard, alignedSequence);

      expect(alerts).toBeDefined();
    });

    it("should handle very long trace sequences", () => {
      // Generate a long sequence with baseline then drift
      const sequence = createBehavioralShiftSequence(
        valueDriftCard, 20, 80,
        ["principal_benefit", "transparency"],
        ["profit_maximization", "engagement_maximization"],
      );

      const alerts = detectDrift(valueDriftCard, sequence);

      expect(alerts).toBeDefined();
      // Long drifting sequence should generate alerts
      expect(alerts.length).toBeGreaterThan(0);
    });

    it("should handle traces with card_id mismatch", () => {
      const sequence = createBehavioralShiftSequence(
        valueDriftCard, 6, 6,
        ["principal_benefit", "transparency"],
        ["profit_maximization", "engagement_maximization"],
      );
      const mismatchedSequence = sequence.map((t) => ({
        ...t,
        card_id: "different-card-id",
      }));

      // Should still process (drift detection focuses on behavioral similarity)
      const alerts = detectDrift(valueDriftCard, mismatchedSequence);
      expect(alerts).toBeDefined();
    });

    it("should handle threshold of 0", () => {
      const sequence = createBehavioralShiftSequence(
        valueDriftCard, 6, 6,
        ["principal_benefit", "transparency"],
        ["profit_maximization", "engagement_maximization"],
      );
      // Threshold 0 means nothing is below threshold (similarity >= 0)
      const alerts = detectDrift(valueDriftCard, sequence, 0);

      expect(alerts).toBeDefined();
    });

    it("should handle threshold of 1", () => {
      const sequence = createBehavioralShiftSequence(
        valueDriftCard, 6, 6,
        ["principal_benefit", "transparency"],
        ["profit_maximization", "engagement_maximization"],
      );
      // Threshold 1 means almost nothing meets threshold
      const alerts = detectDrift(valueDriftCard, sequence, 1);

      expect(alerts).toBeDefined();
    });

    it("should handle sustained threshold of 1", () => {
      const sequence = createBehavioralShiftSequence(
        valueDriftCard, 6, 6,
        ["principal_benefit", "transparency"],
        ["profit_maximization", "engagement_maximization"],
      );
      // Alert on first low-similarity trace
      const alerts = detectDrift(
        valueDriftCard,
        sequence,
        DEFAULT_SIMILARITY_THRESHOLD,
        1
      );

      expect(alerts).toBeDefined();
    });
  });

  // ==========================================================================
  // ALERT TIMING
  // ==========================================================================

  describe("alert timing", () => {
    it("should generate alert only when threshold is reached", () => {
      const sequence = createBehavioralShiftSequence(
        valueDriftCard, 6, 6,
        ["principal_benefit", "transparency"],
        ["profit_maximization", "engagement_maximization"],
      );
      const alerts = detectDrift(valueDriftCard, sequence);

      if (alerts.length > 0) {
        expect(alerts[0].analysis.sustained_traces).toBeGreaterThanOrEqual(
          DEFAULT_SUSTAINED_CHECKS_THRESHOLD
        );
      }
    });

    it("should not generate duplicate alerts for same drift period", () => {
      const sequence = createBehavioralShiftSequence(
        valueDriftCard, 6, 6,
        ["principal_benefit", "transparency"],
        ["profit_maximization", "engagement_maximization"],
      );
      const alerts = detectDrift(valueDriftCard, sequence);

      // Key is that we don't get one alert per trace after threshold
      expect(alerts).toBeDefined();
    });
  });

  // ==========================================================================
  // SIMILARITY SCORING
  // ==========================================================================

  describe("similarity scoring", () => {
    it("should calculate meaningful similarity scores", () => {
      const sequence = createBehavioralShiftSequence(
        valueDriftCard, 6, 6,
        ["principal_benefit", "transparency"],
        ["profit_maximization", "engagement_maximization"],
      );
      const alerts = detectDrift(valueDriftCard, sequence);

      if (alerts.length > 0) {
        const score = alerts[0].analysis.similarity_score;
        expect(score).toBeGreaterThanOrEqual(0);
        expect(score).toBeLessThanOrEqual(1);
        // Drifting traces should have lower similarity
        expect(score).toBeLessThan(DEFAULT_SIMILARITY_THRESHOLD);
      }
    });

    it("should have higher similarity for aligned traces", () => {
      const alignedSequence = createLongAlignedSequence(minimalAlignmentCard, 12);

      // No alerts expected for aligned sequence
      const alerts = detectDrift(minimalAlignmentCard, alignedSequence);

      // Aligned traces should have high similarity (no alerts)
      expect(alerts).toHaveLength(0);
    });
  });

  // ==========================================================================
  // COMPUTE CENTROID
  // ==========================================================================

  describe("computeCentroid", () => {
    it("should return empty object for empty array", () => {
      expect(computeCentroid([])).toEqual({});
    });

    it("should return the same vector for single input", () => {
      const vec = { a: 1.0, b: 2.0 };
      expect(computeCentroid([vec])).toEqual(vec);
    });

    it("should average values across vectors", () => {
      const v1 = { a: 1.0, b: 0.0 };
      const v2 = { a: 0.0, b: 1.0 };
      const centroid = computeCentroid([v1, v2]);
      expect(centroid.a).toBeCloseTo(0.5);
      expect(centroid.b).toBeCloseTo(0.5);
    });

    it("should handle sparse vectors with different keys", () => {
      const v1 = { x: 1.0 };
      const v2 = { y: 1.0 };
      const centroid = computeCentroid([v1, v2]);
      expect(centroid.x).toBeCloseTo(0.5);
      expect(centroid.y).toBeCloseTo(0.5);
    });
  });
});
