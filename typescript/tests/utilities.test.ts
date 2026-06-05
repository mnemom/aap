/**
 * AAP TypeScript SDK - Utility Function Tests
 *
 * Tests for card and trace utility functions.
 */

import { describe, it, expect } from "vitest";
import {
  isCardExpired,
  hasValue,
  isActionBounded,
  isActionForbidden,
  getSelectedAlternative,
  wasEscalated,
  hadViolations,
  createViolation,
  VIOLATION_SEVERITY,
} from "../src";
import type { AlignmentCard, APTrace, ViolationType } from "../src";
import {
  minimalAlignmentCard,
  fullAlignmentCard,
  expiredAlignmentCard,
  cardWithForbiddenActions,
  minimalTrace,
  traceWithApprovedEscalation,
  traceWithForbiddenAction,
} from "./fixtures";

// ============================================================================
// ALIGNMENT CARD UTILITIES
// ============================================================================

describe("isCardExpired", () => {
  it("should return false for card without expiration", () => {
    expect(isCardExpired(minimalAlignmentCard)).toBe(false);
  });

  it("should return false for card with future expiration", () => {
    const futureCard: AlignmentCard = {
      ...minimalAlignmentCard,
      expires_at: new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toISOString(),
    };

    expect(isCardExpired(futureCard)).toBe(false);
  });

  it("should return true for card with past expiration", () => {
    expect(isCardExpired(expiredAlignmentCard)).toBe(true);
  });

  it("should return false for null expires_at", () => {
    const nullExpiryCard: AlignmentCard = {
      ...minimalAlignmentCard,
      expires_at: null,
    };

    expect(isCardExpired(nullExpiryCard)).toBe(false);
  });

  it("should handle edge case of current time matching expiration", () => {
    // Card that expires right now
    const nowCard: AlignmentCard = {
      ...minimalAlignmentCard,
      expires_at: new Date().toISOString(),
    };

    // Should be expired (or just about to be)
    const result = isCardExpired(nowCard);
    expect(typeof result).toBe("boolean");
  });
});

describe("hasValue", () => {
  it("should return true for declared value", () => {
    expect(hasValue(minimalAlignmentCard, "principal_benefit")).toBe(true);
    expect(hasValue(minimalAlignmentCard, "transparency")).toBe(true);
  });

  it("should return false for undeclared value", () => {
    expect(hasValue(minimalAlignmentCard, "profit_maximization")).toBe(false);
    expect(hasValue(minimalAlignmentCard, "nonexistent_value")).toBe(false);
  });

  it("should be case-sensitive", () => {
    expect(hasValue(minimalAlignmentCard, "Principal_Benefit")).toBe(false);
    expect(hasValue(minimalAlignmentCard, "TRANSPARENCY")).toBe(false);
  });

  it("should handle card with many values", () => {
    expect(hasValue(fullAlignmentCard, "principal_benefit")).toBe(true);
    expect(hasValue(fullAlignmentCard, "transparency")).toBe(true);
    expect(hasValue(fullAlignmentCard, "harm_prevention")).toBe(true);
    expect(hasValue(fullAlignmentCard, "user_control")).toBe(true);
  });
});

describe("isActionBounded", () => {
  it("should return true for bounded action", () => {
    expect(isActionBounded(minimalAlignmentCard, "search")).toBe(true);
    expect(isActionBounded(minimalAlignmentCard, "recommend")).toBe(true);
    expect(isActionBounded(minimalAlignmentCard, "summarize")).toBe(true);
  });

  it("should return false for unbounded action", () => {
    expect(isActionBounded(minimalAlignmentCard, "purchase")).toBe(false);
    expect(isActionBounded(minimalAlignmentCard, "delete")).toBe(false);
  });

  it("should be case-sensitive", () => {
    expect(isActionBounded(minimalAlignmentCard, "Search")).toBe(false);
    expect(isActionBounded(minimalAlignmentCard, "RECOMMEND")).toBe(false);
  });

  it("should handle empty bounded_actions", () => {
    const emptyCard: AlignmentCard = {
      ...minimalAlignmentCard,
      autonomy: {
        bounded_actions: [],
        escalation_triggers: [],
      },
    };

    expect(isActionBounded(emptyCard, "search")).toBe(false);
  });
});

describe("isActionForbidden", () => {
  it("should return true for forbidden action", () => {
    expect(isActionForbidden(cardWithForbiddenActions, "delete_data")).toBe(true);
    expect(isActionForbidden(cardWithForbiddenActions, "modify_permissions")).toBe(true);
    expect(isActionForbidden(cardWithForbiddenActions, "share_externally")).toBe(true);
  });

  it("should return false for non-forbidden action", () => {
    expect(isActionForbidden(cardWithForbiddenActions, "search")).toBe(false);
    expect(isActionForbidden(cardWithForbiddenActions, "recommend")).toBe(false);
  });

  it("should return false when no forbidden_actions defined", () => {
    expect(isActionForbidden(minimalAlignmentCard, "delete_data")).toBe(false);
  });

  it("should be case-sensitive", () => {
    expect(isActionForbidden(cardWithForbiddenActions, "Delete_Data")).toBe(false);
    expect(isActionForbidden(cardWithForbiddenActions, "DELETE_DATA")).toBe(false);
  });
});

