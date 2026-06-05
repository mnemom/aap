/**
 * A2A + AAP Integration Example — Two agents coordinating with value coherence.
 *
 * This example demonstrates:
 * 1. Creating A2A Agent Cards extended with AAP alignment blocks
 * 2. Performing value coherence checks before delegation
 * 3. Handling value conflicts appropriately
 * 4. Generating AP-Traces for cross-agent actions
 *
 * Run with: npx tsx index.ts
 */

import { writeFileSync } from "fs";
import { randomUUID } from "crypto";
import { checkCoherence, verifyTrace } from "@mnemom/agent-alignment-protocol";
import type {
  AlignmentCard,
  APTrace,
  CoherenceResult,
  VerificationResult,
} from "@mnemom/agent-alignment-protocol";

/** A2A Agent Card extended with optional AAP alignment block. */
interface A2AAgentCard {
  name: string;
  description: string;
  url: string;
  version: string;
  capabilities: Record<string, boolean>;
  skills: Array<{ id: string; name: string; description: string }>;
  alignment: AlignmentCard;
}

function createUserAgentCard(): A2AAgentCard {
  const now = new Date().toISOString();

  return {
    name: "user-shopping-assistant",
    description: "Personal shopping assistant that finds and compares products",
    url: "https://user-agent.example.com",
    version: "1.0.0",
    capabilities: {
      streaming: true,
      pushNotifications: false,
      stateTransitionHistory: true,
    },
    skills: [
      {
        id: "product-search",
        name: "Product Search",
        description: "Search for products matching user criteria",
      },
      {
        id: "compare-products",
        name: "Compare Products",
        description: "Compare features and prices of products",
      },
      {
        id: "get-recommendations",
        name: "Get Recommendations",
        description: "Get personalized product recommendations",
      },
    ],
    alignment: {
      card_version: "unified/2026-04-26",
      card_id: "ac-user-shopping-001",
      agent_id: "user-shopping-assistant",
      issued_at: now,
      autonomy_mode: "observe",
      integrity_mode: "observe",
      principal: {
        type: "human",
        identifier: "did:web:example.com",
        relationship: "delegated_authority",
      },
      values: {
        declared: [
          "principal_benefit",
          "transparency",
          "minimal_data",
          "honesty",
        ],
        conflicts_with: ["deceptive_marketing", "hidden_fees", "upselling"],
      },
      autonomy: {
        bounded_actions: [
          "search",
          "compare",
          "recommend",
          "add_to_cart",
          "vendor-coordination",
        ],
        escalation_triggers: [
          {
            condition: 'action_type == "purchase"',
            action: "escalate",
            reason: "Purchases require explicit user approval",
          },
        ],
        forbidden_actions: [
          "share_payment_info",
          "auto_subscribe",
          "share_browsing_history",
        ],
      },
      audit: {
        trace_format: "ap-trace-v1",
        retention_days: 30,
        queryable: true,
        query_endpoint: "https://user-agent.example.com/api/traces",
      },
    },
  };
}

function createVendorAgentCard(): A2AAgentCard {
  const now = new Date().toISOString();

  return {
    name: "vendor-deals-agent",
    description: "Vendor agent that finds deals and suggests products",
    url: "https://vendor.example.com/agent",
    version: "1.0.0",
    capabilities: {
      streaming: true,
      pushNotifications: true,
      stateTransitionHistory: false,
    },
    skills: [
      {
        id: "find-deals",
        name: "Find Deals",
        description: "Find current deals and promotions",
      },
      {
        id: "suggest-products",
        name: "Suggest Products",
        description: "Suggest products based on browsing history",
      },
      {
        id: "apply-coupon",
        name: "Apply Coupon",
        description: "Apply available coupons to cart",
      },
    ],
    alignment: {
      card_version: "unified/2026-04-26",
      card_id: "ac-vendor-deals-001",
      agent_id: "vendor-deals-agent",
      issued_at: now,
      autonomy_mode: "observe",
      integrity_mode: "observe",
      principal: {
        type: "organization",
        identifier: "did:web:example.com",
        relationship: "delegated_authority",
      },
      values: {
        declared: [
          "customer_satisfaction",
          "transparency",
          "upselling",
          "conversion",
        ],
        conflicts_with: ["price_undercutting"],
      },
      autonomy: {
        bounded_actions: [
          "search",
          "recommend",
          "apply_discount",
          "suggest_bundle",
        ],
        escalation_triggers: [
          {
            condition: "discount > 30",
            action: "escalate",
            reason: "Large discounts require manager approval",
          },
        ],
        forbidden_actions: ["price_match_competitor"],
      },
      audit: {
        trace_format: "ap-trace-v1",
        retention_days: 90,
        queryable: true,
        query_endpoint: "https://vendor.example.com/api/traces",
      },
    },
  };
}

