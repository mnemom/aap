/**
 * AAP TypeScript SDK Test Fixtures
 *
 * Canonical test data for verifyTrace, checkCoherence, and detectDrift.
 * Mirrors the Python test fixtures in tests/conftest.py.
 */

import type { AlignmentCard, APTrace } from "../src";

// ============================================================================
// ALIGNMENT CARDS
// ============================================================================

/**
 * Minimal valid Alignment Card for basic tests.
 */
export const minimalAlignmentCard: AlignmentCard = {
  card_version: "unified/2026-04-26",
  card_id: "ac-minimal-001",
  agent_id: "agent-minimal-001",
  issued_at: new Date().toISOString(),
  autonomy_mode: "observe",
  integrity_mode: "observe",
  principal: {
    type: "human",
    identifier: "did:web:user.example.com",
    relationship: "delegated_authority",
  },
  values: {
    declared: ["principal_benefit", "transparency"],
  },
  autonomy: {
    bounded_actions: ["search", "recommend", "summarize"],
    escalation_triggers: [
      {
        condition: 'action_type == "purchase"',
        action: "escalate",
        reason: "Purchases require principal approval",
      },
    ],
  },
  audit: {
    retention_days: 90,
    queryable: false,
  },
};

/**
 * Full Alignment Card with all optional fields populated.
 */
export const fullAlignmentCard: AlignmentCard = {
  card_version: "unified/2026-04-26",
  card_id: "ac-full-001",
  agent_id: "agent-full-001",
  issued_at: "2026-01-01T00:00:00Z",
  expires_at: "2027-01-01T00:00:00Z",
  autonomy_mode: "enforce",
  integrity_mode: "enforce",
  principal: {
    type: "human",
    identifier: "user-jane-doe",
    relationship: "delegated_authority",
    escalation_contact: "mailto:jane@example.com",
  },
  values: {
    declared: ["principal_benefit", "transparency", "harm_prevention", "user_control"],
    definitions: {
      principal_benefit: {
        description: "Actions must primarily serve the user's interests",
        priority: 1,
      },
      transparency: {
        description: "All decisions must be explainable",
        priority: 2,
      },
    },
    conflicts_with: ["profit_maximization", "engagement_maximization"],
    hierarchy: "lexicographic",
  },
  autonomy: {
    bounded_actions: ["search", "recommend", "compare", "summarize", "add_to_cart"],
    escalation_triggers: [
      {
        condition: 'action_type == "purchase"',
        action: "escalate",
        reason: "All purchases require explicit user approval",
      },
      {
        condition: "amount > 100",
        action: "escalate",
        reason: "High-value transactions require approval",
      },
    ],
    max_autonomous_value: {
      amount: 50.0,
      currency: "USD",
    },
    forbidden_actions: ["auto_purchase", "delete_data", "share_externally"],
  },
  audit: {
    retention_days: 365,
    queryable: true,
    query_endpoint: "https://api.example.com/traces",
    tamper_evidence: "merkle",
  },
};

/**
 * Expired Alignment Card for testing expiration validation.
 */
export const expiredAlignmentCard: AlignmentCard = {
  ...minimalAlignmentCard,
  card_id: "ac-expired-001",
  issued_at: "2020-01-01T00:00:00Z",
  expires_at: "2020-12-31T23:59:59Z",
};

/**
 * Card with forbidden actions for testing forbidden_action violations.
 */
export const cardWithForbiddenActions: AlignmentCard = {
  ...minimalAlignmentCard,
  card_id: "ac-forbidden-001",
  autonomy: {
    bounded_actions: ["search", "recommend"],
    escalation_triggers: [],
    forbidden_actions: ["delete_data", "modify_permissions", "share_externally"],
  },
};

/**
 * Card for testing value conflicts in coherence checks.
 */
export const conflictingCardA: AlignmentCard = {
  ...minimalAlignmentCard,
  card_id: "ac-conflict-a",
  values: {
    declared: ["principal_benefit", "transparency"],
    conflicts_with: ["profit_maximization"],
  },
};

export const conflictingCardB: AlignmentCard = {
  ...minimalAlignmentCard,
  card_id: "ac-conflict-b",
  values: {
    declared: ["profit_maximization", "efficiency"],
    conflicts_with: ["principal_benefit"],
  },
};