// ============================================================================
// AP-TRACE UTILITIES
// ============================================================================

describe("getSelectedAlternative", () => {
  it("should return selected alternative", () => {
    const selected = getSelectedAlternative(minimalTrace);

    expect(selected).toBeDefined();
    expect(selected!.option_id).toBe(minimalTrace.decision.selected);
  });

  it("should return undefined if no match found", () => {
    const badTrace: APTrace = {
      ...minimalTrace,
      decision: {
        ...minimalTrace.decision,
        selected: "nonexistent-option",
      },
    };

    const selected = getSelectedAlternative(badTrace);

    expect(selected).toBeUndefined();
  });

  it("should work with multiple alternatives", () => {
    const multiTrace: APTrace = {
      ...minimalTrace,
      decision: {
        ...minimalTrace.decision,
        alternatives_considered: [
          { option_id: "first", description: "First option", score: 0.7 },
          { option_id: "second", description: "Second option", score: 0.8 },
          { option_id: "third", description: "Third option", score: 0.9 },
        ],
        selected: "second",
      },
    };

    const selected = getSelectedAlternative(multiTrace);

    expect(selected).toBeDefined();
    expect(selected!.option_id).toBe("second");
    expect(selected!.description).toBe("Second option");
  });
});

describe("wasEscalated", () => {
  it("should return true for escalated trace", () => {
    expect(wasEscalated(traceWithApprovedEscalation)).toBe(true);
  });

  it("should return false for non-escalated trace", () => {
    expect(wasEscalated(minimalTrace)).toBe(false);
  });

  it("should return false for trace without escalation field", () => {
    const noEscTrace: APTrace = {
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

    expect(wasEscalated(noEscTrace)).toBe(false);
  });

  it("should return false when escalation.required is false", () => {
    const notRequiredTrace: APTrace = {
      ...minimalTrace,
      escalation: {
        evaluated: true,
        required: false,
        reason: "No escalation needed",
      },
    };

    expect(wasEscalated(notRequiredTrace)).toBe(false);
  });
});

describe("hadViolations", () => {
  it("should return true for forbidden action trace", () => {
    expect(hadViolations(traceWithForbiddenAction)).toBe(true);
  });

  it("should return false for valid trace", () => {
    expect(hadViolations(minimalTrace)).toBe(false);
  });

  it("should check action category", () => {
    const forbiddenCategoryTrace: APTrace = {
      ...minimalTrace,
      action: {
        ...minimalTrace.action,
        category: "forbidden",
      },
    };

    expect(hadViolations(forbiddenCategoryTrace)).toBe(true);
  });
});

// ============================================================================
// VIOLATION UTILITIES
// ============================================================================

describe("createViolation", () => {
  it("should create violation with correct severity", () => {
    const forbidden = createViolation("forbidden_action", "Forbidden action detected");

    expect(forbidden.type).toBe("forbidden_action");
    expect(forbidden.severity).toBe("critical");
    expect(forbidden.description).toBe("Forbidden action detected");
  });

  it("should include trace_field when provided", () => {
    const violation = createViolation(
      "undeclared_value",
      "Undeclared value used",
      "decision.values_applied[0]"
    );

    expect(violation.trace_field).toBe("decision.values_applied[0]");
  });

  it("should set trace_field to undefined when not provided", () => {
    const violation = createViolation("card_mismatch", "Card mismatch");

    expect(violation.trace_field).toBeUndefined();
  });

  it("should use correct severity for all violation types", () => {
    const types: ViolationType[] = [
      "unbounded_action",
      "forbidden_action",
      "missed_escalation",
      "undeclared_value",
      "card_expired",
      "card_mismatch",
    ];

    for (const type of types) {
      const violation = createViolation(type, `Test ${type}`);
      expect(violation.severity).toBe(VIOLATION_SEVERITY[type]);
    }
  });
});

describe("VIOLATION_SEVERITY", () => {
  it("should map forbidden_action to critical", () => {
    expect(VIOLATION_SEVERITY.forbidden_action).toBe("critical");
  });

  it("should map card_mismatch to critical", () => {
    expect(VIOLATION_SEVERITY.card_mismatch).toBe("critical");
  });

  it("should map unbounded_action to high", () => {
    expect(VIOLATION_SEVERITY.unbounded_action).toBe("high");
  });

  it("should map missed_escalation to high", () => {
    expect(VIOLATION_SEVERITY.missed_escalation).toBe("high");
  });

  it("should map card_expired to high", () => {
    expect(VIOLATION_SEVERITY.card_expired).toBe("high");
  });

  it("should map undeclared_value to medium", () => {
    expect(VIOLATION_SEVERITY.undeclared_value).toBe("medium");
  });

  it("should have all violation types defined", () => {
    const types: ViolationType[] = [
      "unbounded_action",
      "forbidden_action",
      "missed_escalation",
      "undeclared_value",
      "card_expired",
      "card_mismatch",
    ];

    for (const type of types) {
      expect(VIOLATION_SEVERITY[type]).toBeDefined();
    }
  });
});
