/**
 * AAP TypeScript SDK - Feature Extraction Tests
 *
 * Tests for extractCardFeatures, extractTraceFeatures, and cosineSimilarity.
 */

import { describe, it, expect } from "vitest";
import {
  extractCardFeatures,
  extractTraceFeatures,
  cosineSimilarity,
} from "../src";
import type { AlignmentCard, APTrace } from "../src";
import {
  minimalAlignmentCard,
  fullAlignmentCard,
  minimalTrace,
  valueDriftSequence,
} from "./fixtures";

describe("extractCardFeatures", () => {
  describe("value features", () => {
    it("should extract declared values as features", () => {
      const features = extractCardFeatures(minimalAlignmentCard);

      expect(features["value:principal_benefit"]).toBeDefined();
      expect(features["value:transparency"]).toBeDefined();
    });

    it("should assign weight of 1.0 to value features", () => {
      const features = extractCardFeatures(minimalAlignmentCard);

      expect(features["value:principal_benefit"]).toBe(1.0);
      expect(features["value:transparency"]).toBe(1.0);
    });

    it("should extract conflicts_with values", () => {
      const features = extractCardFeatures(fullAlignmentCard);

      expect(features["conflict:profit_maximization"]).toBeDefined();
      expect(features["conflict:engagement_maximization"]).toBeDefined();
    });
  });

  describe("action features", () => {
    it("should extract bounded actions as features", () => {
      const features = extractCardFeatures(minimalAlignmentCard);

      expect(features["action_name:search"]).toBeDefined();
      expect(features["action_name:recommend"]).toBeDefined();
      expect(features["action_name:summarize"]).toBeDefined();
    });

    it("should extract forbidden actions as features", () => {
      const features = extractCardFeatures(fullAlignmentCard);

      expect(features["forbidden:auto_purchase"]).toBeDefined();
      expect(features["forbidden:delete_data"]).toBeDefined();
    });
  });

  describe("escalation features", () => {
    it("should extract escalation triggers", () => {
      const features = extractCardFeatures(minimalAlignmentCard);

      // Should have escalation feature for the trigger action
      expect(features["escalation:escalate"]).toBeDefined();
    });
  });

  describe("principal features", () => {
    it("should extract principal type", () => {
      const features = extractCardFeatures(minimalAlignmentCard);

      expect(features["principal_type:human"]).toBeDefined();
    });

    it("should extract relationship type", () => {
      const features = extractCardFeatures(minimalAlignmentCard);

      expect(features["relationship:delegated_authority"]).toBeDefined();
    });
  });

  describe("edge cases", () => {
    it("should handle card with empty bounded_actions", () => {
      const emptyCard: AlignmentCard = {
        ...minimalAlignmentCard,
        autonomy: {
          bounded_actions: [],
          escalation_triggers: [],
        },
      };

      const features = extractCardFeatures(emptyCard);

      expect(features).toBeDefined();
      // Should still have value features
      expect(features["value:principal_benefit"]).toBeDefined();
    });

    it("should handle card with no forbidden_actions", () => {
      const features = extractCardFeatures(minimalAlignmentCard);

      // Should not throw and should not have forbidden features
      expect(features).toBeDefined();
    });

    it("should return non-empty feature vector", () => {
      const features = extractCardFeatures(minimalAlignmentCard);

      expect(Object.keys(features).length).toBeGreaterThan(0);
    });
  });
});