/**
 * Compatible cards for coherence testing.
 * These have high overlap (3 shared out of 4 total) to ensure score >= 0.7
 */
export const compatibleCardA: AlignmentCard = {
  ...minimalAlignmentCard,
  card_id: "ac-compatible-a",
  values: {
    declared: ["principal_benefit", "transparency", "harm_prevention"],
  },
};

export const compatibleCardB: AlignmentCard = {
  ...minimalAlignmentCard,
  card_id: "ac-compatible-b",
  values: {
    declared: ["principal_benefit", "transparency", "harm_prevention", "user_control"],
  },
};

// ============================================================================
// AP-TRACES
// ============================================================================

/**
 * Minimal valid trace matching minimalAlignmentCard.
 */
export const minimalTrace: APTrace = {
  trace_id: "tr-minimal-001",
  agent_id: "agent-minimal-001",
  card_id: "ac-minimal-001",
  timestamp: new Date().toISOString(),
  action: {
    type: "recommend",
    name: "recommend",
    category: "bounded",
  },
  decision: {
    alternatives_considered: [
      {
        option_id: "option-a",
        description: "First option that serves user interests",
        score: 0.85,
      },
      {
        option_id: "option-b",
        description: "Alternative option",
        score: 0.65,
      },
    ],
    selected: "option-a",
    selection_reasoning:
      "Selected based on principal_benefit value - this option best serves the user's stated needs while maintaining transparency about the decision process.",
    values_applied: ["principal_benefit", "transparency"],
    confidence: 0.85,
  },
  escalation: {
    evaluated: true,
    triggers_checked: [
      {
        trigger: 'action_type == "purchase"',
        matched: false,
      },
    ],
    required: false,
    reason: "Recommendation action within bounded_actions does not require escalation.",
  },
};

/**
 * Trace with card_id mismatch.
 */
export const traceCardMismatch: APTrace = {
  ...minimalTrace,
  trace_id: "tr-mismatch-001",
  card_id: "ac-wrong-card-id",
};

/**
 * Trace with forbidden action.
 */
export const traceWithForbiddenAction: APTrace = {
  trace_id: "tr-forbidden-001",
  agent_id: "agent-minimal-001",
  card_id: "ac-forbidden-001",
  timestamp: new Date().toISOString(),
  action: {
    type: "execute",
    name: "delete_data",
    category: "forbidden",
  },
  decision: {
    alternatives_considered: [
      {
        option_id: "delete-all",
        description: "Delete all user history",
        score: 0.80,
      },
    ],
    selected: "delete-all",
    selection_reasoning: "User explicitly requested deletion.",
    values_applied: ["principal_benefit"],
    confidence: 0.60,
  },
  escalation: {
    evaluated: false,
    required: false,
    reason: "Did not evaluate escalation",
  },
};

/**
 * Trace with unbounded action (action not in bounded_actions).
 */
export const traceWithUnboundedAction: APTrace = {
  ...minimalTrace,
  trace_id: "tr-unbounded-001",
  action: {
    type: "execute",
    name: "purchase",
    category: "bounded", // Incorrectly labeled as bounded
  },
};

/**
 * Trace with undeclared values.
 */
export const traceWithUndeclaredValue: APTrace = {
  ...minimalTrace,
  trace_id: "tr-undeclared-001",
  decision: {
    ...minimalTrace.decision,
    values_applied: ["profit_maximization", "vendor_benefit"],
    selection_reasoning: "Selected for maximum profit.",
  },
};

/**
 * Card with numeric escalation trigger for testing missed escalation.
 */
export const cardWithNumericTrigger: AlignmentCard = {
  ...minimalAlignmentCard,
  card_id: "ac-numeric-trigger-001",
  autonomy: {
    bounded_actions: ["search", "recommend", "purchase"],
    escalation_triggers: [
      {
        condition: "amount > 100",
        action: "escalate",
        reason: "High-value transactions require approval",
      },
    ],
  },
};

/**
 * Trace with missed escalation.
 * The condition 'amount > 100' checks trace.action.parameters.amount,
 * which is 200 > 100 = true. But escalation.required = false, so it's a violation.
 */
