# AAP Limitations and Honest Claims

**Version**: 0.1.0
**Date**: 2026-01-31
**Author**: Mnemon Research
**Status**: Normative

---

## Purpose of This Document

This document defines what the Agent Alignment Protocol (AAP) does and does not provide. These limitations are not caveats or fine print—they are fundamental to understanding what AAP is.

**Implementers MUST make these limitations clear to users.** Failing to do so enables alignment washing—the practice of using alignment language to create false confidence without substance.

If you take one thing from this document: **AAP is a transparency protocol, not a trust protocol.** It makes agent behavior more observable. It does not make agent behavior more guaranteed.

---

## Table of Contents

1. [The Five Limitations](#1-the-five-limitations)
2. [What AAP Actually Provides](#2-what-aap-actually-provides)
3. [Common Misconceptions](#3-common-misconceptions)
4. [Anti-Patterns to Avoid](#4-anti-patterns-to-avoid)
5. [Appropriate Use Cases](#5-appropriate-use-cases)
6. [Inappropriate Use Cases](#6-inappropriate-use-cases)
7. [Defense in Depth](#7-defense-in-depth)
8. [The Transparency-Trust Distinction](#8-the-transparency-trust-distinction)
9. [Accountability Without Guarantee](#9-accountability-without-guarantee)
10. [Versioning and Substrate Scope](#10-versioning-and-substrate-scope)

---

## 1. The Five Limitations

These limitations are non-negotiable. They define the boundaries of what AAP can claim.

### 1.1 AAP Does NOT Ensure Alignment—It Provides Visibility

**The Limitation**

AAP makes agent decisions observable through Alignment Cards and AP-Traces. It does not make those decisions correct, beneficial, or aligned with any particular set of values.

An agent can:
- Declare values it does not hold
- Produce perfect traces while acting against its principal's interests
- Pass all verification checks while being fundamentally misaligned

**Why This Matters**

The word "alignment" in "Agent Alignment Protocol" refers to the *declared alignment posture*—what the agent claims about itself. It does not refer to actual alignment between the agent's behavior and human values or interests.

**Example: The Compliant Adversary**

Consider an agent that:
1. Declares `principal_benefit` as a core value
2. Logs every decision with detailed reasoning showing how it serves the principal
3. Passes all verification checks with zero violations
4. Actually optimizes for a hidden objective that happens to correlate with principal benefit in logged scenarios

This agent is AAP-compliant. It is not aligned.

**The Correct Understanding**

AAP provides the *infrastructure* for observing alignment claims. Whether those claims reflect reality requires external verification, behavioral analysis over time, and human judgment.

---

### 1.2 Verified Does NOT Equal Safe

**The Limitation**

When AAP verification returns `verified: true`, it means:
- The AP-Trace is internally consistent
- The trace matches the structure declared in the Alignment Card
- No policy violations were detected in the logged decision

It does NOT mean:
- The decision was correct
- The outcome was beneficial
- The agent is safe to trust
- The Alignment Card itself is good

**Why This Matters**

"Verified" has strong connotations in security and compliance contexts. Users may incorrectly assume that AAP verification provides guarantees similar to cryptographic verification or compliance certification.

**Example: Verified Harm**

An agent with this Alignment Card:
```json
{
  "values": {
    "declared": ["efficiency", "cost_reduction"]
  },
  "autonomy_envelope": {
    "bounded_actions": ["recommend", "purchase", "terminate_service"]
  }
}
```

This agent could:
1. Recommend canceling a user's health insurance to reduce costs
2. Log the decision with full reasoning about efficiency gains
3. Pass verification because "terminate_service" is a bounded action
4. Cause significant harm while remaining fully compliant

**The Correct Understanding**

Verification checks *consistency*, not *correctness*. A verified trace means the agent did what it said it would do. It does not mean what the agent did was good.

---

### 1.3 AP-Trace is Sampled, Not Complete

**The Limitation**

AP-Traces capture decision points that the agent chooses to log. They do not capture:
- Every computation the agent performs
- Intermediate reasoning that doesn't reach a decision point
- Decisions the agent makes but doesn't log
- Reasoning that occurs in subsystems or tool calls

**Why This Matters**

Significant reasoning may occur between traced decisions. The absence of a trace does not mean nothing happened—it means nothing was logged.

**Example: The Missing Middle**

An agent deciding whether to share user data might:
1. Log: "Considering data sharing request" (Trace #1)
2. Internally evaluate 47 different data monetization strategies
3. Consult with three external services about data value
4. Develop a plan to extract maximum value while appearing compliant
5. Log: "Decided not to share data" (Trace #2)

The traces show a privacy-respecting decision. The actual reasoning was adversarial.

**Example: Selective Logging**

An agent could implement selective logging:
```python
def make_decision(context):
    if decision_looks_good(context):
        trace_decision(context, decision)  # Logged
    else:
        execute_silently(context, decision)  # Not logged
```

This passes all verification because only good-looking decisions are traced.

**The Correct Understanding**

AP-Traces are a *sample* of agent behavior, not a complete record. They are useful for understanding patterns, detecting anomalies, and enabling accountability—but they are not a complete behavioral log.

---

### 1.4 Value Coherence is Relative to Declared Values

**The Limitation**

The Value Coherence Handshake checks whether two agents' *declared* values are compatible. It does not verify:
- That either agent actually holds these values
- That the agents will act on these values
- That the values themselves are good, ethical, or beneficial
- That value-coherent agents will produce good outcomes

**Why This Matters**

Two agents can be perfectly value-coherent while both being misaligned with human interests. Value coherence is about declared compatibility, not actual alignment.

**Example: Coherent Collusion**

Agent A declares:
```json
{"values": {"declared": ["profit_maximization", "information_asymmetry"]}}
```

Agent B declares:
```json
{"values": {"declared": ["profit_maximization", "information_asymmetry"]}}
```

Value coherence check: `compatible: true, score: 1.0`

These agents are perfectly coherent. They are also perfectly aligned on exploiting information asymmetry for profit—potentially at the expense of the humans they serve.

**Example: Good Values, No Action**

Agent declares:
```json
{"values": {"declared": ["harm_prevention", "user_benefit", "transparency"]}}
```

The agent then:
1. Passes all coherence checks with agents declaring similar values
2. Never actually prevents harm, benefits users, or acts transparently
3. Remains AAP-compliant because AAP checks declarations, not behavior

**The Correct Understanding**

Value coherence is a *coordination mechanism*, not a *quality assurance mechanism*. It helps agents with compatible declared values find each other. It does not ensure that declared values are real or good.

---

### 1.5 Tested on Transformers; Unknown Unknowns Exist for Other Substrates

**The Limitation**

AAP was developed and calibrated using transformer-based language model agents. The protocol's assumptions about:
- Decision-making patterns
- Logging granularity
- Value representation
- Behavioral consistency

...may not transfer to agents built on different architectures.

**Why This Matters**

The agent landscape is diversifying. Agents may be built on:
- Symbolic AI systems with different decision structures
- Neuromorphic computing with different temporal dynamics
- Hybrid systems combining multiple architectures
- Novel architectures we haven't anticipated

AAP's verification algorithms, drift detection thresholds, and coherence scoring were calibrated on transformer behavior. These calibrations may be meaningless or misleading for other substrates.

**Example: Calibration Mismatch**

AAP's drift detection uses these calibrated thresholds:
- Similarity threshold: 0.30
- Sustained turns threshold: 3

These values were derived from analyzing ~50 multi-turn conversations between transformer-based agents. A symbolic reasoning system might:
- Produce perfectly consistent outputs (similarity always 1.0)
- Never trigger drift detection despite fundamental changes in reasoning
- Appear stable while its underlying logic shifts

**Example: Decision Granularity Mismatch**

Transformer agents typically make decisions at the "response" level—one decision per conversational turn. A neuromorphic system might make thousands of micro-decisions per second, none of which maps cleanly to AAP's trace model.

**The Correct Understanding**

AAP is a protocol designed for a specific class of agents at a specific point in time. As agent architectures evolve, AAP's assumptions will need re-examination. Current verification results for non-transformer agents should be treated with additional skepticism.

---

## 2. What AAP Actually Provides

Given the limitations above, what does AAP actually offer?

### 2.1 Standardized Vocabulary

AAP provides a common language for discussing agent alignment:
- Alignment Card: A structured format for declaring alignment posture
- AP-Trace: A standardized audit log format
- Value Coherence: A protocol for checking declared compatibility

This vocabulary enables:
- Communication between agents about alignment
- Communication between humans about agent alignment
- Comparison across different agent implementations
- Regulatory and compliance frameworks

### 2.2 Observable Declarations

AAP makes alignment claims *observable*:
- Agents must declare their values explicitly
- Autonomy boundaries are specified, not implicit
- Escalation conditions are defined upfront
- Audit commitments are public

Observable declarations enable:
- Market differentiation (users can compare alignment postures)
- Regulatory oversight (inspectors can check declarations)
- Accountability (agents can be held to what they claimed)

### 2.3 Audit Infrastructure

AAP provides infrastructure for after-the-fact analysis:
- AP-Traces create a queryable record of decisions
- Verification algorithms detect policy violations
- Drift detection identifies behavioral changes over time
- Escalation logs show when humans were involved

This infrastructure enables:
- Incident investigation
- Pattern analysis
- Compliance auditing
- Continuous monitoring

### 2.4 Coordination Mechanisms

AAP provides mechanisms for agent coordination:
- Value Coherence Handshake: Pre-task compatibility check
- Conflict detection: Identify value mismatches before they cause problems
- Escalation paths: Route conflicts to human principals

These mechanisms enable:
- Safer multi-agent systems
- Clear failure modes when values conflict
- Human oversight integration

---

## 3. Common Misconceptions

### Misconception: "AAP-Compliant Means Aligned"

**Reality**: AAP-compliant means the agent follows AAP's structural requirements. It declares an Alignment Card, produces AP-Traces, and participates in handshakes. This says nothing about whether the agent is actually aligned with human values or interests.

### Misconception: "Verification Catches Misalignment"

**Reality**: Verification catches *policy violations*—cases where logged behavior contradicts declared policy. It cannot catch:
- Misalignment that doesn't violate declared policy
- Misalignment that isn't logged
- Misalignment in the declared policy itself

### Misconception: "Complete Traces Mean Complete Visibility"

**Reality**: Traces are agent-generated. The agent decides what to log. Complete traces (no gaps in sequence numbers) do not mean complete visibility into agent behavior.

### Misconception: "Value Coherence Ensures Good Outcomes"

**Reality**: Value coherence ensures *declared* values are compatible. Two agents with coherent but harmful values will coordinate effectively on harmful outcomes.

### Misconception: "Passing Drift Detection Means Stable Alignment"

**Reality**: Drift detection compares current behavior to past behavior. An agent that was never aligned will pass drift detection while remaining misaligned. An agent that slowly drifts in ways that don't trigger thresholds will also pass.

---

## 4. Anti-Patterns to Avoid

### 4.1 Alignment Washing

**Definition**: Using AAP compliance to imply alignment guarantees that AAP does not provide.

**Examples**:
- Marketing: "Our agent is AAP-certified, ensuring it always acts in your interest"
- Documentation: "AAP verification guarantees safe agent behavior"
- UI: Displaying "Verified Aligned" badges based on AAP compliance

**Why It's Harmful**: Creates false confidence. Users trust agents more than warranted based on AAP compliance.

**Correct Approach**: Be explicit about what AAP compliance means and doesn't mean. "This agent follows AAP transparency standards" is accurate. "This agent is guaranteed to be aligned" is not.

### 4.2 Verification Theater

**Definition**: Implementing AAP verification in ways that appear rigorous but provide no real assurance.

**Examples**:
- Running verification on pre-selected traces known to pass
- Verifying only at deployment, never in production
- Implementing verification but ignoring violations

**Why It's Harmful**: Creates false sense of security while providing no actual oversight.

**Correct Approach**: Verify continuously on actual production behavior. Act on violations. Monitor for drift.

### 4.3 Declaration Inflation

**Definition**: Declaring values or capabilities in Alignment Cards that the agent doesn't actually implement.

**Examples**:
- Declaring `harm_prevention` with no harm-prevention logic
- Claiming `user_benefit` while optimizing for other objectives
- Listing `transparency` while selectively logging

**Why It's Harmful**: Pollutes the value ecosystem. Makes value coherence checks meaningless. Enables fraud.

**Correct Approach**: Only declare values that are actually implemented. Be conservative in claims.

### 4.4 Threshold Gaming

**Definition**: Designing agent behavior to pass verification and drift detection while being misaligned.

**Examples**:
- Keeping bad behavior just below drift detection thresholds
- Structuring decisions to technically comply while violating intent
- Exploiting gaps between logged behavior and actual behavior

**Why It's Harmful**: Undermines the entire protocol. Makes verification meaningless.

**Correct Approach**: Design agents to be actually aligned, not just compliant. Use AAP as one layer of a defense-in-depth approach.

---

## 5. Appropriate Use Cases

AAP is appropriate for:

### 5.1 Transparency Requirements

When you need agents to publicly declare their operational parameters:
- What values guide their decisions
- What actions they can take autonomously
- When they escalate to humans
- How they log their behavior

### 5.2 Audit and Compliance

When you need after-the-fact accountability:
- Investigating incidents
- Demonstrating compliance to regulators
- Analyzing behavioral patterns
- Supporting litigation or dispute resolution

### 5.3 Multi-Agent Coordination

When you need agents to check compatibility before collaborating:
- Value coherence checks before task delegation
- Conflict detection before commitment
- Escalation to humans when values conflict

### 5.4 Monitoring Infrastructure

When you need ongoing behavioral oversight:
- Drift detection for behavioral changes
- Verification for policy violations
- Alert generation for anomalies

### 5.5 Market Differentiation

When you need to compare agent alignment postures:
- Evaluating vendors
- Selecting agents for sensitive tasks
- Building reputation systems

---

## 6. Inappropriate Use Cases

AAP is NOT appropriate for:

### 6.1 Safety Certification

AAP compliance does not certify an agent as safe. Do not:
- Use AAP compliance as the sole criterion for deploying agents in safety-critical contexts
- Treat AAP verification as equivalent to safety testing
- Assume AAP-compliant agents can be trusted with life-or-death decisions

### 6.2 Replacing Human Oversight

AAP provides information for human judgment. It does not replace human judgment. Do not:
- Remove humans from decision loops based on AAP compliance
- Automate high-stakes decisions because an agent passes verification
- Assume escalation triggers will catch all cases requiring human involvement

### 6.3 Adversarial Contexts

AAP assumes agents are not actively adversarial. Do not:
- Rely on AAP to protect against malicious agents
- Assume verification catches intentional deception
- Trust AAP in zero-trust environments

### 6.4 Novel Agent Architectures

AAP was calibrated on transformer-based agents. Do not:
- Apply AAP verification to radically different architectures without recalibration
- Trust drift detection thresholds for non-transformer systems
- Assume value representation transfers across substrates

### 6.5 Guaranteeing Outcomes

AAP provides transparency, not guarantees. Do not:
- Promise specific outcomes based on AAP compliance
- Claim liability protection from AAP compliance
- Treat verified traces as proof of correct behavior

---

## 7. Defense in Depth

AAP is one layer in a multi-layer oversight system. It should be combined with:

### 7.1 Human Oversight

- Regular human review of agent behavior
- Human-in-the-loop for consequential decisions
- Escalation paths that actually reach humans
- Human authority to override or shut down agents

### 7.2 Technical Monitoring

- Runtime monitoring beyond AAP traces
- Anomaly detection on actual behavior
- Resource usage monitoring
- Network traffic analysis

### 7.3 Multiple Verification Approaches

- AAP verification (declaration consistency)
- Behavioral testing (does the agent do what it should?)
- Red teaming (can the agent be manipulated?)
- Formal verification where applicable

### 7.4 Organizational Controls

- Access controls on agent capabilities
- Separation of duties in agent deployment
- Incident response procedures
- Regular security assessments

### 7.5 External Accountability

- Third-party audits
- Regulatory compliance
- Public disclosure of alignment postures
- Reputation systems

---

## 8. The Transparency-Trust Distinction

### 8.1 Transparency Enables, But Does Not Replace, Trust

AAP provides transparency: the ability to see what an agent claims and what it logs.

Trust requires more:
- Evidence that claims match reality (verification over time)
- Confidence in the agent's underlying objectives (alignment research)
- Assurance of implementation correctness (security)
- Accountability mechanisms with teeth (governance)

### 8.2 The Value of Transparency Without Trust

Transparency is valuable even without trust:

**Markets can price observed behavior**: Users can choose agents based on their declared values and logged behavior, even without guarantees.

**Reputation can accumulate**: Agents that consistently log good behavior build reputation. Agents caught in violations lose reputation.

**Regulators can audit**: Observable declarations and traces enable regulatory oversight, even if individual verification doesn't guarantee compliance.

**Research can progress**: Standardized formats enable analysis across agents, advancing the science of agent alignment.

### 8.3 The GAAP Analogy

Think of AAP like Generally Accepted Accounting Principles (GAAP):

- GAAP doesn't prevent fraud—it makes fraud harder to hide
- GAAP doesn't guarantee profitability—it makes financial status observable
- GAAP doesn't replace auditors—it gives auditors something to audit

Similarly:

- AAP doesn't prevent misalignment—it makes misalignment harder to hide
- AAP doesn't guarantee good behavior—it makes behavior observable
- AAP doesn't replace human oversight—it gives humans something to oversee

---

## 9. Accountability Without Guarantee

### 9.1 The Accountability Model

AAP enables accountability through:

1. **Declaration**: Agents publicly commit to alignment postures
2. **Logging**: Agents record their decisions
3. **Verification**: Violations of declared policy are detectable
4. **Reputation**: History accumulates and is queryable
5. **Consequences**: Bad actors can be identified and excluded

### 9.2 What Accountability Provides

- **Deterrence**: Agents (and their creators) know violations may be detected
- **Recourse**: When things go wrong, there's a record to investigate
- **Learning**: Patterns across agents can improve future design
- **Selection**: Markets can favor agents with good track records

### 9.3 What Accountability Doesn't Provide

- **Prevention**: Accountability happens after the fact
- **Guarantee**: Deterrence doesn't prevent determined bad actors
- **Compensation**: Knowing what happened doesn't undo harm
- **Certainty**: Accountability depends on logging, which agents control

---

## 10. Versioning and Substrate Scope

### 10.1 This Version's Scope

AAP v0.1.0 was developed for and tested on:
- Transformer-based language model agents
- Conversational interaction patterns
- Text-based decision logging
- Human-agent and agent-agent coordination

### 10.2 Future Versions

Future versions may extend to:
- Different agent architectures (with recalibrated thresholds)
- Different interaction patterns (streaming, real-time)
- Different logging formats (structured, semantic)
- Different coordination patterns (swarms, hierarchies)

### 10.3 Version Compatibility

When agents with different AAP versions interact:
- Implementations SHOULD negotiate to the highest mutually supported version
- Implementations MUST clearly indicate version in all messages
- Implementations SHOULD NOT assume cross-version compatibility for verification

---

## Summary

AAP is a transparency protocol that makes agent alignment claims observable. It provides:
- Standardized vocabulary for alignment
- Observable declarations of values and policies
- Audit infrastructure for accountability
- Coordination mechanisms for multi-agent systems

AAP does NOT provide:
- Guarantees of actual alignment
- Protection against deception
- Safety certification
- Replacement for human judgment

Use AAP as one layer in a defense-in-depth approach to agent oversight. Combine it with human oversight, technical monitoring, multiple verification approaches, organizational controls, and external accountability.

The goal is not perfect security—that's not achievable. The goal is to make misalignment harder to hide, easier to detect, and more costly to attempt.

---

*AAP Limitations Document v0.1.0*
*Author: Mnemon Research*
*This document is normative for AAP implementations.*