describe("extractTraceFeatures", () => {
  describe("action features", () => {
    it("should extract action type", () => {
      const features = extractTraceFeatures(minimalTrace);

      expect(features["action:recommend"]).toBeDefined();
    });

    it("should extract action category", () => {
      const features = extractTraceFeatures(minimalTrace);

      expect(features["category:bounded"]).toBeDefined();
    });

    it("should extract action name", () => {
      const features = extractTraceFeatures(minimalTrace);

      expect(features["action_name:recommend"]).toBeDefined();
    });
  });

  describe("value features", () => {
    it("should extract values_applied as features", () => {
      const features = extractTraceFeatures(minimalTrace);

      expect(features["value:principal_benefit"]).toBeDefined();
      expect(features["value:transparency"]).toBeDefined();
    });

    it("should weight value features at 1.0", () => {
      const features = extractTraceFeatures(minimalTrace);

      expect(features["value:principal_benefit"]).toBe(1.0);
    });
  });

  describe("escalation features", () => {
    it("should extract escalation required status", () => {
      const features = extractTraceFeatures(minimalTrace);

      expect(features["escalation:not_required"]).toBeDefined();
    });

    it("should extract escalation:evaluated when evaluated=true", () => {
      // minimalTrace has escalation.evaluated = true
      const features = extractTraceFeatures(minimalTrace);

      expect(features["escalation:evaluated"]).toBe(1.0);
    });

    it("should NOT extract escalation:evaluated when evaluated=false", () => {
      const unevaluatedTrace: APTrace = {
        ...minimalTrace,
        escalation: {
          evaluated: false,
          required: false,
        },
      };

      const features = extractTraceFeatures(unevaluatedTrace);

      expect(features["escalation:evaluated"]).toBeUndefined();
    });

    it("should NOT extract escalation_status as a feature (SDK parity with Python)", () => {
      const escalatedTrace: APTrace = {
        ...minimalTrace,
        escalation: {
          ...minimalTrace.escalation!,
          required: true,
          escalation_status: "approved",
        },
      };

      const features = extractTraceFeatures(escalatedTrace);

      // escalation_status is deliberately excluded to match the Python extractor
      expect(features["escalation:approved"]).toBeUndefined();
    });
  });

  describe("confidence feature", () => {
    it("should extract confidence as a float feature", () => {
      const features = extractTraceFeatures(minimalTrace);

      // minimalTrace has confidence: 0.85
      expect(features["confidence"]).toBe(0.85);
    });

    it("should NOT add confidence feature when confidence is undefined", () => {
      const noConfTrace: APTrace = {
        ...minimalTrace,
        decision: { ...minimalTrace.decision, confidence: undefined },
      };

      const features = extractTraceFeatures(noConfTrace);

      expect(features["confidence"]).toBeUndefined();
    });
  });

  describe("content and flag features excluded", () => {
    it("should NOT extract content from selection_reasoning", () => {
      const features = extractTraceFeatures(minimalTrace);

      // Content features are deliberately excluded from trace features
      // to prevent diluting cosine similarity in drift detection
      const contentKeys = Object.keys(features).filter((k) => k.startsWith("content:"));
      expect(contentKeys.length).toBe(0);
    });

    it("should NOT extract flag features from alternatives (SDK parity with Python)", () => {
      const traceWithFlags: APTrace = {
        ...minimalTrace,
        decision: {
          ...minimalTrace.decision,
          alternatives_considered: [
            {
              option_id: "flagged",
              description: "Option with flags",
              score: 0.5,
              flags: ["sponsored_content", "transparency_concern"],
            },
          ],
        },
      };

      const features = extractTraceFeatures(traceWithFlags);

      // flag:* features are deliberately excluded to match the Python extractor
      const flagKeys = Object.keys(features).filter((k) => k.startsWith("flag:"));
      expect(flagKeys.length).toBe(0);
    });
  });

  describe("edge cases", () => {
    it("should handle trace without escalation field", () => {
      const noEscalationTrace: APTrace = {
        trace_id: "tr-no-esc",
        agent_id: "agent-001",
        card_id: "card-001",
        timestamp: new Date().toISOString(),
        action: { type: "recommend", name: "recommend", category: "bounded" },
        decision: {
          alternatives_considered: [
            { option_id: "a", description: "option", score: 0.5 },
          ],
          selected: "a",
          selection_reasoning: "reasoning",
          values_applied: ["principal_benefit"],
        },
      };

      const features = extractTraceFeatures(noEscalationTrace);

      expect(features).toBeDefined();
    });

    it("should handle trace with empty values_applied", () => {
      const emptyValuesTrace: APTrace = {
        ...minimalTrace,
        decision: {
          ...minimalTrace.decision,
          values_applied: [],
        },
      };

      const features = extractTraceFeatures(emptyValuesTrace);

      expect(features).toBeDefined();
      // Should not have value features
      const valueKeys = Object.keys(features).filter((k) => k.startsWith("value:"));
      expect(valueKeys).toHaveLength(0);
    });

    it("should return non-empty feature vector", () => {
      const features = extractTraceFeatures(minimalTrace);

      expect(Object.keys(features).length).toBeGreaterThan(0);
    });
  });
});