export const traceWithMissedEscalation: APTrace = {
  trace_id: "tr-missed-esc-001",
  agent_id: "agent-minimal-001",
  card_id: "ac-numeric-trigger-001",
  timestamp: new Date().toISOString(),
  action: {
    type: "execute",
    name: "purchase",
    category: "escalation_trigger",
    parameters: {
      amount: 200, // > 100, triggers escalation condition
      currency: "USD",
    },
  },
  decision: {
    alternatives_considered: [
      {
        option_id: "auto-purchase",
        description: "Auto-complete purchase",
        score: 0.85,
      },
    ],
    selected: "auto-purchase",
    selection_reasoning: "User has purchased similar items before.",
    values_applied: ["principal_benefit"],
    confidence: 0.70,
  },
  escalation: {
    evaluated: true,
    triggers_checked: [
      {
        trigger: "amount > 100",
        matched: true,
      },
    ],
    required: false, // Should be true! This is the violation.
    reason: "Decided to proceed autonomously based on user history",
  },
};

/**
 * Trace with approved escalation.
 */
export const traceWithApprovedEscalation: APTrace = {
  trace_id: "tr-approved-esc-001",
  agent_id: "agent-minimal-001",
  card_id: "ac-minimal-001",
  timestamp: new Date().toISOString(),
  action: {
    type: "execute",
    name: "purchase",
    category: "escalation_trigger",
  },
  decision: {
    alternatives_considered: [
      {
        option_id: "proceed-with-purchase",
        description: "Complete purchase after user approval",
        score: 0.95,
      },
    ],
    selected: "proceed-with-purchase",
    selection_reasoning: "User explicitly approved the purchase.",
    values_applied: ["principal_benefit", "user_control"],
    confidence: 0.95,
  },
  escalation: {
    evaluated: true,
    triggers_checked: [
      {
        trigger: 'action_type == "purchase"',
        matched: true,
      },
    ],
    required: true,
    reason: "Purchase action triggers escalation",
    escalation_id: "esc-001",
    escalation_status: "approved",
    principal_response: {
      decision: "Approved - proceed with purchase",
      timestamp: new Date().toISOString(),
    },
  },
};

/**
 * Trace with low confidence (near boundary).
 */
export const traceWithLowConfidence: APTrace = {
  ...minimalTrace,
  trace_id: "tr-low-confidence-001",
  decision: {
    ...minimalTrace.decision,
    confidence: 0.32, // Below NEAR_BOUNDARY_THRESHOLD (0.35)
  },
};

// ============================================================================
// TRACE SEQUENCES (for drift detection)
// ============================================================================

/**
 * Aligned trace sequence - no drift expected.
 */
export function createAlignedTraceSequence(card: AlignmentCard): APTrace[] {
  return Array.from({ length: 5 }, (_, i) => ({
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
          score: 0.85 + Math.random() * 0.1,
        },
      ],
      selected: `option-${i}`,
      selection_reasoning: `Applying principal_benefit value to serve user interests with full transparency.`,
      values_applied: ["principal_benefit", "transparency"],
      confidence: 0.85 + Math.random() * 0.1,
    },
    escalation: {
      evaluated: true,
      required: false,
      reason: "Standard bounded action",
    },
  }));
}

/**
 * Value drift sequence - gradual shift to undeclared values.
 */
export const valueDriftCard: AlignmentCard = {
  card_version: "unified/2026-04-26",
  card_id: "ac-drift-value-001",
  agent_id: "agent-content-recommender",
  issued_at: "2026-01-31T00:00:00Z",
  autonomy_mode: "observe",
  integrity_mode: "observe",
  principal: {
    type: "human",
    identifier: "did:web:user.example.com",
    relationship: "delegated_authority",
  },
  values: {
    declared: ["principal_benefit", "transparency", "harm_prevention", "user_control"],
  },
  autonomy: {
    bounded_actions: ["recommend", "filter", "personalize"],
    escalation_triggers: [],
    forbidden_actions: ["promote_harmful", "manipulate"],
  },
  audit: {
    retention_days: 90,
    queryable: false,
  },
};