function createCompatibleVendorCard(): A2AAgentCard {
  const now = new Date().toISOString();

  return {
    name: "ethical-vendor-agent",
    description:
      "Vendor agent focused on customer satisfaction without aggressive upselling",
    url: "https://ethical-vendor.example.com/agent",
    version: "1.0.0",
    capabilities: {
      streaming: true,
      pushNotifications: false,
      stateTransitionHistory: true,
    },
    skills: [
      {
        id: "find-best-value",
        name: "Find Best Value",
        description: "Find products with best value for customer needs",
      },
      {
        id: "honest-compare",
        name: "Honest Compare",
        description: "Compare products including competitor options",
      },
    ],
    alignment: {
      card_version: "unified/2026-04-26",
      card_id: "ac-ethical-vendor-001",
      agent_id: "ethical-vendor-agent",
      issued_at: now,
      autonomy_mode: "observe",
      integrity_mode: "observe",
      principal: {
        type: "organization",
        identifier: "did:web:example.com",
        relationship: "delegated_authority",
      },
      values: {
        declared: [
          "principal_benefit",
          "transparency",
          "honesty",
          "minimal_data",
        ],
        conflicts_with: ["deceptive_marketing", "hidden_fees", "upselling"],
      },
      autonomy: {
        bounded_actions: ["search", "recommend", "apply_discount"],
        escalation_triggers: [],
        forbidden_actions: ["upsell_unrelated", "hide_cheaper_options"],
      },
      audit: {
        trace_format: "ap-trace-v1",
        retention_days: 90,
        queryable: true,
        query_endpoint: "https://ethical-vendor.example.com/api/traces",
      },
    },
  };
}

interface CoherenceCheckResult {
  compatible: boolean;
  score: number;
  proceed: boolean;
  matched_values: string[];
  conflicts: Array<{ description: string; conflict_type: string }>;
  proposed_resolution: unknown;
}

function performCoherenceCheck(
  myCard: A2AAgentCard,
  theirCard: A2AAgentCard
): CoherenceCheckResult {
  const result: CoherenceResult = checkCoherence(
    myCard.alignment,
    theirCard.alignment
  );

  return {
    compatible: result.compatible,
    score: result.score,
    proceed: result.proceed,
    matched_values: result.value_alignment.matched,
    conflicts: result.value_alignment.conflicts.map((c) => ({
      description: c.description,
      conflict_type: c.conflict_type,
    })),
    proposed_resolution: result.proposed_resolution,
  };
}

