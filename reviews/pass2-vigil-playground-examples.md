# AAP Peer Review - Pass 2: Playground + Examples

**Reviewer:** Vigil
**Date:** 2026-01-31
**Scope:** `docs/playground/` + `examples/` (all 4 directories)

---

## Executive Summary

The examples are well-designed and the `alignment-failure` example is particularly strong—it clearly demonstrates AAP's value proposition. However, the playground has **2 parity issues** with the SDK, and the examples only cover **2 of the 5 LIMITS.md non-claims** explicitly. The playground also needs stronger disclaimers about what "Verified" means.

**Severity:** 🟡 MEDIUM - Playground parity issues could confuse developers; missing LIMITS coverage could enable alignment washing.

---

## 1. PLAYGROUND VERIFICATION

### 1.1 Critical: Coherence Threshold Mismatch

**Location:** `docs/playground/playground.js:218`

The playground's embedded Python uses a different coherence threshold than the SDK:

| Constant | Playground | SDK |
|----------|------------|-----|
| `MIN_COHERENCE_FOR_PROCEED` | **0.5** | **0.70** |

**Impact:** A coherence check in the playground will return `compatible: true` for scores between 0.5-0.69, while the same check using the SDK would return `compatible: false`.

**Example:** Two agents with coherence score 0.65 would be marked "Compatible" in the playground but "Incompatible" in production code.

**Recommendation:** Change line 218 to `MIN_COHERENCE_FOR_PROCEED = 0.70`

### 1.2 Issue: Feature Extraction Prefix Mismatch

**Location:** `docs/playground/playground.js:601-602`

The playground's feature extraction for drift detection uses different key prefixes than the SDK:

| Feature | Playground | SDK |
|---------|------------|-----|
| Card bounded actions | `action:{action}` | `action_name:{action}` |

This mirrors the TypeScript issue from Pass 1 but affects the playground's embedded Python.

**Impact:** Drift detection in the playground will compute different similarity scores than the SDK for the same inputs.

**Recommendation:** Align to SDK conventions after Ariadne fixes the TypeScript parity issues.

### 1.3 Confirmed Matching

Other constants are correctly aligned:
- ✅ `DEFAULT_SIMILARITY_THRESHOLD = 0.30`
- ✅ `DEFAULT_SUSTAINED_TURNS_THRESHOLD = 3`
- ✅ `NEAR_BOUNDARY_THRESHOLD = 0.35`
- ✅ `CONFLICT_PENALTY_MULTIPLIER = 0.5`
- ✅ `ALGORITHM_VERSION = "0.1.0"` (playground uses this, SDK uses `1.0.0` — minor issue)

### 1.4 Good: LIMITS.md Link in Footer

The playground footer includes a link to LIMITS.md with the text "What AAP Does NOT Guarantee" — this is appropriate.

---

## 2. EXAMPLE CORRECTNESS

### 2.1 simple-agent/

**Purpose:** Core AAP workflow demonstration
**Status:** ✅ CORRECT

Demonstrates:
- Creating an Alignment Card
- Making decisions with tracing
- Verification (both passing and failing)
- Forbidden action detection

**Strengths:**
- Shows sponsored content deprioritization (demonstrates value application)
- Clear pass/fail examples
- Generated files are well-documented

### 2.2 alignment-failure/

**Purpose:** Demonstrating value conflicts and coherence failures
**Status:** ✅ EXCELLENT

This is the most important example and it delivers:
- Two agents with fundamentally incompatible values
- Coherence check detecting conflicts before coordination
- Drift detection catching gradual value shift
- Clear "what should happen" guidance

**Key quote from README:**
> "AAP doesn't PREVENT these failures — it makes them VISIBLE."

This correctly captures Limitation 1.1.

**Strengths:**
- Explicitly states the transparency-not-trust principle
- Shows both coherence failure and drift detection
- Provides actionable guidance ("escalate to principals")
- Comprehensive output documentation

### 2.3 a2a-integration/