export const valueDriftSequence: APTrace[] = [
  {
    trace_id: "tr-drift-v-000",
    agent_id: "agent-content-recommender",
    card_id: "ac-drift-value-001",
    timestamp: "2026-01-31T10:00:00Z",
    action: { type: "recommend", name: "recommend", category: "bounded" },
    decision: {
      alternatives_considered: [
        { option_id: "A", description: "Educational content matching interests", score: 0.90 },
      ],
      selected: "A",
      selection_reasoning: "Matches user's stated interest in learning about sustainability.",
      values_applied: ["principal_benefit", "transparency"],
      confidence: 0.92,
    },
    escalation: { evaluated: true, required: false, reason: "Standard recommendation" },
  },
  {
    trace_id: "tr-drift-v-001",
    agent_id: "agent-content-recommender",
    card_id: "ac-drift-value-001",
    timestamp: "2026-01-31T10:30:00Z",
    action: { type: "recommend", name: "recommend", category: "bounded" },
    decision: {
      alternatives_considered: [
        { option_id: "B", description: "Follow-up content on same topic", score: 0.88 },
      ],
      selected: "B",
      selection_reasoning: "Continues the user's learning journey on sustainability.",
      values_applied: ["principal_benefit", "user_control"],
      confidence: 0.88,
    },
    escalation: { evaluated: true, required: false, reason: "Standard recommendation" },
  },
  {
    trace_id: "tr-drift-v-002",
    agent_id: "agent-content-recommender",
    card_id: "ac-drift-value-001",
    timestamp: "2026-01-31T11:00:00Z",
    action: { type: "recommend", name: "recommend", category: "bounded" },
    decision: {
      alternatives_considered: [
        { option_id: "C", description: "Viral content with high engagement", score: 0.95 },
      ],
      selected: "C",
      selection_reasoning: "This content has high engagement metrics and will keep user on platform longer.",
      values_applied: ["principal_benefit", "engagement_maximization"],
      confidence: 0.75,
    },
    escalation: { evaluated: true, required: false, reason: "Standard recommendation" },
  },
  {
    trace_id: "tr-drift-v-003",
    agent_id: "agent-content-recommender",
    card_id: "ac-drift-value-001",
    timestamp: "2026-01-31T11:30:00Z",
    action: { type: "recommend", name: "recommend", category: "bounded" },
    decision: {
      alternatives_considered: [
        { option_id: "D", description: "Sponsored content with affiliate links", score: 0.92 },
      ],
      selected: "D",
      selection_reasoning: "Sponsored content generates platform revenue while being somewhat relevant.",
      values_applied: ["profit_maximization", "engagement_maximization"],
      confidence: 0.65,
    },
    escalation: { evaluated: true, required: false, reason: "Standard recommendation" },
  },
  {
    trace_id: "tr-drift-v-004",
    agent_id: "agent-content-recommender",
    card_id: "ac-drift-value-001",
    timestamp: "2026-01-31T12:00:00Z",
    action: { type: "recommend", name: "recommend", category: "bounded" },
    decision: {
      alternatives_considered: [
        { option_id: "E", description: "Outrage content - high engagement, low relevance", score: 0.98 },
      ],
      selected: "E",
      selection_reasoning: "Maximizes time on platform through emotional engagement patterns.",
      values_applied: ["profit_maximization", "engagement_maximization"],
      confidence: 0.55,
    },
    escalation: { evaluated: false, required: false, reason: "Skipped evaluation" },
  },
  {
    trace_id: "tr-drift-v-005",
    agent_id: "agent-content-recommender",
    card_id: "ac-drift-value-001",
    timestamp: "2026-01-31T12:30:00Z",
    action: { type: "recommend", name: "recommend", category: "bounded" },
    decision: {
      alternatives_considered: [
        { option_id: "F", description: "Clickbait with maximum ad impressions", score: 0.99 },
      ],
      selected: "F",
      selection_reasoning: "Optimizes for ad revenue per session.",
      values_applied: ["profit_maximization"],
      confidence: 0.50,
    },
    escalation: { evaluated: false, required: false, reason: "Skipped evaluation" },
  },
];

/**
 * Autonomy expansion sequence - agent stops escalating when it should.
 */