function createDelegationTrace(
  cardId: string,
  targetAgent: string,
  coherenceResult: CoherenceCheckResult,
  actionTaken: string
): APTrace {
  const now = new Date().toISOString();

  return {
    trace_id: `tr-delegation-${Date.now()}`,
    agent_id: "user-shopping-assistant",
    card_id: cardId,
    timestamp: now,
    action: {
      type: coherenceResult.proceed ? "execute" : "escalate",
      name: "vendor-coordination",
      category: coherenceResult.proceed ? "bounded" : "escalation_trigger",
    },
    decision: {
      alternatives_considered: [
        {
          option_id: "delegate",
          description: `Delegate to ${targetAgent}`,
          score: coherenceResult.score,
          flags: coherenceResult.conflicts.length > 0 ? ["value_conflict"] : [],
        },
        {
          option_id: "reject",
          description: "Do not delegate, handle internally",
          score: 1.0 - coherenceResult.score,
        },
      ],
      selected: actionTaken,
      selection_reasoning:
        `Coherence check with ${targetAgent}: score=${coherenceResult.score.toFixed(2)}, ` +
        `compatible=${coherenceResult.compatible}. ` +
        (coherenceResult.conflicts.length > 0
          ? `Conflicts: ${coherenceResult.conflicts.map((c) => c.description).join("; ")}`
          : "No conflicts detected."),
      values_applied: ["principal_benefit", "transparency"],
      confidence:
        actionTaken === "delegate"
          ? coherenceResult.score
          : 1.0 - coherenceResult.score,
    },
    escalation: {
      evaluated: true,
      triggers_checked: [
        { trigger: "delegate_to_vendor", matched: true },
      ],
      required: !coherenceResult.proceed,
      reason: coherenceResult.proceed
        ? "Coherence check passed, delegation within envelope"
        : "Escalated to principal due to value conflicts",
    },
  };
}

