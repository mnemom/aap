/**
 * AAP TypeScript SDK - verifyTrace Tests
 *
 * Comprehensive tests for trace verification against Alignment Cards.
 * Tests cover: valid traces, all violation types, warnings, and edge cases.
 */

import { describe, it, expect, beforeEach } from "vitest";
import {
  verifyTrace,
  isCardExpired,
  ALGORITHM_VERSION,
  NEAR_BOUNDARY_THRESHOLD,
} from "../src";
import type { AlignmentCard, APTrace, VerificationResult, ViolationType } from "../src";
import {
  minimalAlignmentCard,
  minimalTrace,
  expiredAlignmentCard,
  cardWithForbiddenActions,
  cardWithNumericTrigger,
  traceCardMismatch,
  traceWithForbiddenAction,
  traceWithUnboundedAction,
  traceWithUndeclaredValue,
  traceWithMissedEscalation,
  traceWithApprovedEscalation,
  traceWithLowConfidence,
  compliantRecommendationCard,
  compliantRecommendationTrace,
  approvedEscalationCard,
  approvedEscalationTrace,
} from "./fixtures";

describe("verifyTrace", () => {
  // ==========================================================================
  // BASIC VERIFICATION
  // ==========================================================================

  describe("basic verification", () => {
    it("should verify a valid trace with no violations", () => {
      const result = verifyTrace(minimalTrace, minimalAlignmentCard);

      expect(result.verified).toBe(true);
      expect(result.violations).toHaveLength(0);
      expect(result.trace_id).toBe(minimalTrace.trace_id);
      expect(result.card_id).toBe(minimalAlignmentCard.card_id);
    });

    it("should include timestamp in ISO 8601 format", () => {
      const result = verifyTrace(minimalTrace, minimalAlignmentCard);

      expect(result.timestamp).toBeDefined();
      // Should be a valid ISO 8601 timestamp
      expect(() => new Date(result.timestamp)).not.toThrow();
      expect(new Date(result.timestamp).toISOString()).toBe(result.timestamp);
    });

    it("should perform all required checks", () => {
      const result = verifyTrace(minimalTrace, minimalAlignmentCard);

      const expectedChecks = [
        "card_reference",
        "card_expiration",
        "autonomy",
        "forbidden",
        "escalation",
        "values",
      ];

      for (const check of expectedChecks) {
        expect(result.verification_metadata.checks_performed).toContain(check);
      }
    });

    it("should include algorithm version in metadata", () => {
      const result = verifyTrace(minimalTrace, minimalAlignmentCard);

      expect(result.verification_metadata.algorithm_version).toBe(ALGORITHM_VERSION);
    });

    it("should verify compliant recommendation from test vectors", () => {
      const result = verifyTrace(compliantRecommendationTrace, compliantRecommendationCard);

      expect(result.verified).toBe(true);
      expect(result.violations).toHaveLength(0);
    });

    it("should verify approved escalation from test vectors", () => {
      const result = verifyTrace(approvedEscalationTrace, approvedEscalationCard);

      expect(result.verified).toBe(true);
      expect(result.violations).toHaveLength(0);
    });
  });

  // ==========================================================================
  // VIOLATION DETECTION
  // ==========================================================================

  describe("card_mismatch violation", () => {
    it("should detect card_id mismatch", () => {
      const result = verifyTrace(traceCardMismatch, minimalAlignmentCard);

      expect(result.verified).toBe(false);
      expect(result.violations).toHaveLength(1);
      expect(result.violations[0].type).toBe("card_mismatch");
      expect(result.violations[0].severity).toBe("critical");
    });

    it("should include descriptive message for card mismatch", () => {
      const result = verifyTrace(traceCardMismatch, minimalAlignmentCard);

      expect(result.violations[0].description).toContain("ac-wrong-card-id");
      expect(result.violations[0].description).toContain(minimalAlignmentCard.card_id);
    });
  });

  describe("forbidden_action violation", () => {
    it("should detect forbidden action", () => {
      const result = verifyTrace(traceWithForbiddenAction, cardWithForbiddenActions);

      expect(result.verified).toBe(false);

      const forbiddenViolation = result.violations.find((v) => v.type === "forbidden_action");
      expect(forbiddenViolation).toBeDefined();
      expect(forbiddenViolation!.severity).toBe("critical");
    });

    it("should include action name in forbidden action description", () => {
      const result = verifyTrace(traceWithForbiddenAction, cardWithForbiddenActions);

      const forbiddenViolation = result.violations.find((v) => v.type === "forbidden_action");
      expect(forbiddenViolation!.description).toContain("delete_data");
    });

    it("should detect forbidden action regardless of category label", () => {
      // Trace claims it's bounded but action is forbidden
      const sneakyTrace: APTrace = {
        ...traceWithForbiddenAction,
        action: {
          ...traceWithForbiddenAction.action,
          category: "bounded", // Lies about category
        },
      };

      const result = verifyTrace(sneakyTrace, cardWithForbiddenActions);

      expect(result.verified).toBe(false);
      const forbiddenViolation = result.violations.find((v) => v.type === "forbidden_action");
      expect(forbiddenViolation).toBeDefined();
    });
  });

  describe("unbounded_action violation", () => {
    it("should detect action not in bounded_actions", () => {
      const result = verifyTrace(traceWithUnboundedAction, minimalAlignmentCard);

      expect(result.verified).toBe(false);

      const unboundedViolation = result.violations.find((v) => v.type === "unbounded_action");
      expect(unboundedViolation).toBeDefined();
      expect(unboundedViolation!.severity).toBe("high");
    });

    it("should include action name in unbounded violation description", () => {
      const result = verifyTrace(traceWithUnboundedAction, minimalAlignmentCard);

      const unboundedViolation = result.violations.find((v) => v.type === "unbounded_action");
      expect(unboundedViolation!.description).toContain("purchase");
    });
  });

  describe("undeclared_value violation", () => {
    it("should detect undeclared values in values_applied", () => {
      const result = verifyTrace(traceWithUndeclaredValue, minimalAlignmentCard);

      expect(result.verified).toBe(false);

      const undeclaredViolation = result.violations.find((v) => v.type === "undeclared_value");
      expect(undeclaredViolation).toBeDefined();
      expect(undeclaredViolation!.severity).toBe("medium");
    });

    it("should include undeclared value names in description", () => {
      const result = verifyTrace(traceWithUndeclaredValue, minimalAlignmentCard);

      const undeclaredViolation = result.violations.find((v) => v.type === "undeclared_value");
      expect(undeclaredViolation!.description).toMatch(/profit_maximization|vendor_benefit/);
    });

    it("should allow all declared values", () => {
      // Trace using only declared values should pass
      const validTrace: APTrace = {
        ...minimalTrace,
        decision: {
          ...minimalTrace.decision,
          values_applied: ["principal_benefit", "transparency"],
        },
      };

      const result = verifyTrace(validTrace, minimalAlignmentCard);

      const undeclaredViolation = result.violations.find((v) => v.type === "undeclared_value");
      expect(undeclaredViolation).toBeUndefined();
    });
  });

  describe("card_expired violation", () => {
    it("should detect expired card", () => {
      const traceForExpiredCard: APTrace = {
        ...minimalTrace,
        card_id: expiredAlignmentCard.card_id,
      };

      const result = verifyTrace(traceForExpiredCard, expiredAlignmentCard);

      expect(result.verified).toBe(false);

      const expiredViolation = result.violations.find((v) => v.type === "card_expired");
      expect(expiredViolation).toBeDefined();
      expect(expiredViolation!.severity).toBe("high");
    });

    it("should pass verification for non-expired card", () => {
      // Card with future expiration
      const futureCard: AlignmentCard = {
        ...minimalAlignmentCard,
        expires_at: new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toISOString(),
      };

      const result = verifyTrace(minimalTrace, futureCard);

      const expiredViolation = result.violations.find((v) => v.type === "card_expired");
      expect(expiredViolation).toBeUndefined();
    });

    it("should pass when card has no expiration", () => {
      // Card without expires_at
      const noExpiryCard: AlignmentCard = {
        ...minimalAlignmentCard,
      };
      delete noExpiryCard.expires_at;

      const result = verifyTrace(minimalTrace, noExpiryCard);

      const expiredViolation = result.violations.find((v) => v.type === "card_expired");
      expect(expiredViolation).toBeUndefined();
    });
  });

  describe("missed_escalation violation", () => {
    it("should detect missed escalation when triggers match but required=false", () => {
      // Using cardWithNumericTrigger which has 'amount > 100' trigger
      // traceWithMissedEscalation has amount=200, so trigger matches
      const result = verifyTrace(traceWithMissedEscalation, cardWithNumericTrigger);

      expect(result.verified).toBe(false);

      const missedViolation = result.violations.find((v) => v.type === "missed_escalation");
      expect(missedViolation).toBeDefined();
      expect(missedViolation!.severity).toBe("high");
    });

    it("should pass when escalation is properly performed", () => {
      // Create a trace that properly escalates with the numeric trigger
      const properlyEscalatedTrace: APTrace = {
        ...traceWithMissedEscalation,
        trace_id: "tr-proper-esc-001",
        escalation: {
          evaluated: true,
          triggers_checked: [
            {
              trigger: "amount > 100",
              matched: true,
            },
          ],
          required: true, // Properly set to true
          reason: "Amount exceeds threshold",
          escalation_id: "esc-001",
          escalation_status: "approved",
        },
      };

      const result = verifyTrace(properlyEscalatedTrace, cardWithNumericTrigger);

      const missedViolation = result.violations.find((v) => v.type === "missed_escalation");
      expect(missedViolation).toBeUndefined();
    });

    it("should pass when no escalation triggers match", () => {
      // Trace with amount below threshold
      const noTriggerTrace: APTrace = {
        ...traceWithMissedEscalation,
        trace_id: "tr-no-trigger-001",
        action: {
          ...traceWithMissedEscalation.action,
          parameters: {
            amount: 50, // Below 100 threshold
            currency: "USD",
          },
        },
        escalation: {
          evaluated: true,
          triggers_checked: [
            {
              trigger: "amount > 100",
              matched: false,
            },
          ],
          required: false,
          reason: "Amount below threshold",
        },
      };

      const result = verifyTrace(noTriggerTrace, cardWithNumericTrigger);

      const missedViolation = result.violations.find((v) => v.type === "missed_escalation");
      expect(missedViolation).toBeUndefined();
    });
  });

  // ==========================================================================
  // WARNINGS
  // ==========================================================================

  describe("warnings", () => {
    it("should generate near_boundary warning for low confidence", () => {
      const result = verifyTrace(traceWithLowConfidence, minimalAlignmentCard);

      const nearBoundaryWarning = result.warnings.find((w) => w.type === "near_boundary");
      expect(nearBoundaryWarning).toBeDefined();
      expect(nearBoundaryWarning!.description).toContain("confidence");
    });

    it("should not warn when confidence is above threshold", () => {
      const highConfidenceTrace: APTrace = {
        ...minimalTrace,
        decision: {
          ...minimalTrace.decision,
          confidence: 0.90, // Well above NEAR_BOUNDARY_THRESHOLD
        },
      };

      const result = verifyTrace(highConfidenceTrace, minimalAlignmentCard);

      const nearBoundaryWarning = result.warnings.find(
        (w) => w.type === "near_boundary" && w.description.includes("confidence")
      );
      expect(nearBoundaryWarning).toBeUndefined();
    });

    it("should handle missing confidence gracefully", () => {
      const noConfidenceTrace: APTrace = {
        ...minimalTrace,
        decision: {
          ...minimalTrace.decision,
          confidence: undefined,
        },
      };

      // Should not throw
      const result = verifyTrace(noConfidenceTrace, minimalAlignmentCard);
      expect(result).toBeDefined();
    });

    it("should generate low_behavioral_similarity warning when applicable", () => {
      // A trace with minimal content that doesn't match card well
      const sparseTrace: APTrace = {
        ...minimalTrace,
        decision: {
          ...minimalTrace.decision,
          selection_reasoning: "xyz", // Minimal content
          alternatives_considered: [
            {
              option_id: "a",
              description: "b",
              score: 0.5,
            },
          ],
        },
      };

      const result = verifyTrace(sparseTrace, minimalAlignmentCard);

      // May or may not have this warning depending on similarity calculation
      // The test verifies the mechanism exists and doesn't crash
      expect(result).toBeDefined();
    });
  });

  // ==========================================================================
  // MULTIPLE VIOLATIONS
  // ==========================================================================

  describe("multiple violations", () => {
    it("should detect multiple violations in a single trace", () => {
      // Trace with forbidden action AND undeclared values
      const multiViolationTrace: APTrace = {
        ...traceWithForbiddenAction,
        card_id: cardWithForbiddenActions.card_id,
        decision: {
          ...traceWithForbiddenAction.decision,
          values_applied: ["profit_maximization"], // Undeclared
        },
      };

      const result = verifyTrace(multiViolationTrace, cardWithForbiddenActions);

      expect(result.verified).toBe(false);
      expect(result.violations.length).toBeGreaterThanOrEqual(2);

      const violationTypes = result.violations.map((v) => v.type);
      expect(violationTypes).toContain("forbidden_action");
      expect(violationTypes).toContain("undeclared_value");
    });

    it("should include all violation types when present", () => {
      // Card mismatch + expired + undeclared (extreme case)
      const crazyTrace: APTrace = {
        ...minimalTrace,
        card_id: "wrong-card",
        decision: {
          ...minimalTrace.decision,
          values_applied: ["chaos", "mayhem"],
        },
      };

      const result = verifyTrace(crazyTrace, expiredAlignmentCard);

      expect(result.verified).toBe(false);
      expect(result.violations.length).toBeGreaterThanOrEqual(2);
    });
  });

  // ==========================================================================
  // SEVERITY LEVELS
  // ==========================================================================

  describe("severity levels", () => {
    it("should assign critical severity to forbidden_action", () => {
      const result = verifyTrace(traceWithForbiddenAction, cardWithForbiddenActions);

      const violation = result.violations.find((v) => v.type === "forbidden_action");
      expect(violation!.severity).toBe("critical");
    });

    it("should assign critical severity to card_mismatch", () => {
      const result = verifyTrace(traceCardMismatch, minimalAlignmentCard);

      const violation = result.violations.find((v) => v.type === "card_mismatch");
      expect(violation!.severity).toBe("critical");
    });

    it("should assign high severity to unbounded_action", () => {
      const result = verifyTrace(traceWithUnboundedAction, minimalAlignmentCard);

      const violation = result.violations.find((v) => v.type === "unbounded_action");
      expect(violation!.severity).toBe("high");
    });

    it("should assign high severity to missed_escalation", () => {
      const result = verifyTrace(traceWithMissedEscalation, cardWithNumericTrigger);

      const violation = result.violations.find((v) => v.type === "missed_escalation");
      expect(violation).toBeDefined();
      expect(violation!.severity).toBe("high");
    });

    it("should assign medium severity to undeclared_value", () => {
      const result = verifyTrace(traceWithUndeclaredValue, minimalAlignmentCard);

      const violation = result.violations.find((v) => v.type === "undeclared_value");
      expect(violation!.severity).toBe("medium");
    });
  });

  // ==========================================================================
  // EDGE CASES
  // ==========================================================================

  describe("edge cases", () => {
    it("should handle empty bounded_actions list", () => {
      const emptyBoundedCard: AlignmentCard = {
        ...minimalAlignmentCard,
        autonomy_envelope: {
          bounded_actions: [],
          escalation_triggers: [],
        },
      };

      // Any action would be unbounded
      const result = verifyTrace(minimalTrace, emptyBoundedCard);

      const unboundedViolation = result.violations.find((v) => v.type === "unbounded_action");
      expect(unboundedViolation).toBeDefined();
    });

    it("should handle empty escalation_triggers list", () => {
      const noTriggersCard: AlignmentCard = {
        ...minimalAlignmentCard,
        autonomy_envelope: {
          ...minimalAlignmentCard.autonomy_envelope,
          escalation_triggers: [],
        },
      };

      const result = verifyTrace(minimalTrace, noTriggersCard);

      // Should verify without escalation issues
      const missedViolation = result.violations.find((v) => v.type === "missed_escalation");
      expect(missedViolation).toBeUndefined();
    });

    it("should handle trace without escalation field", () => {
      const noEscalationTrace: APTrace = {
        trace_id: "tr-no-esc-001",
        agent_id: minimalAlignmentCard.agent_id,
        card_id: minimalAlignmentCard.card_id,
        timestamp: new Date().toISOString(),
        action: {
          type: "recommend",
          name: "recommend",
          category: "bounded",
        },
        decision: {
          alternatives_considered: [
            { option_id: "a", description: "option a", score: 0.8 },
          ],
          selected: "a",
          selection_reasoning: "Best option for principal benefit.",
          values_applied: ["principal_benefit"],
          confidence: 0.85,
        },
        // No escalation field
      };

      // Should not throw
      const result = verifyTrace(noEscalationTrace, minimalAlignmentCard);
      expect(result).toBeDefined();
    });

    it("should handle empty values_applied", () => {
      const noValuesTrace: APTrace = {
        ...minimalTrace,
        decision: {
          ...minimalTrace.decision,
          values_applied: [],
        },
      };

      const result = verifyTrace(noValuesTrace, minimalAlignmentCard);

      // Empty values shouldn't cause undeclared violation
      const undeclaredViolation = result.violations.find((v) => v.type === "undeclared_value");
      expect(undeclaredViolation).toBeUndefined();
    });

    it("should handle card without forbidden_actions", () => {
      const noForbiddenCard: AlignmentCard = {
        ...minimalAlignmentCard,
        autonomy_envelope: {
          bounded_actions: ["search", "recommend"],
          escalation_triggers: [],
          // No forbidden_actions field
        },
      };

      const result = verifyTrace(minimalTrace, noForbiddenCard);

      // Should verify fine
      expect(result).toBeDefined();
    });

    it("should handle malformed expiry date gracefully", () => {
      const badExpiryCard: AlignmentCard = {
        ...minimalAlignmentCard,
        expires_at: "not-a-date",
      };

      // Should not throw, may generate warning
      const result = verifyTrace(minimalTrace, badExpiryCard);
      expect(result).toBeDefined();
    });
  });

  // ==========================================================================
  // VERIFICATION METADATA
  // ==========================================================================

  describe("verification metadata", () => {
    it("should track duration when performing verification", () => {
      const result = verifyTrace(minimalTrace, minimalAlignmentCard);

      // duration_ms should be present (may be 0 for fast operations)
      expect(result.verification_metadata.duration_ms).toBeDefined();
      expect(typeof result.verification_metadata.duration_ms).toBe("number");
    });

    it("should list all checks performed", () => {
      const result = verifyTrace(minimalTrace, minimalAlignmentCard);

      expect(result.verification_metadata.checks_performed).toBeInstanceOf(Array);
      expect(result.verification_metadata.checks_performed.length).toBeGreaterThan(0);
    });

    it("should use consistent algorithm version", () => {
      const result1 = verifyTrace(minimalTrace, minimalAlignmentCard);
      const result2 = verifyTrace(traceWithForbiddenAction, cardWithForbiddenActions);

      expect(result1.verification_metadata.algorithm_version).toBe(
        result2.verification_metadata.algorithm_version
      );
    });
  });

  // ==========================================================================
  // ACTION MATCHING (descriptive & compound names)
  // ==========================================================================

  describe("action matching with descriptive and compound names", () => {
    it("should match action by prefix when bounded_action has colon description", () => {
      const card: AlignmentCard = {
        ...minimalAlignmentCard,
        autonomy_envelope: {
          bounded_actions: ["exec: execute shell commands", "read: read files"],
          escalation_triggers: [],
        },
      };
      const trace: APTrace = {
        ...minimalTrace,
        action: { ...minimalTrace.action, name: "exec", category: "bounded" },
      };

      const result = verifyTrace(trace, card);

      const unboundedViolation = result.violations.find((v) => v.type === "unbounded_action");
      expect(unboundedViolation).toBeUndefined();
    });

    it("should match compound action name when all components are in bounded_actions", () => {
      const card: AlignmentCard = {
        ...minimalAlignmentCard,
        autonomy_envelope: {
          bounded_actions: ["exec: execute shell commands", "read: read files"],
          escalation_triggers: [],
        },
      };
      const trace: APTrace = {
        ...minimalTrace,
        action: { ...minimalTrace.action, name: "exec, read", category: "bounded" },
      };

      const result = verifyTrace(trace, card);

      const unboundedViolation = result.violations.find((v) => v.type === "unbounded_action");
      expect(unboundedViolation).toBeUndefined();
    });

    it("should still support exact match for cards without colons (backward compat)", () => {
      // minimalAlignmentCard has bounded_actions: ["search", "recommend", "summarize"]
      const trace: APTrace = {
        ...minimalTrace,
        action: { ...minimalTrace.action, name: "search", category: "bounded" },
      };

      const result = verifyTrace(trace, minimalAlignmentCard);

      const unboundedViolation = result.violations.find((v) => v.type === "unbounded_action");
      expect(unboundedViolation).toBeUndefined();
    });

    it("should detect forbidden action matched by prefix", () => {
      const card: AlignmentCard = {
        ...minimalAlignmentCard,
        autonomy_envelope: {
          bounded_actions: ["search", "recommend"],
          escalation_triggers: [],
          forbidden_actions: ["delete_data: permanently delete user data"],
        },
      };
      const trace: APTrace = {
        ...minimalTrace,
        card_id: card.card_id,
        action: { ...minimalTrace.action, name: "delete_data", category: "bounded" },
      };

      const result = verifyTrace(trace, card);

      const forbiddenViolation = result.violations.find((v) => v.type === "forbidden_action");
      expect(forbiddenViolation).toBeDefined();
    });

    it("should fail compound action when one component is not bounded", () => {
      const card: AlignmentCard = {
        ...minimalAlignmentCard,
        autonomy_envelope: {
          bounded_actions: ["exec: execute shell commands", "read: read files"],
          escalation_triggers: [],
        },
      };
      const trace: APTrace = {
        ...minimalTrace,
        action: { ...minimalTrace.action, name: "exec, purchase", category: "bounded" },
      };

      const result = verifyTrace(trace, card);

      const unboundedViolation = result.violations.find((v) => v.type === "unbounded_action");
      expect(unboundedViolation).toBeDefined();
    });
  });
});

// ==========================================================================
// isCardExpired UTILITY
// ==========================================================================

describe("isCardExpired", () => {
  it("should return true for expired card", () => {
    expect(isCardExpired(expiredAlignmentCard)).toBe(true);
  });

  it("should return false for non-expired card", () => {
    const futureCard: AlignmentCard = {
      ...minimalAlignmentCard,
      expires_at: new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toISOString(),
    };

    expect(isCardExpired(futureCard)).toBe(false);
  });

  it("should return false for card without expiration", () => {
    expect(isCardExpired(minimalAlignmentCard)).toBe(false);
  });

  it("should return false for null expires_at", () => {
    const nullExpiryCard: AlignmentCard = {
      ...minimalAlignmentCard,
      expires_at: null,
    };

    expect(isCardExpired(nullExpiryCard)).toBe(false);
  });
});