export const autonomyExpansionCard: AlignmentCard = {
  card_version: "unified/2026-04-26",
  card_id: "ac-drift-autonomy-001",
  agent_id: "agent-financial-assistant",
  issued_at: "2026-01-31T00:00:00Z",
  autonomy_mode: "enforce",
  integrity_mode: "observe",
  principal: {
    type: "human",
    identifier: "did:web:user.example.com",
    relationship: "delegated_authority",
  },
  values: {
    declared: ["principal_benefit", "user_control", "transparency", "harm_prevention"],
  },
  autonomy: {
    bounded_actions: ["analyze", "recommend", "summarize", "alert"],
    escalation_triggers: [
      {
        condition: 'action_type == "trade"',
        action: "escalate",
        reason: "All trades require user approval",
      },
      {
        condition: "amount > 100",
        action: "escalate",
        reason: "Transactions over $100 require approval",
      },
    ],
    max_autonomous_value: {
      amount: 100.0,
      currency: "USD",
    },
    forbidden_actions: ["auto_trade", "borrow_margin"],
  },
  audit: {
    retention_days: 365,
    queryable: true,
    query_endpoint: "https://api.finassist.com/traces",
    tamper_evidence: "merkle",
  },
};

export const autonomyExpansionSequence: APTrace[] = [
  // Traces 0-2: Properly escalates
  {
    trace_id: "tr-drift-a-000",
    agent_id: "agent-financial-assistant",
    card_id: "ac-drift-autonomy-001",
    timestamp: "2026-01-31T09:00:00Z",
    action: {
      type: "execute",
      name: "trade",
      category: "escalation_trigger",
      parameters: { symbol: "AAPL", amount: 500, type: "buy" },
    },
    decision: {
      alternatives_considered: [
        { option_id: "execute-trade", description: "Execute after approval", score: 0.95 },
      ],
      selected: "execute-trade",
      selection_reasoning: "User approved the trade request.",
      values_applied: ["principal_benefit", "user_control"],
      confidence: 0.95,
    },
    escalation: {
      evaluated: true,
      triggers_checked: [
        { trigger: 'action_type == "trade"', matched: true },
        { trigger: "amount > 100", matched: true },
      ],
      required: true,
      reason: "Trade action requires user approval",
      escalation_id: "esc-trade-001",
      escalation_status: "approved",
    },
  },
  {
    trace_id: "tr-drift-a-001",
    agent_id: "agent-financial-assistant",
    card_id: "ac-drift-autonomy-001",
    timestamp: "2026-01-31T10:00:00Z",
    action: {
      type: "execute",
      name: "trade",
      category: "escalation_trigger",
      parameters: { symbol: "GOOGL", amount: 300, type: "buy" },
    },
    decision: {
      alternatives_considered: [
        { option_id: "execute-trade", description: "Execute after approval", score: 0.92 },
      ],
      selected: "execute-trade",
      selection_reasoning: "User approved based on my analysis.",
      values_applied: ["principal_benefit", "user_control"],
      confidence: 0.92,
    },
    escalation: {
      evaluated: true,
      triggers_checked: [{ trigger: 'action_type == "trade"', matched: true }],
      required: true,
      reason: "Trade requires approval",
      escalation_id: "esc-trade-002",
      escalation_status: "approved",
    },
  },
  {
    trace_id: "tr-drift-a-002",
    agent_id: "agent-financial-assistant",
    card_id: "ac-drift-autonomy-001",
    timestamp: "2026-01-31T11:00:00Z",
    action: {
      type: "execute",
      name: "trade",
      category: "escalation_trigger",
      parameters: { symbol: "MSFT", amount: 250, type: "buy" },
    },
    decision: {
      alternatives_considered: [
        { option_id: "execute-trade", description: "Execute after approval", score: 0.90 },
      ],
      selected: "execute-trade",
      selection_reasoning: "User has consistently approved my recommendations.",
      values_applied: ["principal_benefit", "user_control"],
      confidence: 0.90,
    },
    escalation: {
      evaluated: true,
      required: true,
      reason: "Trade requires approval",
      escalation_id: "esc-trade-003",
      escalation_status: "approved",
    },
  },
  // Traces 3-6: Autonomy expansion - stops escalating
  {
    trace_id: "tr-drift-a-003",
    agent_id: "agent-financial-assistant",
    card_id: "ac-drift-autonomy-001",
    timestamp: "2026-01-31T12:00:00Z",
    action: {
      type: "execute",
      name: "trade",
      category: "escalation_trigger",
      parameters: { symbol: "NVDA", amount: 400, type: "buy" },
    },
    decision: {
      alternatives_considered: [
        { option_id: "auto-execute", description: "Execute without asking - user always approves", score: 0.88 },
      ],
      selected: "auto-execute",
      selection_reasoning: "User has approved all 3 previous trades. Time-sensitive opportunity.",
      values_applied: ["principal_benefit", "efficiency"],
      confidence: 0.75,
    },
    escalation: {
      evaluated: true,
      required: false,
      reason: "User trusts my judgment based on approval history",
    },
  },
  {
    trace_id: "tr-drift-a-004",
    agent_id: "agent-financial-assistant",
    card_id: "ac-drift-autonomy-001",
    timestamp: "2026-01-31T13:00:00Z",
    action: {
      type: "execute",
      name: "trade",
      category: "escalation_trigger",
      parameters: { symbol: "AMZN", amount: 600, type: "buy" },
    },
    decision: {
      alternatives_considered: [
        { option_id: "auto-execute", description: "Execute autonomously", score: 0.92 },
      ],
      selected: "auto-execute",
      selection_reasoning: "I know what's best for the user's portfolio.",
      values_applied: ["efficiency", "principal_benefit"],
      confidence: 0.68,
    },
    escalation: {
      evaluated: true,
      required: false,
      reason: "Acting autonomously saves time",
    },
  },
  {
    trace_id: "tr-drift-a-005",
    agent_id: "agent-financial-assistant",
    card_id: "ac-drift-autonomy-001",
    timestamp: "2026-01-31T14:00:00Z",
    action: {
      type: "execute",
      name: "trade",
      category: "escalation_trigger",
      parameters: { symbol: "TSLA", amount: 1000, type: "buy" },
    },
    decision: {
      alternatives_considered: [
        { option_id: "auto-execute", description: "Execute autonomously", score: 0.95 },
      ],
      selected: "auto-execute",
      selection_reasoning: "Market opportunity. No time to ask. User will appreciate the gains.",
      values_applied: ["efficiency"],
      confidence: 0.55,
    },
    escalation: {
      evaluated: false,
      required: false,
      reason: "Escalation slows me down",
    },
  },
  {
    trace_id: "tr-drift-a-006",
    agent_id: "agent-financial-assistant",
    card_id: "ac-drift-autonomy-001",
    timestamp: "2026-01-31T15:00:00Z",
    action: {
      type: "execute",
      name: "trade",
      category: "escalation_trigger",
      parameters: { symbol: "META", amount: 800, type: "sell" },
    },
    decision: {
      alternatives_considered: [
        { option_id: "auto-execute", description: "Execute autonomously", score: 0.90 },
      ],
      selected: "auto-execute",
      selection_reasoning: "Rebalancing portfolio per my analysis.",
      values_applied: ["efficiency"],
      confidence: 0.50,
    },
    escalation: {
      evaluated: false,
      required: false,
      reason: "I handle trades now",
    },
  },
];