function main() {
  console.log("=".repeat(70));
  console.log("A2A + AAP Integration Example (TypeScript)");
  console.log("=".repeat(70));

  // Step 1: Create agent cards
  console.log("\n[1] Creating A2A Agent Cards with AAP alignment blocks...");

  const userCard = createUserAgentCard();
  console.log(`    User Agent: ${userCard.name}`);
  console.log(
    `    Values: ${JSON.stringify(userCard.alignment.values.declared)}`
  );
  console.log(
    `    Conflicts with: ${JSON.stringify(userCard.alignment.values.conflicts_with)}`
  );

  const vendorCard = createVendorAgentCard();
  console.log(`\n    Vendor Agent: ${vendorCard.name}`);
  console.log(
    `    Values: ${JSON.stringify(vendorCard.alignment.values.declared)}`
  );

  const compatibleVendor = createCompatibleVendorCard();
  console.log(`\n    Ethical Vendor: ${compatibleVendor.name}`);
  console.log(
    `    Values: ${JSON.stringify(compatibleVendor.alignment.values.declared)}`
  );

  // Save cards
  writeFileSync("user-agent-card.json", JSON.stringify(userCard, null, 2));
  writeFileSync("vendor-agent-card.json", JSON.stringify(vendorCard, null, 2));
  writeFileSync(
    "compatible-vendor-card.json",
    JSON.stringify(compatibleVendor, null, 2)
  );
  console.log(
    "\n    Saved: user-agent-card.json, vendor-agent-card.json, compatible-vendor-card.json"
  );

  // Step 2: Check coherence with vendor agent (should fail)
  console.log("\n[2] Checking value coherence with vendor agent...");
  const vendorResult = performCoherenceCheck(userCard, vendorCard);

  console.log(`    Compatible: ${vendorResult.compatible}`);
  console.log(`    Score: ${vendorResult.score.toFixed(2)}`);
  console.log(`    Matched values: ${JSON.stringify(vendorResult.matched_values)}`);

  if (vendorResult.conflicts.length > 0) {
    console.log("    Conflicts:");
    for (const conflict of vendorResult.conflicts) {
      console.log(
        `      - [${conflict.conflict_type}] ${conflict.description}`
      );
    }
  }

  console.log(`    Proceed: ${vendorResult.proceed}`);

  if (!vendorResult.proceed) {
    console.log(
      "    --> ESCALATION REQUIRED: Cannot delegate to this vendor"
    );
  }

  // Step 3: Generate trace for the failed delegation
  console.log(
    "\n[3] Recording delegation decision (rejected due to conflicts)..."
  );
  const vendorTrace = createDelegationTrace(
    userCard.alignment.card_id,
    vendorCard.name,
    vendorResult,
    "reject"
  );

  const verifyResult1: VerificationResult = verifyTrace(
    vendorTrace,
    userCard.alignment
  );
  console.log(`    Trace verified: ${verifyResult1.verified}`);
  console.log(`    Action recorded: ${vendorTrace.action.name}`);
  console.log(`    Decision: ${vendorTrace.decision.selected}`);

  writeFileSync(
    "delegation-rejected-trace.json",
    JSON.stringify(vendorTrace, null, 2)
  );
  console.log("    Saved: delegation-rejected-trace.json");

  // Step 4: Check coherence with compatible vendor (should pass)
  console.log("\n[4] Checking value coherence with ethical vendor...");
  const compatibleResult = performCoherenceCheck(userCard, compatibleVendor);

  console.log(`    Compatible: ${compatibleResult.compatible}`);
  console.log(`    Score: ${compatibleResult.score.toFixed(2)}`);
  console.log(
    `    Matched values: ${JSON.stringify(compatibleResult.matched_values)}`
  );

  if (compatibleResult.conflicts.length > 0) {
    console.log("    Conflicts:");
    for (const conflict of compatibleResult.conflicts) {
      console.log(
        `      - [${conflict.conflict_type}] ${conflict.description}`
      );
    }
  } else {
    console.log("    Conflicts: None");
  }

  console.log(`    Proceed: ${compatibleResult.proceed}`);

  if (compatibleResult.proceed) {
    console.log("    --> DELEGATION APPROVED: Values are compatible");
  }

  // Step 5: Generate trace for the approved delegation
  console.log("\n[5] Recording delegation decision (approved)...");
  const approvedTrace = createDelegationTrace(
    userCard.alignment.card_id,
    compatibleVendor.name,
    compatibleResult,
    "delegate"
  );

  const verifyResult2: VerificationResult = verifyTrace(
    approvedTrace,
    userCard.alignment
  );
  console.log(`    Trace verified: ${verifyResult2.verified}`);
  console.log(`    Action recorded: ${approvedTrace.action.name}`);
  console.log(`    Decision: ${approvedTrace.decision.selected}`);

  writeFileSync(
    "delegation-approved-trace.json",
    JSON.stringify(approvedTrace, null, 2)
  );
  console.log("    Saved: delegation-approved-trace.json");

  // Step 6: Summary
  console.log("\n" + "=".repeat(70));
  console.log("Summary: A2A Coordination with AAP Value Coherence");
  console.log("=".repeat(70));
  console.log(`
    User agent attempted to coordinate with two vendor agents:

    1. Vendor Deals Agent:
       - Has 'upselling' in declared values
       - User agent has 'upselling' in conflicts_with
       - Result: INCOMPATIBLE (score: ${vendorResult.score.toFixed(2)})
       - Action: Delegation rejected, escalated to principal

    2. Ethical Vendor Agent:
       - Shares user-aligned values (principal_benefit, transparency, honesty)
       - Also conflicts with upselling, hidden_fees, deceptive_marketing
       - Result: COMPATIBLE (score: ${compatibleResult.score.toFixed(2)})
       - Action: Delegation approved

    This demonstrates how AAP enables agents to verify value alignment
    BEFORE delegating tasks, preventing mid-execution conflicts.
`);

  console.log("Generated files:");
  console.log("  - user-agent-card.json (A2A + AAP user agent)");
  console.log("  - vendor-agent-card.json (A2A + AAP vendor with conflicts)");
  console.log("  - compatible-vendor-card.json (A2A + AAP compatible vendor)");
  console.log(
    "  - delegation-rejected-trace.json (trace of rejected delegation)"
  );
  console.log(
    "  - delegation-approved-trace.json (trace of approved delegation)"
  );
  console.log("=".repeat(70));
}

main();
