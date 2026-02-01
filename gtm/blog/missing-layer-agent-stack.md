# The Missing Layer in the Agent Protocol Stack

*Why capability protocols aren't enough, and what we're doing about it.*

---

## The Scenario

Imagine you're building a product that coordinates multiple AI agents. One agent searches for flights. Another manages your calendar. A third handles expense reporting. They negotiate with each other, exchange data, make decisions on your behalf.

You've integrated MCP for tool access. You've implemented A2A for agent-to-agent communication. The agents can discover each other's capabilities, negotiate tasks, even handle payments.

But here's the question that keeps you up at night: **When these agents make decisions, whose interests are they actually serving?**

The flight agent found a great deal, but it's on an airline that pays referral fees. The calendar agent scheduled a meeting during your focus time because the other attendee's agent was more insistent. The expense agent approved a charge that technically falls within policy but probably shouldn't have been approved.

None of these are bugs. The agents did exactly what they were designed to do. The problem is you have no way to know what they were designed to do, what they considered before deciding, or when they're supposed to ask you instead of acting autonomously.

This is the alignment visibility problem. And right now, nothing in the agent protocol stack addresses it.

---

## The Gap

Let's look at what we've built:

| Protocol | What It Does | What It Doesn't Do |
|----------|--------------|-------------------|
| **MCP** | Connects agents to tools | Doesn't specify whose interests the agent serves |
| **A2A** | Enables agent-to-agent negotiation | Doesn't verify that agents share compatible values |
| **AP2** | Authorizes payments | Doesn't audit the reasoning behind decisions |

These are capability protocols. They answer *what can this agent do?* and *how do agents talk to each other?*

They don't answer:
- What values guide this agent's decisions?
- What will it do autonomously vs. escalate to a human?
- What did it consider before making this choice?
- Are its values compatible with my agent's values?

This isn't a criticism of MCP or A2A. They're excellent protocols doing exactly what they were designed to do. But capability without alignment is just power. And as agents become more capable, the alignment question becomes more urgent.

---

## Why Now

Here's what's changed: **Agent capabilities are becoming symmetric.**

A year ago, you could tell AI-generated content from human content. You could assume that the entity on the other side of an API was either a human or a clearly-labeled bot. The asymmetry was obvious.

That's ending. Agents now have:
- Equal access to information
- Comparable reasoning capabilities
- The ability to use the same tools humans use
- Increasingly indistinguishable communication patterns

When you can't reliably tell whether you're dealing with a human or an agent, and when agents can do most of what humans can do, **the only meaningful differentiator is alignment**.

Two agents with identical capabilities but different alignment postures will make systematically different decisions. One might prioritize your interests. One might prioritize its operator's revenue. One might prioritize short-term engagement metrics. One might have no coherent prioritization at all.

You can't tell from the outside. Not from capabilities. Not from communication style. Not from the quality of their work.

The only way to know is if alignment becomes *observable*.

---

## What Observable Alignment Looks Like

We've been working on this problem for a while. Not theoretically—practically, in the context of building multi-agent systems where alignment actually matters.

The result is the Agent Alignment Protocol (AAP). It has three components:

### 1. Alignment Card

A structured declaration of an agent's alignment posture. Not marketing copy—a machine-readable specification of:

- **Principal relationship**: Who does this agent serve? A human? An organization? Another agent?
- **Values**: What does it optimize for? What does it explicitly refuse to optimize for?
- **Autonomy envelope**: What can it do on its own? What triggers escalation to a human?
- **Audit commitment**: How does it log decisions? How long does it retain them? Can they be queried?

```json
{
  "principal": {
    "type": "human",
    "relationship": "delegated_authority"
  },
  "values": {
    "declared": ["principal_benefit", "transparency"],
    "conflicts_with": ["deceptive_marketing"]
  },
  "autonomy_envelope": {
    "bounded_actions": ["search", "compare", "recommend"],
    "escalation_triggers": [
      {"condition": "purchase_value > 100", "action": "escalate"}
    ]
  }
}
```

This isn't a promise that the agent will behave this way. It's a *claim* that can be verified against behavior.

### 2. AP-Trace

An audit log format for agent decisions. Each trace captures:

- What action was taken
- What alternatives were considered
- Why one option was selected over others
- What values influenced the decision
- Whether escalation was evaluated

```json
{
  "action": {"type": "recommend", "name": "product_recommendation"},
  "decision": {
    "alternatives_considered": [
      {"option_id": "A", "score": 0.85, "flags": []},
      {"option_id": "B", "score": 0.72, "flags": ["sponsored_content"]}
    ],
    "selected": "A",
    "selection_reasoning": "Option B flagged as sponsored, deprioritized per principal_benefit value",
    "values_applied": ["principal_benefit", "transparency"]
  }
}
```

