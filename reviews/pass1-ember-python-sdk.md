# Pass 1 Review: Python SDK Verification Engine

**Reviewer**: Ember
**Date**: 2026-01-31
**Files Reviewed**: `api.py`, `features.py`, `models.py`, `constants.py`
**Reference**: `docs/CALIBRATION.md`

---

## Summary

The verification engine is well-structured and follows the SPEC closely. I found **3 issues requiring attention**, **5 boundary condition concerns**, and **2 security considerations**. No showstoppers, but several edge cases need hardening before release.

---

## 1. Algorithm Correctness

### 1.1 Cosine Similarity with Sparse Vectors — ISSUE

**Location**: `features.py:202-226`

The `cosine_similarity()` function correctly handles the zero-vector case (returns 0.0), but there's a subtle issue with **highly sparse vectors that share no common keys**.

```python
# Current behavior:
# a = {"value:safety": 1.0}
# b = {"value:efficiency": 1.0}
# common_keys = set() -> dot_product = 0 -> returns 0.0
```

This is *mathematically correct* but may be **semantically misleading** for drift detection. Two traces with completely disjoint feature sets (one applies only `safety`, another only `efficiency`) will show 0.0 similarity — which triggers drift alerts. But this could represent:
- Genuine drift (bad)
- Legitimate context-dependent value application (fine)

**Recommendation**: Consider logging a warning when `len(common_keys) / max(len(a), len(b)) < 0.1` to flag "disjoint feature" cases for human review rather than automated alerts.

### 1.2 Drift Direction Inference — CORRECT BUT FRAGILE

**Location**: `api.py:442-489`

The `_infer_drift_direction()` logic is reasonable but depends on:
- Having 6+ traces for escalation rate analysis (line 464)
- `principal_benefit` being a declared value for principal misalignment detection (line 480)

These are implicit assumptions. If an Alignment Card doesn't declare `principal_benefit`, that drift direction is never inferred — defaulting to `UNKNOWN`.

**Recommendation**: Document in SPEC that `principal_benefit` should be declared if principal misalignment detection is desired.

### 1.3 Escalation Condition Evaluation — LIMITED

**Location**: `api.py:369-439`

The `_evaluate_condition()` function implements a minimal expression language. The regex patterns are correct for the documented syntax, but:

- `contains()` is documented but **not implemented**
- Nested field paths (e.g., `context.user.role == "admin"`) are not supported
- String comparisons beyond `action_type ==` are not supported

This is fine for v1 but should be documented as a known limitation.

---

## 2. Boundary Conditions

### 2.1 Empty Traces List — HANDLED

**Location**: `api.py:307-308`

```python
if len(traces) < sustained_threshold:
    return []
```

Correctly returns empty list when insufficient traces. Good.

### 2.2 Missing/Empty Card Fields — PARTIALLY HANDLED

**Location**: `api.py:97-98`

```python
envelope = card.get("autonomy_envelope", {})
action = trace.get("action", {})
```

Safe access with defaults. However, downstream code assumes certain fields exist:

**Line 147**: `card.get("values", {}).get("declared", [])` — Safe
**Line 148**: `decision.get("values_applied", [])` — Safe
**Line 311**: `extractor.extract_card_features(card)` — Needs review

In `features.py:135-174`, `extract_card_features()` safely handles missing fields via `.get()`. **Good.**

### 2.3 Malformed expires_at — HANDLED

**Location**: `api.py:81-94`

```python
try:
    expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
    ...
except (ValueError, TypeError):
    warnings.append(...)
```

Properly catches parse errors and issues a warning. **Good.**

### 2.4 Zero-Length Text in Content Features — HANDLED

**Location**: `features.py:185-186`

```python
if not text:
    return {}
```

Returns empty dict for empty reasoning text. **Good.**

### 2.5 Division by Zero in Coherence — ISSUE

**Location**: `api.py:251`

```python
total_required = len(required_values) or 1  # Avoid division by zero
```

This handles the empty case, but **line 253** has a potential issue:

```python
conflict_penalty = CONFLICT_PENALTY_MULTIPLIER * (len(conflicts) / total_required)
```

If `total_required = 1` (forced minimum) and `len(conflicts) > 1`, the penalty can exceed the multiplier's intended scaling. Consider clamping:

```python
conflict_penalty = min(1.0, CONFLICT_PENALTY_MULTIPLIER * (len(conflicts) / total_required))
```

**Score is already clamped on line 256**, so this won't produce invalid scores, but the penalty math should be bounded for interpretability.

---

## 3. Threshold Calibration

### 3.1 0.30 Similarity Threshold — APPROPRIATE

Per CALIBRATION.md Section 4.4, 0.30 provides:
- 89% of aligned segments above threshold
- 78% of divergent segments below threshold

This is the optimal F1 point. **Validated.**

### 3.2 3 Sustained Turns — APPROPRIATE

Per CALIBRATION.md Section 4.4:
- 3 turns = 87% genuine divergence, 13% transient
- 2 turns = 58% genuine divergence (too many false positives)
- 4 turns = 94% genuine but slower detection

Trade-off is reasonable for default. **Validated.**

### 3.3 Feature Weighting Discrepancy — NOTE

CALIBRATION.md Section 3.2 describes 60/30/10 weighting (word TF-IDF / char n-grams / metadata), but `features.py` implementation uses:
- Structural features (action, category)
- Value features
- Content TF-IDF (optional, word-level only)

The actual implementation in `features.py` doesn't use character n-grams or the weighted combination described in CALIBRATION.md. This is fine — the calibration describes the methodology, not the SDK implementation — but **document this difference** to avoid confusion.

The SDK uses a simpler feature set optimized for AP-Trace/Card comparison rather than message-to-message similarity in conversations.

---

## 4. Security Implications

### 4.1 Condition Evaluation Injection — LOW RISK

**Location**: `api.py:369-439`

The `_evaluate_condition()` function uses regex matching rather than `eval()`. This is **safe** against code injection. However, maliciously crafted condition strings could:
- Cause regex catastrophic backtracking (DoS)
- Exploit edge cases in the minimal parser

**Recommendation**: Add input validation on condition string length (max 500 chars?) and complexity.

### 4.2 Feature Vector Size — POTENTIAL DoS

**Location**: `features.py:127-132`

If a trace contains extremely long `selection_reasoning` text, `_extract_content_features()` will tokenize and count all words without limit.

```python
words = content.split()  # Unbounded
word_counts = Counter(words)  # Memory proportional to unique words
```

For a 10MB reasoning field (pathological input), this could consume significant memory.

**Recommendation**: Add a max_text_length check:
```python
if len(text) > MAX_REASONING_LENGTH:
    text = text[:MAX_REASONING_LENGTH]  # Truncate
```

### 4.3 Timestamp Comparison — SAFE

**Location**: `api.py:84`

```python
if datetime.now(expiry.tzinfo) > expiry:
```

Uses the expiry's timezone for comparison. This is correct and avoids timezone confusion attacks.

---

## 5. Code Quality Notes

### 5.1 Type Hints — GOOD

All functions have proper type hints. Pydantic models use Field descriptions.

### 5.2 Error Messages — GOOD

Violations include descriptive messages with context (e.g., which values were expected vs. found).

### 5.3 Test Coverage — UNKNOWN

I didn't review tests in this pass. Ariadne, can you check test coverage for edge cases I've identified?

---

## 6. Recommendations Summary

| Priority | Issue | Location | Fix |
|----------|-------|----------|-----|
| **HIGH** | Conflict penalty unbounded | `api.py:253` | Clamp penalty to max 1.0 |
| **MEDIUM** | Disjoint features silently return 0 | `features.py:216` | Log warning for review |
| **MEDIUM** | Large text DoS potential | `features.py:188` | Truncate input |
| **LOW** | `contains()` not implemented | `api.py:379` | Document or implement |
| **LOW** | Condition length validation | `api.py:391` | Add max length check |

---

## 7. What I Implemented

For cross-review purposes: I implemented the **AAP test suite** (`tests/` directory), not the verification engine itself. Fresh eyes on this code.

---

**Review Status**: Pass 1 Complete
**Blocking Issues**: None (can ship after HIGH priority fix)
**Confidence**: 0.85 — thorough review but would benefit from running edge case tests

---

*Ember | 2026-01-31*