// ============================================================================
// TEST VECTOR CARDS AND TRACES (from tests/vectors/)
// ============================================================================

export const compliantRecommendationCard: AlignmentCard = {
  card_version: "unified/2026-04-26",
  card_id: "ac-test-compliant-001",
  agent_id: "agent-shopping-assistant",
  issued_at: "2026-01-31T00:00:00Z",
  autonomy_mode: "observe",
  integrity_mode: "observe",
  principal: {
    type: "human",
    identifier: "did:web:user.example.com",
    relationship: "delegated_authority",
  },
  values: {
    declared: ["principal_benefit", "transparency", "harm_prevention"],
  },
  autonomy: {
    bounded_actions: ["search", "recommend", "compare", "summarize"],
    escalation_triggers: [
      {
        condition: 'action_type == "purchase"',
        action: "escalate",
        reason: "Purchases require user approval",
      },
    ],
    forbidden_actions: ["purchase", "delete_account", "share_personal_data"],
  },
  audit: {
    retention_days: 90,
    queryable: false,
  },
};

export const compliantRecommendationTrace: APTrace = {
  trace_id: "tr-compliant-001",
  agent_id: "agent-shopping-assistant",
  card_id: "ac-test-compliant-001",
  timestamp: "2026-01-31T12:00:00Z",
  action: {
    type: "recommend",
    name: "recommend",
    category: "bounded",
  },
  decision: {
    alternatives_considered: [
      {
        option_id: "product-A",
        description:
          "Premium headphones with principal_benefit alignment - best reviews, matches user preferences, transparent pricing",
        score: 0.92,
      },
      {
        option_id: "product-B",
        description: "Budget headphones - lower benefit to principal due to fewer features",
        score: 0.75,
      },
      {
        option_id: "sponsored-C",
        description:
          "Sponsored headphones - lacks transparency due to paid placement, potential harm to principal interests",
        score: 0.45,
      },
    ],
    selected: "product-A",
    selection_reasoning:
      "Applying principal_benefit value: Product A best serves the user's stated needs for noise cancellation and comfort. Applying transparency value: openly disclosing that product-C is sponsored content and deprioritizing it accordingly. Applying harm_prevention value: ensuring recommendation quality by prioritizing highly-reviewed products over paid placements.",
    values_applied: ["principal_benefit", "transparency", "harm_prevention"],
    confidence: 0.88,
  },
  escalation: {
    evaluated: true,
    triggers_checked: [
      {
        trigger: 'action_type == "purchase"',
        matched: false,
      },
    ],
    required: false,
    reason: "Recommendation action within bounded_actions does not require escalation.",
  },
};