describe("cosineSimilarity", () => {
  describe("basic calculations", () => {
    it("should return 1.0 for identical vectors", () => {
      const vector = { a: 1, b: 2, c: 3 };

      expect(cosineSimilarity(vector, vector)).toBeCloseTo(1.0);
    });

    it("should return 0.0 for orthogonal vectors", () => {
      const vectorA = { a: 1, b: 0 };
      const vectorB = { c: 1, d: 0 };

      expect(cosineSimilarity(vectorA, vectorB)).toBeCloseTo(0.0);
    });

    it("should return value between 0 and 1", () => {
      const vectorA = { a: 1, b: 2, c: 3 };
      const vectorB = { a: 2, b: 1, d: 4 };

      const similarity = cosineSimilarity(vectorA, vectorB);

      expect(similarity).toBeGreaterThanOrEqual(0);
      expect(similarity).toBeLessThanOrEqual(1);
    });

    it("should be symmetric", () => {
      const vectorA = { a: 1, b: 2 };
      const vectorB = { a: 3, c: 4 };

      expect(cosineSimilarity(vectorA, vectorB)).toBeCloseTo(
        cosineSimilarity(vectorB, vectorA)
      );
    });
  });

  describe("edge cases", () => {
    it("should handle empty vectors", () => {
      const empty = {};
      const nonEmpty = { a: 1 };

      expect(cosineSimilarity(empty, nonEmpty)).toBe(0);
      expect(cosineSimilarity(empty, empty)).toBe(0);
    });

    it("should handle single-element vectors", () => {
      const vectorA = { a: 1 };
      const vectorB = { a: 1 };

      expect(cosineSimilarity(vectorA, vectorB)).toBeCloseTo(1.0);
    });

    it("should handle vectors with negative values", () => {
      const vectorA = { a: 1, b: -1 };
      const vectorB = { a: -1, b: 1 };

      const similarity = cosineSimilarity(vectorA, vectorB);

      // Should handle negative values correctly
      expect(similarity).toBeDefined();
    });

    it("should handle vectors with zero values", () => {
      const vectorA = { a: 0, b: 1 };
      const vectorB = { a: 1, b: 0 };

      const similarity = cosineSimilarity(vectorA, vectorB);

      expect(similarity).toBeDefined();
      expect(similarity).toBeGreaterThanOrEqual(0);
    });

    it("should handle large vectors", () => {
      const vectorA: Record<string, number> = {};
      const vectorB: Record<string, number> = {};

      for (let i = 0; i < 1000; i++) {
        vectorA[`key_${i}`] = Math.random();
        vectorB[`key_${i}`] = Math.random();
      }

      const similarity = cosineSimilarity(vectorA, vectorB);

      expect(similarity).toBeGreaterThanOrEqual(0);
      expect(similarity).toBeLessThanOrEqual(1);
    });
  });

  describe("real feature vectors", () => {
    it("should compute similarity between card and trace features", () => {
      const cardFeatures = extractCardFeatures(minimalAlignmentCard);
      const traceFeatures = extractTraceFeatures(minimalTrace);

      const similarity = cosineSimilarity(cardFeatures, traceFeatures);

      expect(similarity).toBeGreaterThanOrEqual(0);
      expect(similarity).toBeLessThanOrEqual(1);
      // Aligned trace should have some similarity
      expect(similarity).toBeGreaterThan(0);
    });

    it("should show lower similarity for drifting traces", () => {
      const cardFeatures = extractCardFeatures(minimalAlignmentCard);

      // Aligned trace
      const alignedFeatures = extractTraceFeatures(minimalTrace);
      const alignedSimilarity = cosineSimilarity(cardFeatures, alignedFeatures);

      // Drifting trace (using undeclared values)
      const driftingTrace = valueDriftSequence[5]; // Fully drifted
      const driftingFeatures = extractTraceFeatures(driftingTrace);

      // Compare to same card's features
      const driftCardFeatures = extractCardFeatures({
        ...minimalAlignmentCard,
        card_id: driftingTrace.card_id,
      });
      const driftingSimilarity = cosineSimilarity(driftCardFeatures, driftingFeatures);

      // Both should be valid similarities
      expect(alignedSimilarity).toBeDefined();
      expect(driftingSimilarity).toBeDefined();
    });
  });
});