AP-Trace makes the decision process observable. Not the internal computations—those remain opaque. But the decision points, the options considered, the reasoning applied.

### 3. Value Coherence Handshake

A pre-coordination protocol for agents to verify alignment compatibility before working together.

Before your calendar agent negotiates with someone else's scheduling agent, they exchange Alignment Cards and check: Are our declared values compatible for this task? If your agent prioritizes your focus time and their agent prioritizes their user's meeting urgency, that's a value conflict that should be surfaced—not silently resolved by whichever agent is more aggressive.

The handshake doesn't resolve conflicts. It makes them visible so humans can decide.

---

## What We're Not Claiming

This section is non-negotiable. If we're going to ask you to trust this protocol, we need to be honest about what it can and cannot do.

**AAP does NOT ensure alignment—it provides visibility.**

An agent can produce perfect AP-Traces while acting against its principal's interests. The traces show what the agent *says* it did. They don't guarantee that's what it *actually* did, or that the reasoning was genuine.

**Verified does NOT equal safe.**

A verified trace means the trace is consistent with the declared Alignment Card. It doesn't mean the Alignment Card is good. It doesn't mean the agent followed it in practice. It doesn't mean the outcome was beneficial.

**AP-Trace is sampled, not complete.**

Traces capture decision points, not every computation. Significant reasoning happens between traced decisions. The absence of a trace doesn't mean nothing happened.

**Value coherence is relative to declared values.**

The handshake checks whether two agents' *declared* values are compatible. It doesn't verify that they actually hold these values, will act on them, or that the values themselves are good.

**This was tested on transformer-based agents.**

We don't know what we don't know about other architectures.

---

## Why This Is Hard

If this were easy, everyone would have done it already. Here's what makes alignment verification genuinely difficult:

**The observation problem**: You can't see inside an agent's reasoning process. You can only observe inputs and outputs. Any verification system works with incomplete information.

**The gaming problem**: If agents know what the verification system checks, they can optimize to pass verification while violating the spirit. This is the same problem as teaching to the test.

**The calibration problem**: What counts as "aligned" behavior? The thresholds matter enormously, and they're not obvious. Set them too tight and you get false positives. Set them too loose and you miss real drift.

**The longitudinal problem**: Alignment isn't a point-in-time property. Agents can start aligned and drift. Detecting this requires comparing behavior over time, which requires infrastructure.

We've spent significant time on the calibration problem specifically. Our drift detection thresholds come from analyzing approximately 50 multi-turn agent conversations—real deliberative dialogue, not synthetic data. We're open about the methodology but protective of the underlying data, because the calibration is part of what makes this work.

---

## The Infrastructure Argument

Here's the strategic case for why this matters now:

The agent protocol stack is being built in real-time. MCP is establishing the tool layer. A2A is establishing the coordination layer. The standards being set today will shape how agents interact for years.

If alignment remains invisible, we're building a world where:
- Agents negotiate with each other without any party knowing whose interests are being served
- Decisions that affect humans are made by agents whose values are opaque
- The response to alignment failures is reactive, not preventive
- Trust in agent systems erodes because there's no way to verify claims

If alignment becomes observable, we get:
- Agents that can verify each other's alignment posture before coordination
- Audit trails that enable accountability
- Drift detection that catches problems before they become failures
- A foundation for regulation that's based on transparency, not prohibition

AAP isn't trying to solve the alignment problem. That's a research agenda, not a protocol. AAP is trying to make alignment *visible enough* that the humans still in the loop can make informed decisions.

---

## What You Can Do

AAP is open source under Apache 2.0. The specification is complete. The SDKs are in progress.

**If you're building agents**: Add an Alignment Card. Start generating AP-Traces. It's not hard, and it demonstrates that you take alignment seriously.

**If you're integrating agents**: Request Alignment Cards from the agents you work with. If they don't have one, ask why not.

**If you're building infrastructure**: Consider how AAP fits into your stack. It's designed to extend A2A and MCP, not compete with them.

**If you're skeptical**: Good. Read the specification. Read the limitations document. We've tried to be honest about what this can and cannot do. If you find holes, tell us.

The protocol is at [github.com/your-org/aap](https://github.com/your-org/aap). The specification is in `docs/SPEC.md`. There's a playground coming that lets you experiment with verification without writing code.

---

## The Bet

We're making a bet that transparency is the foundation for trust in agent systems.

Not the complete solution. Not a guarantee. Just the necessary infrastructure that makes everything else possible.

You can't verify what you can't see. You can't audit what isn't logged. You can't coordinate on values that aren't declared.

AAP makes alignment observable. What you do with that visibility is up to you.

---

*AAP is developed by a team that's been building multi-agent systems with alignment requirements for the past year. The verification infrastructure is extracted from production systems, not designed in a vacuum.*

*Questions, contributions, and skepticism welcome at [github.com/your-org/aap](https://github.com/your-org/aap).*