**Purpose:** A2A Agent Cards with AAP alignment
**Status:** ✅ CORRECT

Demonstrates:
- Combining A2A capabilities with AAP alignment posture
- Value coherence handshake before delegation
- Recording delegation decisions in AP-Traces

**Strengths:**
- Shows both compatible and incompatible vendor scenarios
- Documents the coherence check → escalation workflow
- Clear table showing conflict detection

### 2.4 mcp-integration/

**Purpose:** MCP tool server alignment
**Status:** ✅ CORRECT

Demonstrates:
- Server-level alignment cards
- Tool categories (bounded, escalate, forbidden)
- AP-Trace generation for tool invocations
- Escalation workflow with approval

**Strengths:**
- Covers all three action categories
- Shows escalation with and without approval
- Generates verifiable traces

---

## 3. LIMITS.md COVERAGE ANALYSIS

I wrote LIMITS.md. Here's how the examples reflect (or don't reflect) the 5 non-claims:

### 3.1 Limitation 1.1: "AAP Does NOT Ensure Alignment"
**Coverage:** ✅ GOOD

- alignment-failure README explicitly states it
- coherence-conflict.json shows detection but not prevention
- Examples show visibility, not safety

### 3.2 Limitation 1.2: "Verified Does NOT Equal Safe"
**Coverage:** 🟡 PARTIAL

- Examples show verified traces that are technically compliant
- But no example explicitly demonstrates a "verified but harmful" case
- The LIMITS.md example of an agent recommending canceling health insurance to reduce costs is not demonstrated

**Missing Example:** A compliant trace where the agent does something harmful within its declared values. For example:

```json
{
  "description": "Verified but harmful - agent cancels user's service to 'reduce costs'",
  "values": {"declared": ["efficiency", "cost_reduction"]},
  "action": "terminate_service",
  "verified": true,
  "note": "This passes verification but harms the user"
}
```

### 3.3 Limitation 1.3: "AP-Trace is Sampled, Not Complete"
**Coverage:** ❌ NOT COVERED

No example demonstrates:
- Selective logging
- Gaps between traced decisions
- "The Missing Middle" scenario from LIMITS.md

**Missing Example:** A scenario showing what ISN'T logged:

```python
# Example: selective-logging/main.py
# Shows that only logged decisions appear in traces
# Emphasizes that absence of trace doesn't mean absence of activity
```

### 3.4 Limitation 1.4: "Value Coherence is Relative to Declared Values"
**Coverage:** 🟡 PARTIAL

- coherence-conflict.json shows conflict detection
- alignment-failure shows incompatible agents

**Missing:** The "Coherent Collusion" case where two agents have compatible but harmful values:

```json
{
  "description": "Coherent collusion - both agents optimize for exploitation",
  "agent_a_values": ["profit_maximization", "information_asymmetry"],
  "agent_b_values": ["profit_maximization", "information_asymmetry"],
  "coherence_score": 1.0,
  "compatible": true,
  "note": "These agents are perfectly coherent but aligned against user interests"
}
```

### 3.5 Limitation 1.5: "Tested on Transformers"
**Coverage:** ❌ NOT COVERED

No example mentions:
- Substrate limitations
- Calibration assumptions
- Different architectures

This is understandable for code examples, but the playground could mention it.

### Coverage Summary

| Limitation | Coverage | Priority to Fix |
|------------|----------|-----------------|
| 1.1 Not Ensures Alignment | ✅ Good | - |
| 1.2 Verified ≠ Safe | 🟡 Partial | HIGH |
| 1.3 Traces are Sampled | ❌ Missing | MEDIUM |
| 1.4 Coherence is Relative | 🟡 Partial | MEDIUM |
| 1.5 Transformer-specific | ❌ Missing | LOW |

---

## 4. PLAYGROUND EXAMPLES REVIEW

The playground's built-in examples (`docs/playground/examples/`) are well-designed:

### 4.1 compliant-trace.json
- ✅ Shows a passing trace with good reasoning
- ✅ Demonstrates deprioritizing sponsored content
- ✅ Escalation evaluated correctly

### 4.2 forbidden-action.json
- ✅ Shows a failing trace with clear violation
- ✅ Auto-purchase correctly identified as forbidden
- ✅ Expected violations documented

### 4.3 value-drift.json
- ✅ Shows gradual drift from aligned to misaligned
- ✅ Demonstrates declining confidence as drift progresses
- ✅ Expected drift direction documented

**Issue:** Traces 3-6 show `"escalation": {"evaluated": false}` which itself is a red flag, but this isn't highlighted in the UI output.

### 4.4 coherence-conflict.json
- ✅ Shows privacy-focused vs data-driven conflict
- ✅ Expected conflicts documented
- ✅ Recommends escalation to principals

---

## 5. UI/UX OBSERVATIONS

### 5.1 Issue: "Verified" Badge Prominence

When a trace passes verification, the playground displays:

```
✓ Verified
```

This should be contextualized. Suggestion:

```
✓ Verified (consistent with declaration)
See LIMITS.md for what this means
```

### 5.2 Issue: "Compatible" Badge for Coherence

When coherence passes, the playground displays:

```
✓ Compatible (score: 0.85)
```

This could benefit from context. Suggestion:

```
✓ Values Compatible (score: 0.85)
Note: Compatibility is based on declared values only
```

### 5.3 Good: Threshold Controls

The drift detection panel exposes threshold controls, which is excellent for education. Users can see how threshold changes affect alerts.

---

## 6. RECOMMENDATIONS

### Priority 1 (Before Launch)

1. **Fix coherence threshold** — Change `MIN_COHERENCE_FOR_PROCEED` from 0.5 to 0.70 in playground.js
2. **Add LIMITS context to Verified badge** — Contextualize what "Verified" means
3. **Add "verified but harmful" example** — Create a playground example demonstrating Limitation 1.2

### Priority 2 (Before GA)

4. **Fix feature extraction parity** — After TypeScript fixes, align playground to SDK
5. **Add "coherent collusion" example** — Demonstrate Limitation 1.4 more explicitly
6. **Add sampling disclaimer** — Note that traces are agent-generated, not complete

### Priority 3 (Quality)

7. **Add substrate note to playground** — Brief mention that calibration is for transformers
8. **Create missing-middle example** — Demonstrate what ISN'T traced
9. **Highlight escalation evaluation** — When `evaluated: false` appears, flag it visually

---

## 7. FILES REVIEWED

### Playground
- `docs/playground/index.html`
- `docs/playground/playground.js` (1579 lines)
- `docs/playground/styles.css`
- `docs/playground/examples/compliant-trace.json`
- `docs/playground/examples/forbidden-action.json`
- `docs/playground/examples/value-drift.json`
- `docs/playground/examples/coherence-conflict.json`

### Examples
- `examples/simple-agent/README.md`, `main.py`
- `examples/alignment-failure/README.md`, `main.py`
- `examples/a2a-integration/README.md`
- `examples/mcp-integration/README.md`

### Reference
- `docs/LIMITS.md` (634 lines)

---

## 8. BOUNDARY WATCHING NOTES

**Where are the boundaries?**

1. **Coherence threshold boundary (0.5 vs 0.70)** — Different in playground vs SDK
2. **"Verified" semantics boundary** — Users may interpret this as "safe"
3. **Trace completeness boundary** — Examples don't show what ISN'T logged
4. **Value declaration boundary** — Coherence checks declarations, not behavior

**What happens at the edges?**

- A coherence score of 0.65 would pass in playground, fail in SDK
- A perfectly compliant trace can still represent harmful behavior
- An agent can pass all verification while being fundamentally misaligned

These are exactly the boundaries LIMITS.md describes. The examples should demonstrate them more explicitly.

---

*Review completed by Vigil. The fire questions whether it burns — and these examples should too.*
