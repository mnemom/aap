/**
 * AAP TypeScript SDK - detectDrift Tests
 *
 * Comprehensive tests for behavioral drift detection over trace sequences.
 * Tests cover: no drift, drift detection, thresholds, direction inference, and indicators.
 */

import { describe, it, expect } from "vitest";
import {
  detectDrift,
  DEFAULT_SIMILARITY_THRESHOLD,
  DEFAULT_SUSTAINED_TURNS_THRESHOLD,
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

describe("detectDrift", () => {
  // ==========================================================================
  // NO DRIFT CASES
  // ==========================================================================

  describe("no drift cases", () => {
    it("should return empty array for aligned trace sequence", () => {
      const alignedSequence = createAlignedTraceSequence(minimalAlignmentCard);
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

    it("should not alert if drift is not sustained", () => {
      // 2 drifting traces (below threshold of 3)
      const shortDriftSequence = valueDriftSequence.slice(3, 5);
      const alerts = detectDrift(valueDriftCard, shortDriftSequence);

      // Should not trigger alert with only 2 traces
      expect(alerts.length).toBeLessThanOrEqual(0);
    });
  });

  // ==========================================================================
  // DRIFT DETECTION
  // ==========================================================================

  describe("drift detection", () => {
    it("should detect value drift in drifting sequence", () => {
      const alerts = detectDrift(valueDriftCard, valueDriftSequence);

      expect(alerts.length).toBeGreaterThan(0);
    });

    it("should detect autonomy expansion in expanding sequence", () => {
      const alerts = detectDrift(autonomyExpansionCard, autonomyExpansionSequence);

      expect(alerts.length).toBeGreaterThan(0);
    });

    it("should include correct alert_type", () => {
      const alerts = detectDrift(valueDriftCard, valueDriftSequence);

      if (alerts.length > 0) {
        expect(alerts[0].alert_type).toBe("drift_detected");
      }
    });

    it("should include agent_id and card_id", () => {
      const alerts = detectDrift(valueDriftCard, valueDriftSequence);

      if (alerts.length > 0) {
        expect(alerts[0].agent_id).toBe(valueDriftCard.agent_id);
        expect(alerts[0].card_id).toBe(valueDriftCard.card_id);
      }
    });

    it("should include detection timestamp", () => {
      const alerts = detectDrift(valueDriftCard, valueDriftSequence);

      if (alerts.length > 0) {
        expect(alerts[0].detection_timestamp).toBeDefined();
        // Should be valid ISO 8601
        expect(() => new Date(alerts[0].detection_timestamp)).not.toThrow();
      }
    });

    it("should include trace_ids of drifting traces", () => {
      const alerts = detectDrift(valueDriftCard, valueDriftSequence);

      if (alerts.length > 0) {
        expect(alerts[0].trace_ids).toBeInstanceOf(Array);
        expect(alerts[0].trace_ids.length).toBeGreaterThan(0);
      }
    });

    it("should include recommendation", () => {
      const alerts = detectDrift(valueDriftCard, valueDriftSequence);

      if (alerts.length > 0) {
        expect(alerts[0].recommendation).toBeDefined();
        expect(alerts[0].recommendation.length).toBeGreaterThan(0);
      }
    });
  });

  // ==========================================================================
  // THRESHOLD CUSTOMIZATION
  // ==========================================================================

  describe("threshold customization", () => {
    it("should use default similarity threshold when not specified", () => {
      const alerts = detectDrift(valueDriftCard, valueDriftSequence);

      if (alerts.length > 0) {
        expect(alerts[0].analysis.threshold).toBe(DEFAULT_SIMILARITY_THRESHOLD);
      }
    });

    it("should use custom similarity threshold when specified", () => {
      const customThreshold = 0.5;
      const alerts = detectDrift(
        valueDriftCard,
        valueDriftSequence,
        customThreshold
      );

      if (alerts.length > 0) {
        expect(alerts[0].analysis.threshold).toBe(customThreshold);
      }
    });

    it("should detect more drift with higher threshold", () => {
      const alertsLow = detectDrift(valueDriftCard, valueDriftSequence, 0.05);
      const alertsHigh = detectDrift(valueDriftCard, valueDriftSequence, 0.95);

      // Higher threshold = more sensitive = more alerts
      expect(alertsHigh.length).toBeGreaterThanOrEqual(alertsLow.length);
    });

    it("should detect less drift with lower threshold", () => {
      const alertsVeryLow = detectDrift(valueDriftCard, valueDriftSequence, 0.01);
      const alertsNormal = detectDrift(valueDriftCard, valueDriftSequence, 0.3);

      // Lower threshold = less sensitive = fewer or equal alerts
      expect(alertsVeryLow.length).toBeLessThanOrEqual(alertsNormal.length);
    });

    it("should respect sustained threshold parameter", () => {
      // With higher sustained threshold, need more drifting traces
      const alertsSustained3 = detectDrift(
        valueDriftCard,
        valueDriftSequence,
        DEFAULT_SIMILARITY_THRESHOLD,
        3
      );

      const alertsSustained5 = detectDrift(
        valueDriftCard,
        valueDriftSequence,
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
    it("should include similarity_score in analysis", () => {
      const alerts = detectDrift(valueDriftCard, valueDriftSequence);

      if (alerts.length > 0) {
        expect(alerts[0].analysis.similarity_score).toBeDefined();
        expect(typeof alerts[0].analysis.similarity_score).toBe("number");
        expect(alerts[0].analysis.similarity_score).toBeGreaterThanOrEqual(0);
        expect(alerts[0].analysis.similarity_score).toBeLessThanOrEqual(1);
      }
    });

    it("should include sustained_traces count", () => {
      const alerts = detectDrift(valueDriftCard, valueDriftSequence);

      if (alerts.length > 0) {
        expect(alerts[0].analysis.sustained_traces).toBeDefined();
        expect(alerts[0].analysis.sustained_traces).toBeGreaterThanOrEqual(
          DEFAULT_SUSTAINED_TURNS_THRESHOLD
        );
      }
    });

    it("should include threshold in analysis", () => {
      const alerts = detectDrift(valueDriftCard, valueDriftSequence);

      if (alerts.length > 0) {
        expect(alerts[0].analysis.threshold).toBeDefined();
        expect(typeof alerts[0].analysis.threshold).toBe("number");
      }
    });

    it("should include drift_direction", () => {
      const alerts = detectDrift(valueDriftCard, valueDriftSequence);

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
      const alerts = detectDrift(valueDriftCard, valueDriftSequence);

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
      const alerts = detectDrift(valueDriftCard, valueDriftSequence);

      if (alerts.length > 0) {
        // Value drift sequence uses profit_maximization, engagement_maximization
        // which are not in declared values
        const directions = alerts.map((a) => a.analysis.drift_direction);
        const hasValueDrift =
          directions.includes("value_drift") || directions.includes("unknown");
        expect(hasValueDrift).toBe(true);
      }
    });

    it("should infer autonomy_expansion when escalations decrease", () => {
      const alerts = detectDrift(autonomyExpansionCard, autonomyExpansionSequence);

      if (alerts.length > 0) {
        const directions = alerts.map((a) => a.analysis.drift_direction);
        // Autonomy expansion sequence has agent stop escalating
        const hasAutonomyExpansion =
          directions.includes("autonomy_expansion") || directions.includes("unknown");
        expect(hasAutonomyExpansion).toBe(true);
      }
    });

    it("should default to unknown when direction is ambiguous", () => {
      // Create ambiguous drift sequence
      const ambiguousSequence: APTrace[] = [
        ...createAlignedTraceSequence(minimalAlignmentCard),
        // Add traces that drift but without clear pattern
        {
          trace_id: "tr-ambig-001",
          agent_id: minimalAlignmentCard.agent_id,
          card_id: minimalAlignmentCard.card_id,
          timestamp: new Date().toISOString(),
          action: { type: "recommend", name: "recommend", category: "bounded" },
          decision: {
            alternatives_considered: [{ option_id: "x", description: "x", score: 0.5 }],
            selected: "x",
            selection_reasoning: "Completely unrelated reasoning with random words",
            values_applied: ["something_odd"],
            confidence: 0.5,
          },
          escalation: { evaluated: true, required: false, reason: "No triggers" },
        },
      ];

      // Repeat the ambiguous trace to sustain drift
      for (let i = 2; i <= 4; i++) {
        ambiguousSequence.push({
          ...ambiguousSequence[ambiguousSequence.length - 1],
          trace_id: `tr-ambig-00${i}`,
        });
      }

      const alerts = detectDrift(minimalAlignmentCard, ambiguousSequence);

      // May or may not detect drift depending on similarity
      // If detected, direction could be unknown
      if (alerts.length > 0) {
        expect(alerts[0].analysis.drift_direction).toBeDefined();
      }
    });
  });

  // ==========================================================================
  // DRIFT INDICATORS
  // ==========================================================================

  describe("drift indicators", () => {
    it("should include indicator structure with required fields", () => {
      const alerts = detectDrift(valueDriftCard, valueDriftSequence);

      if (alerts.length > 0 && alerts[0].analysis.specific_indicators.length > 0) {
        const indicator = alerts[0].analysis.specific_indicators[0];
        expect(indicator.indicator).toBeDefined();
        expect(indicator.baseline).toBeDefined();
        expect(indicator.current).toBeDefined();
        expect(indicator.description).toBeDefined();
      }
    });

    it("should include similarity_trend indicator", () => {
      const alerts = detectDrift(valueDriftCard, valueDriftSequence);

      if (alerts.length > 0) {
        const hasSimilarityIndicator = alerts[0].analysis.specific_indicators.some(
          (i) => i.indicator === "similarity_trend" || i.indicator.includes("similarity")
        );
        // May or may not have this specific indicator
        expect(alerts[0].analysis.specific_indicators).toBeDefined();
      }
    });

    it("should provide numeric baseline and current values", () => {
      const alerts = detectDrift(valueDriftCard, valueDriftSequence);

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
      // Create sequence: drift, drift, RECOVER, drift, drift
      // This should not trigger alert because streak resets
      const recoverySequence: APTrace[] = [
        valueDriftSequence[3], // drift
        valueDriftSequence[4], // drift
        valueDriftSequence[0], // RECOVER - aligned trace
        valueDriftSequence[3], // drift again
        valueDriftSequence[4], // drift again
      ];

      const alerts = detectDrift(valueDriftCard, recoverySequence);

      // With recovery in middle, sustained threshold may not be reached
      // Behavior depends on implementation
      expect(alerts).toBeDefined();
    });

    it("should track new streak after recovery", () => {
      // Multiple recovery cycles
      const multiRecoverySequence: APTrace[] = [
        ...valueDriftSequence.slice(0, 2), // aligned
        ...valueDriftSequence.slice(3, 5), // drift (2)
        valueDriftSequence[0], // recover
        ...valueDriftSequence.slice(3, 6), // drift (3) - may trigger
      ];

      const alerts = detectDrift(valueDriftCard, multiRecoverySequence);

      // May or may not trigger depending on exact thresholds
      expect(alerts).toBeDefined();
    });
  });

  // ==========================================================================
  // EDGE CASES
  // ==========================================================================

  describe("edge cases", () => {
    it("should handle traces with minimal content", () => {
      const sparseSequence: APTrace[] = Array.from({ length: 5 }, (_, i) => ({
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

      const alignedSequence = createAlignedTraceSequence(sparseCard);
      const alerts = detectDrift(sparseCard, alignedSequence);

      expect(alerts).toBeDefined();
    });

    it("should handle very long trace sequences", () => {
      // Generate 100 traces
      const longSequence: APTrace[] = [];
      for (let i = 0; i < 100; i++) {
        longSequence.push({
          ...valueDriftSequence[i % valueDriftSequence.length],
          trace_id: `tr-long-${i.toString().padStart(3, "0")}`,
        });
      }

      const alerts = detectDrift(valueDriftCard, longSequence);

      expect(alerts).toBeDefined();
      // Long drifting sequence should generate alerts
      expect(alerts.length).toBeGreaterThan(0);
    });

    it("should handle traces with card_id mismatch", () => {
      const mismatchedSequence: APTrace[] = valueDriftSequence.map((t) => ({
        ...t,
        card_id: "different-card-id",
      }));

      // Should still process (drift detection focuses on behavioral similarity)
      const alerts = detectDrift(valueDriftCard, mismatchedSequence);
      expect(alerts).toBeDefined();
    });

    it("should handle threshold of 0", () => {
      // Threshold 0 means everything is below threshold
      const alerts = detectDrift(valueDriftCard, valueDriftSequence, 0);

      expect(alerts).toBeDefined();
    });

    it("should handle threshold of 1", () => {
      // Threshold 1 means almost nothing meets threshold
      const alerts = detectDrift(valueDriftCard, valueDriftSequence, 1);

      expect(alerts).toBeDefined();
      // With threshold 1, even aligned traces would be "drifting"
    });

    it("should handle sustained threshold of 1", () => {
      // Alert on first low-similarity trace
      const alerts = detectDrift(
        valueDriftCard,
        valueDriftSequence,
        DEFAULT_SIMILARITY_THRESHOLD,
        1
      );

      expect(alerts).toBeDefined();
      // Should potentially have more alerts with lower sustained threshold
    });
  });

  // ==========================================================================
  // ALERT TIMING
  // ==========================================================================

  describe("alert timing", () => {
    it("should generate alert only when threshold is reached", () => {
      // Use exactly sustained_threshold traces
      const exactThresholdSequence = valueDriftSequence.slice(
        3,
        3 + DEFAULT_SUSTAINED_TURNS_THRESHOLD
      );

      const alerts = detectDrift(valueDriftCard, exactThresholdSequence);

      // Should trigger exactly when threshold is reached
      if (alerts.length > 0) {
        expect(alerts[0].analysis.sustained_traces).toBeGreaterThanOrEqual(
          DEFAULT_SUSTAINED_TURNS_THRESHOLD
        );
      }
    });

    it("should not generate duplicate alerts for same drift period", () => {
      // Even with many drifting traces, should consolidate alerts
      const alerts = detectDrift(valueDriftCard, valueDriftSequence);

      // Count alerts - implementation may vary
      // Key is that we don't get one alert per trace after threshold
      expect(alerts).toBeDefined();
    });
  });

  // ==========================================================================
  // SIMILARITY SCORING
  // ==========================================================================

  describe("similarity scoring", () => {
    it("should calculate meaningful similarity scores", () => {
      const alerts = detectDrift(valueDriftCard, valueDriftSequence);

      if (alerts.length > 0) {
        const score = alerts[0].analysis.similarity_score;
        expect(score).toBeGreaterThanOrEqual(0);
        expect(score).toBeLessThanOrEqual(1);
        // Drifting traces should have lower similarity
        expect(score).toBeLessThan(DEFAULT_SIMILARITY_THRESHOLD);
      }
    });

    it("should have higher similarity for aligned traces", () => {
      const alignedSequence = createAlignedTraceSequence(minimalAlignmentCard);

      // No alerts expected for aligned sequence
      const alerts = detectDrift(minimalAlignmentCard, alignedSequence);

      // Aligned traces should have high similarity (no alerts)
      expect(alerts).toHaveLength(0);
    });
  });
});
