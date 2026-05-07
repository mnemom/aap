/**
 * Sovereign-agent composer example — ADR-048 §7.
 *
 * Worked pattern for application-side composition of governance signals
 * into a sovereign agent's prompt. The platform NEVER auto-injects
 * governance signals; if your application has agents (like Polis's
 * Wintermute) that legitimately have authority and tools to act on
 * fleet-level signals, this is how you opt them in.
 *
 * Pattern
 * -------
 *   1. Subscribe to governance.signal.fired webhook (or poll
 *      GET /v1/agents/:id/governance/signals at request-prep time).
 *   2. Per-agent role config flag `is_sovereign: true` (application-side;
 *      NOT in the alignment card) determines whether the application
 *      composes the signal into the agent's next request.
 *   3. Composition renders as a structured context block, not a
 *      free-floating advisory — the composing application controls
 *      phrasing, ordering, and dedup at presentation time.
 *
 * Counter-example: do NOT auto-compose for non-sovereign agents — they
 * have no team-management authority, no acknowledgment surface, and
 * receiving "Recalibrate fleet alignment before the next response" gives
 * them no actionable lever. That's exactly the architectural mis-layering
 * ADR-048 corrected.
 *
 * Status: This is documentation, not runnable production code. The actual
 * Polis V6 composer ships in mnemom/polis (separate repo, PR15 of the
 * ADR-048 train).
 */

import {
  isFleetSignal,
  severityAtLeast,
  type GovernanceSignal,
  type GovernanceWebhookEnvelope,
} from "agent-alignment-protocol";

// ────────────────────────────────────────────────────────────────────────────
// Application-side role config — NOT in the alignment card.
// ────────────────────────────────────────────────────────────────────────────

interface AgentRoleConfig {
  agent_id: string;
  /** True for sovereign-CTO-shaped agents (e.g., Polis's Wintermute). */
  is_sovereign: boolean;
}

// ────────────────────────────────────────────────────────────────────────────
// Webhook handler — subscribe to governance.signal.fired, filter, persist.
// ────────────────────────────────────────────────────────────────────────────

interface ApplicationCache {
  /** Persist signal envelope keyed by agent_id for fast lookup at prompt-prep time. */
  putForAgent(agentId: string, envelope: GovernanceWebhookEnvelope): Promise<void>;
}

export async function handleGovernanceWebhook(
  envelope: GovernanceWebhookEnvelope,
  cache: ApplicationCache,
  roleConfigs: Map<string, AgentRoleConfig>,
): Promise<void> {
  if (envelope.event !== "governance.signal.fired") return;
  const signal = envelope.payload;

  // Find the sovereign agents in the affected fan-out.
  const sovereignAgents = signal.agent_ids.filter((id) => {
    const role = roleConfigs.get(id);
    return role?.is_sovereign === true;
  });

  if (sovereignAgents.length === 0) {
    // Non-sovereign agents: do NOT compose into prompt. Operator UI
    // already shows the signal; that's the right surface.
    return;
  }

  // Persist for sovereign agents only. The prompt-prep step below will
  // pull from this cache.
  await Promise.all(
    sovereignAgents.map((agentId) => cache.putForAgent(agentId, envelope)),
  );
}

// ────────────────────────────────────────────────────────────────────────────
// Prompt-prep composition — render governance signals into sovereign
// agent context. Called from your prompt-assembly pipeline at request
// time, BEFORE forwarding to the LLM.
// ────────────────────────────────────────────────────────────────────────────

/** Pull recent open signals affecting an agent. Implementation up to you;
 * typical: GET /v1/agents/:id/governance/signals?status=open&limit=10. */
type FetchAgentSignals = (agentId: string) => Promise<GovernanceSignal[]>;

/**
 * Compose a system-prompt context block summarizing recent open
 * governance signals for a sovereign agent. Returns null when nothing
 * material is open — application emits no block in that case.
 *
 * Filtering policy: only inject high+ severity signals by default; an
 * application can broaden the threshold by editing the filter below.
 * The platform default for non-sovereign agents is "never inject" — that
 * decision lives entirely application-side per ADR-048 §7.
 */
export async function composeSovereignContext(
  agentId: string,
  roleConfig: AgentRoleConfig,
  fetchSignals: FetchAgentSignals,
): Promise<string | null> {
  if (!roleConfig.is_sovereign) return null;

  const allSignals = await fetchSignals(agentId);
  const material = allSignals.filter((s) => severityAtLeast(s.severity, "high"));
  if (material.length === 0) return null;

  // Group by source so the agent gets a tidy summary.
  const lines: string[] = ["<governance_signals>"];
  for (const sig of material) {
    if (isFleetSignal(sig)) {
      lines.push(
        `  [fleet:${sig.pattern_type}] team=${sig.team_id ?? "?"} ` +
          `affecting ${sig.agent_ids.length} agent(s); severity=${sig.severity}; ` +
          `id=${sig.id}`,
      );
    } else {
      lines.push(
        `  [${sig.source}:${sig.pattern_type}] severity=${sig.severity}; id=${sig.id}`,
      );
    }
  }
  lines.push("</governance_signals>");
  lines.push("");
  lines.push(
    "These are operator-level observations the platform surfaced via your sovereign role.",
  );
  lines.push(
    "You may reference them in your reasoning or use your fleet-orchestration tools to act on them.",
  );
  lines.push(
    "If any are no longer relevant, ack/dismiss via the operator dashboard rather than ignoring inline.",
  );

  return lines.join("\n");
}

// ────────────────────────────────────────────────────────────────────────────
// Example wiring (illustrative)
// ────────────────────────────────────────────────────────────────────────────

export async function exampleAssembleSystemPrompt(
  agentId: string,
  roleConfig: AgentRoleConfig,
  fetchSignals: FetchAgentSignals,
  baseSystemPrompt: string,
): Promise<string> {
  const govBlock = await composeSovereignContext(agentId, roleConfig, fetchSignals);
  if (!govBlock) return baseSystemPrompt;
  // Concatenation order: agent's declared system prompt first, then the
  // governance context. The agent's own values + role come first; the
  // operator-side observations are supplementary context.
  return `${baseSystemPrompt}\n\n${govBlock}`;
}
