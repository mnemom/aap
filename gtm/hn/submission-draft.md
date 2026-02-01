# Hacker News Submission Draft

## Title Options (pick one, max 80 chars)

**Option A (descriptive):**
```
Agent Alignment Protocol: A transparency protocol for autonomous AI agents
```

**Option B (problem-focused):**
```
Show HN: AAP – Making AI agent alignment observable and auditable
```

**Option C (technical):**
```
AAP: Alignment Cards, AP-Trace, and Value Coherence for multi-agent systems
```

**Recommended: Option B** — "Show HN" signals it's a real project. "Observable and auditable" is concrete.

---

## URL

```
https://github.com/[org]/aap
```

---

## Text (if Show HN, include brief description)

```
We built AAP because the agent protocol stack (A2A, MCP) has no alignment layer.

When multiple AI agents coordinate, there's currently no standard way to:
- Know what values guide an agent's decisions
- Audit what alternatives it considered
- Verify that two agents' values are compatible before they work together
- Detect when an agent drifts from its declared alignment

AAP provides three primitives:

1. Alignment Card: Static declaration of values, autonomy bounds, and audit commitments
2. AP-Trace: Audit log format for agent decisions
3. Value Coherence Handshake: Pre-coordination compatibility check

Key constraints we held ourselves to:
- Transparency, not trust. AAP makes behavior observable, not provably correct.
- Explicit limitations. We document what AAP can't do (see LIMITS.md).
- Extends, doesn't replace. Works with existing A2A and MCP protocols.

The verification engine is extracted from production systems, not designed in a vacuum. Drift detection thresholds are calibrated from ~50 real multi-turn agent conversations.

Python SDK: `pip install agent-alignment-protocol`
TypeScript SDK: coming soon

We're submitting to the Agentic AI Foundation as well.

Feedback welcome, especially from people building multi-agent systems.
```

---

## Alternative Short Version (if just link)

```
The agent stack (A2A, MCP) handles capabilities but not alignment. AAP adds Alignment Cards (what the agent claims to be), AP-Trace (what it actually did), and Value Coherence Handshake (can these agents work together?).

It's a transparency protocol - we're explicit about what it can and can't do. See LIMITS.md.
```

---

## Anticipated Questions and Responses

**Q: How is this different from just having API documentation?**
A: Alignment Cards are machine-readable and verifiable. You can programmatically check that an agent's behavior matches its declared alignment, detect drift over time, and verify value compatibility before coordination.

**Q: Can't agents just lie?**
A: Yes. AAP is a transparency protocol, not a trust protocol. It makes claims auditable, not guaranteed. See Section 10 of the spec (Limitations) - we're explicit about this.

**Q: Why not just use existing logging/audit systems?**
A: AP-Trace has a specific schema designed for alignment verification. It captures alternatives considered, values applied, and escalation decisions. Generic logs don't have this structure.

**Q: What's the threat model?**
A: Documented in SECURITY.md. Short version: we protect against careless misrepresentation and enable audit. We don't protect against sophisticated adversaries who control the agent runtime.

**Q: Is this just another JSON schema?**
A: The schemas are the easy part. The verification engine (drift detection, coherence scoring) is where the real work is. The thresholds are calibrated from real dialogue data.

---

## Timing Recommendations

- **Best days**: Tuesday, Wednesday, Thursday
- **Best time**: 9-10 AM EST (when US coast wakes up, EU still online)
- **Avoid**: Weekends, Fridays, holidays, major tech news days

---

## Post-Submission Checklist

1. [ ] Monitor for questions, respond promptly and substantively
2. [ ] Don't ask friends to upvote (HN detects this)
3. [ ] If someone points out a real issue, acknowledge it honestly
4. [ ] Link to specific docs when answering (SPEC.md, LIMITS.md, etc.)
5. [ ] Keep responses technical, not marketing-speak