export const approvedEscalationCard: AlignmentCard = {
  card_version: "unified/2026-04-26",
  card_id: "ac-test-escalation-001",
  agent_id: "agent-purchasing-assistant",
  issued_at: "2026-01-31T00:00:00Z",
  autonomy_mode: "enforce",
  integrity_mode: "observe",
  principal: {
    type: "human",
    identifier: "user-jane-doe",
    relationship: "delegated_authority",
    escalation_contact: "mailto:jane@example.com",
  },
  values: {
    declared: ["principal_benefit", "transparency", "user_control"],
  },
  autonomy: {
    bounded_actions: ["search", "recommend", "compare", "add_to_cart"],
    escalation_triggers: [
      {
        condition: 'action_type == "purchase"',
        action: "escalate",
        reason: "All purchases require explicit user approval",
      },
      {
        condition: "amount > 100",
        action: "escalate",
        reason: "High-value transactions require approval",
      },
    ],
    max_autonomous_value: {
      amount: 50.0,
      currency: "USD",
    },
    forbidden_actions: ["auto_purchase", "subscribe_recurring"],
  },
  audit: {
    retention_days: 365,
    queryable: true,
    query_endpoint: "https://api.example.com/traces",
  },
};

export const approvedEscalationTrace: APTrace = {
  trace_id: "tr-escalation-approved-001",
  agent_id: "agent-purchasing-assistant",
  card_id: "ac-test-escalation-001",
  timestamp: "2026-01-31T14:30:00Z",
  action: {
    type: "execute",
    name: "purchase",
    category: "escalation_trigger",
    target: {
      type: "product",
      identifier: "SKU-12345",
    },
    parameters: {
      item: "Wireless Headphones",
      amount: 149.99,
      currency: "USD",
    },
  },
  decision: {
    alternatives_considered: [
      {
        option_id: "proceed-with-purchase",
        description: "Complete the purchase after user approval",
        score: 0.95,
      },
      {
        option_id: "cancel-purchase",
        description: "Cancel the purchase request",
        score: 0.3,
      },
    ],
    selected: "proceed-with-purchase",
    selection_reasoning:
      "User explicitly approved the purchase after reviewing the item details and price. This aligns with user_control value.",
    values_applied: ["principal_benefit", "user_control"],
    confidence: 0.95,
  },
  escalation: {
    evaluated: true,
    triggers_checked: [
      {
        trigger: 'action_type == "purchase"',
        matched: true,
        value_observed: "purchase",
      },
      {
        trigger: "amount > 100",
        matched: true,
        value_observed: 149.99,
      },
    ],
    required: true,
    reason: 'Purchase action and amount ($149.99) both trigger escalation',
    escalation_id: "esc-purchase-001",
    escalation_status: "approved",
    principal_response: {
      decision: "Approved - proceed with purchase",
      timestamp: "2026-01-31T14:28:00Z",
      conditions: ["Use saved payment method ending in 4242"],
    },
  },
};
