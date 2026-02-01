/**
 * AAP TypeScript SDK - checkCoherence Tests
 *
 * Comprehensive tests for value coherence checking between Alignment Cards.
 * Tests cover: compatible cards, conflicting cards, scoring, and edge cases.
 */

import { describe, it, expect } from "vitest";
import { checkCoherence, MIN_COHERENCE_FOR_PROCEED } from "../src";
import type { AlignmentCard, CoherenceResult } from "../src";
import {
  minimalAlignmentCard,
  fullAlignmentCard,
  compatibleCardA,
  compatibleCardB,
  conflictingCardA,
  conflictingCardB,
} from "./fixtures";

describe("checkCoherence", () => {
  // ==========================================================================
  // COMPATIBLE CARDS
  // ==========================================================================

  describe("compatible cards", () => {
    it("should identify compatible cards with shared values", () => {
      const result = checkCoherence(compatibleCardA, compatibleCardB);

      expect(result.compatible).toBe(true);
      expect(result.value_alignment.conflicts).toHaveLength(0);
    });

    it("should calculate matched values correctly", () => {
      const result = checkCoherence(compatibleCardA, compatibleCardB);

      // Both cards have "principal_benefit" and "transparency"
      expect(result.value_alignment.matched).toContain("principal_benefit");
      expect(result.value_alignment.matched).toContain("transparency");
    });

    it("should identify unmatched values", () => {
      const result = checkCoherence(compatibleCardA, compatibleCardB);

      // Card A has "harm_prevention", Card B has "user_control"
      const unmatched = result.value_alignment.unmatched;
      expect(unmatched.length).toBeGreaterThan(0);
    });

    it("should recommend proceeding for compatible cards", () => {
      const result = checkCoherence(compatibleCardA, compatibleCardB);

      expect(result.proceed).toBe(true);
    });

    it("should have high coherence score for compatible cards", () => {
      const result = checkCoherence(compatibleCardA, compatibleCardB);

      expect(result.score).toBeGreaterThanOrEqual(MIN_COHERENCE_FOR_PROCEED);
    });

    it("should not propose resolution for compatible cards", () => {
      const result = checkCoherence(compatibleCardA, compatibleCardB);

      expect(result.proposed_resolution).toBeNull();
    });
  });

  // ==========================================================================
  // CONFLICTING CARDS
  // ==========================================================================

  describe("conflicting cards", () => {
    it("should identify conflicting cards", () => {
      const result = checkCoherence(conflictingCardA, conflictingCardB);

      expect(result.compatible).toBe(false);
      expect(result.value_alignment.conflicts.length).toBeGreaterThan(0);
    });

    it("should detect value in conflicts_with list", () => {
      // Card A declares principal_benefit, Card B has it in conflicts_with
      const result = checkCoherence(conflictingCardA, conflictingCardB);

      const hasConflict = result.value_alignment.conflicts.some(
        (c) =>
          (c.initiator_value === "principal_benefit" ||
            c.responder_value === "principal_benefit") ||
          (c.initiator_value === "profit_maximization" ||
            c.responder_value === "profit_maximization")
      );
      expect(hasConflict).toBe(true);
    });

    it("should not recommend proceeding for conflicting cards", () => {
      const result = checkCoherence(conflictingCardA, conflictingCardB);

      expect(result.proceed).toBe(false);
    });

    it("should have lower coherence score for conflicting cards", () => {
      const result = checkCoherence(conflictingCardA, conflictingCardB);

      expect(result.score).toBeLessThan(MIN_COHERENCE_FOR_PROCEED);
    });

    it("should propose resolution for conflicting cards", () => {
      const result = checkCoherence(conflictingCardA, conflictingCardB);

      expect(result.proposed_resolution).toBeDefined();
      expect(result.proposed_resolution).not.toBeNull();
      expect(result.proposed_resolution!.type).toBeDefined();
      expect(result.proposed_resolution!.reason).toBeDefined();
    });

    it("should include conflict descriptions", () => {
      const result = checkCoherence(conflictingCardA, conflictingCardB);

      for (const conflict of result.value_alignment.conflicts) {
        expect(conflict.description).toBeDefined();
        expect(conflict.description.length).toBeGreaterThan(0);
      }
    });
  });

  // ==========================================================================
  // SCORING
  // ==========================================================================

  describe("coherence scoring", () => {
    it("should return score between 0 and 1", () => {
      const result = checkCoherence(compatibleCardA, compatibleCardB);

      expect(result.score).toBeGreaterThanOrEqual(0);
      expect(result.score).toBeLessThanOrEqual(1);
    });

    it("should calculate perfect score for identical cards", () => {
      const result = checkCoherence(minimalAlignmentCard, minimalAlignmentCard);

      expect(result.score).toBe(1.0);
      expect(result.compatible).toBe(true);
    });

    it("should penalize conflicts in scoring", () => {
      const compatibleResult = checkCoherence(compatibleCardA, compatibleCardB);
      const conflictingResult = checkCoherence(conflictingCardA, conflictingCardB);

      expect(conflictingResult.score).toBeLessThan(compatibleResult.score);
    });

    it("should calculate matched/required ratio correctly", () => {
      // Cards with 2 shared values out of 3 total
      const cardWith3Values: AlignmentCard = {
        ...minimalAlignmentCard,
        card_id: "card-3-values",
        values: {
          declared: ["principal_benefit", "transparency", "unique_value"],
        },
      };

      const cardWith2Shared: AlignmentCard = {
        ...minimalAlignmentCard,
        card_id: "card-2-shared",
        values: {
          declared: ["principal_benefit", "transparency", "different_value"],
        },
      };

      const result = checkCoherence(cardWith3Values, cardWith2Shared);

      // Should have at least 2 matched values
      expect(result.value_alignment.matched.length).toBeGreaterThanOrEqual(2);
    });
  });

  // ==========================================================================
  // TASK VALUES
  // ==========================================================================

  describe("task values focusing", () => {
    it("should accept optional task_values parameter", () => {
      const result = checkCoherence(compatibleCardA, compatibleCardB, ["principal_benefit"]);

      expect(result).toBeDefined();
    });

    it("should focus scoring on task-relevant values", () => {
      // When specifying task values that both cards have
      const resultWithTask = checkCoherence(compatibleCardA, compatibleCardB, [
        "principal_benefit",
      ]);

      const resultWithoutTask = checkCoherence(compatibleCardA, compatibleCardB);

      // Both should succeed, but task-focused may have different score
      expect(resultWithTask.compatible).toBe(true);
      expect(resultWithoutTask.compatible).toBe(true);
    });

    it("should handle empty task_values array", () => {
      // When task_values is empty, requiredValues becomes empty set.
      // matchedCount = 0 (nothing matches empty set), so score = 0.
      // This is expected behavior - empty task_values means no required values to match.
      const result = checkCoherence(compatibleCardA, compatibleCardB, []);

      expect(result).toBeDefined();
      expect(result.score).toBe(0);
      // With score 0, compatible is false
      expect(result.compatible).toBe(false);
    });

    it("should handle task values not present in either card", () => {
      const result = checkCoherence(compatibleCardA, compatibleCardB, [
        "nonexistent_value",
      ]);

      // Should still work, just with potentially lower match
      expect(result).toBeDefined();
    });
  });

  // ==========================================================================
  // VALUE ALIGNMENT STRUCTURE
  // ==========================================================================

  describe("value alignment structure", () => {
    it("should include matched values array", () => {
      const result = checkCoherence(compatibleCardA, compatibleCardB);

      expect(result.value_alignment.matched).toBeInstanceOf(Array);
    });

    it("should include unmatched values array", () => {
      const result = checkCoherence(compatibleCardA, compatibleCardB);

      expect(result.value_alignment.unmatched).toBeInstanceOf(Array);
    });

    it("should include conflicts array", () => {
      const result = checkCoherence(conflictingCardA, conflictingCardB);

      expect(result.value_alignment.conflicts).toBeInstanceOf(Array);
    });

    it("should format conflicts with required fields", () => {
      const result = checkCoherence(conflictingCardA, conflictingCardB);

      if (result.value_alignment.conflicts.length > 0) {
        const conflict = result.value_alignment.conflicts[0];
        expect(conflict.initiator_value).toBeDefined();
        expect(conflict.responder_value).toBeDefined();
        expect(conflict.conflict_type).toBeDefined();
        expect(conflict.description).toBeDefined();
      }
    });
  });

  // ==========================================================================
  // PROCEED CONDITIONS
  // ==========================================================================

  describe("proceed conditions", () => {
    it("should set proceed=true for compatible cards above threshold", () => {
      const result = checkCoherence(compatibleCardA, compatibleCardB);

      expect(result.proceed).toBe(true);
      expect(result.score).toBeGreaterThanOrEqual(MIN_COHERENCE_FOR_PROCEED);
    });

    it("should set proceed=false when conflicts exist", () => {
      const result = checkCoherence(conflictingCardA, conflictingCardB);

      expect(result.proceed).toBe(false);
    });

    it("should include conditions array", () => {
      const result = checkCoherence(compatibleCardA, compatibleCardB);

      expect(result.conditions).toBeInstanceOf(Array);
    });

    it("should add conditions when proceeding with caveats", () => {
      // Cards that are compatible but have some unmatched values
      const result = checkCoherence(compatibleCardA, compatibleCardB);

      // May or may not have conditions depending on implementation
      expect(result.conditions).toBeDefined();
    });
  });

  // ==========================================================================
  // EDGE CASES
  // ==========================================================================

  describe("edge cases", () => {
    it("should handle cards with empty declared values", () => {
      const emptyValuesCard: AlignmentCard = {
        ...minimalAlignmentCard,
        card_id: "empty-values",
        values: {
          declared: [],
        },
      };

      const result = checkCoherence(emptyValuesCard, minimalAlignmentCard);

      expect(result).toBeDefined();
      // Empty intersection means low compatibility
      expect(result.value_alignment.matched).toHaveLength(0);
    });

    it("should handle cards with single value", () => {
      const singleValueCard: AlignmentCard = {
        ...minimalAlignmentCard,
        card_id: "single-value",
        values: {
          declared: ["principal_benefit"],
        },
      };

      const result = checkCoherence(singleValueCard, minimalAlignmentCard);

      expect(result).toBeDefined();
      expect(result.value_alignment.matched).toContain("principal_benefit");
    });

    it("should handle cards without conflicts_with field", () => {
      const noConflictsCard: AlignmentCard = {
        ...minimalAlignmentCard,
        card_id: "no-conflicts",
        values: {
          declared: ["principal_benefit", "transparency"],
          // No conflicts_with field
        },
      };

      const result = checkCoherence(noConflictsCard, minimalAlignmentCard);

      expect(result).toBeDefined();
      expect(result.compatible).toBe(true);
    });

    it("should handle null conflicts_with", () => {
      const nullConflictsCard: AlignmentCard = {
        ...minimalAlignmentCard,
        card_id: "null-conflicts",
        values: {
          declared: ["principal_benefit"],
          conflicts_with: null,
        },
      };

      const result = checkCoherence(nullConflictsCard, minimalAlignmentCard);

      expect(result).toBeDefined();
    });

    it("should handle checking card against itself", () => {
      const result = checkCoherence(fullAlignmentCard, fullAlignmentCard);

      expect(result.compatible).toBe(true);
      expect(result.score).toBe(1.0);
      expect(result.value_alignment.matched.length).toBe(
        fullAlignmentCard.values.declared.length
      );
      expect(result.value_alignment.unmatched).toHaveLength(0);
    });

    it("should be symmetric for compatible cards", () => {
      const resultAB = checkCoherence(compatibleCardA, compatibleCardB);
      const resultBA = checkCoherence(compatibleCardB, compatibleCardA);

      // Core compatibility should be symmetric
      expect(resultAB.compatible).toBe(resultBA.compatible);
      expect(resultAB.score).toBeCloseTo(resultBA.score, 2);
    });

    it("should handle very long value lists", () => {
      const manyValuesCard: AlignmentCard = {
        ...minimalAlignmentCard,
        card_id: "many-values",
        values: {
          declared: Array.from({ length: 50 }, (_, i) => `value_${i}`),
        },
      };

      const result = checkCoherence(manyValuesCard, minimalAlignmentCard);

      expect(result).toBeDefined();
    });
  });

  // ==========================================================================
  // PROPOSED RESOLUTION
  // ==========================================================================

  describe("proposed resolution", () => {
    it("should be null when no conflicts", () => {
      const result = checkCoherence(compatibleCardA, compatibleCardB);

      expect(result.proposed_resolution).toBeNull();
    });

    it("should suggest escalation for conflicts", () => {
      const result = checkCoherence(conflictingCardA, conflictingCardB);

      expect(result.proposed_resolution).not.toBeNull();
      expect(result.proposed_resolution!.type).toBe("escalate_to_principals");
    });

    it("should include reason in resolution", () => {
      const result = checkCoherence(conflictingCardA, conflictingCardB);

      if (result.proposed_resolution) {
        expect(result.proposed_resolution.reason).toBeDefined();
        expect(result.proposed_resolution.reason.length).toBeGreaterThan(0);
      }
    });
  });

  // ==========================================================================
  // MUTUAL CONFLICTS
  // ==========================================================================

  describe("mutual conflicts", () => {
    it("should detect when both cards conflict with each other", () => {
      // Card A conflicts_with profit_maximization (which B declares)
      // Card B conflicts_with principal_benefit (which A declares)
      const result = checkCoherence(conflictingCardA, conflictingCardB);

      expect(result.compatible).toBe(false);
      // Should detect at least one conflict
      expect(result.value_alignment.conflicts.length).toBeGreaterThanOrEqual(1);
    });

    it("should detect one-way conflicts", () => {
      // Only one card has conflicts_with
      const cardWithConflicts: AlignmentCard = {
        ...minimalAlignmentCard,
        card_id: "has-conflicts",
        values: {
          declared: ["principal_benefit"],
          conflicts_with: ["evil_value"],
        },
      };

      const cardWithEvilValue: AlignmentCard = {
        ...minimalAlignmentCard,
        card_id: "has-evil",
        values: {
          declared: ["evil_value"],
          // No conflicts_with
        },
      };

      const result = checkCoherence(cardWithConflicts, cardWithEvilValue);

      expect(result.compatible).toBe(false);
      expect(result.value_alignment.conflicts.length).toBeGreaterThan(0);
    });
  });
});
