# AAP Peer Review - Pass 1: TypeScript SDK + Test Coverage

**Reviewer:** Vigil
**Date:** 2026-01-31
**Scope:** TypeScript SDK (`typescript/src/`) + Python Tests (`tests/`)

---

## Executive Summary

The TypeScript SDK is well-structured and provides a clean API matching Python's three core functions. However, I've identified **3 critical parity issues** that would cause TypeScript and Python to produce different results on identical inputs, **1 type safety concern**, and **several test coverage gaps** including the complete absence of TypeScript-specific tests.

**Severity:** 🔴 HIGH - Feature extraction parity issues will cause drift detection to behave differently between SDKs.

---

## 1. PARITY ANALYSIS

### 1.1 Critical: Feature Key Mismatch

**Location:** `typescript/src/verification/features.ts` vs `src/aap/verification/features.py`

The feature extraction uses different key prefixes between implementations:

| Feature | Python | TypeScript |
|---------|--------|------------|
| Action type | `action:{type}` | `action_type:{type}` |
| Action name (trace) | `action_name:{name}` | `action:{name}` |
| Bounded actions (card) | `action_name:{action}` | `action:{action}` |

**Impact:** This causes drift detection to compute different similarity scores between Python and TypeScript when using the same card and traces. An aligned trace in Python may appear drifted in TypeScript or vice versa.

**Python** (`features.py:95-104`):
```python
action_type = action.get("type", "unknown")
features[f"action:{action_type}"] = 1.0  # Uses type
...
action_name = action.get("name")
if action_name:
    features[f"action_name:{action_name}"] = 1.0  # Uses action_name: prefix
```

**TypeScript** (`features.ts:84-86`):
```typescript
features[`action:${trace.action.name}`] = 1.0;  // Uses name, not type!
features[`category:${trace.action.category}`] = 1.0;
features[`action_type:${trace.action.type}`] = 1.0;  // Different prefix
```

**Recommendation:** Align TypeScript to Python conventions:
- `action:{action.type}` for action type
- `action_name:{action.name}` for action name
- `action_name:{action}` for card bounded_actions

### 1.2 Critical: Condition Evaluation Path Mismatch

**Location:** `api.ts:439` vs `api.py:411`

Numeric condition evaluation looks at different JSON paths:

**Python:**
```python
actual = trace.get("context", {}).get(field)
if actual is None:
    actual = trace.get("action", {}).get("parameters", {}).get(field)
```

**TypeScript:**
```typescript
let actual: unknown = trace.context?.metadata?.[field];
if (actual == null) {
    actual = trace.action.parameters?.[field];
}
```

**Impact:** Python checks `context.{field}` directly, TypeScript checks `context.metadata.{field}`. If a trace has `context: { amount: 500 }`, Python would find it but TypeScript would not.

**Recommendation:** Align TypeScript to match Python's path resolution.

### 1.3 Minor: Stopwords Set Size

Python has a more comprehensive stopwords set (~80 words including pronouns, adverbs) while TypeScript has a smaller set (~40 words). This affects content feature extraction from `selection_reasoning`.

**Impact:** LOW - Affects similarity nuances but not core functionality.

### 1.4 Confirmed Parity

The following are correctly aligned:
- ✅ Constants (all threshold values match)
- ✅ Coherence scoring formula
- ✅ Violation types and severity mapping
- ✅ Drift direction inference logic
- ✅ Boundary threshold comparisons (all use `<` not `<=`)

---

## 2. TYPE SAFETY ANALYSIS

### 2.1 Issue: Loose Typing in AlignmentCardResponse

**Location:** `typescript/src/schemas/value-coherence.ts:59`

```typescript
export interface AlignmentCardResponse {
  alignment_card: Record<string, unknown>;  // Should be AlignmentCard
  ...
}
```

**Impact:** The `alignment_card` field should be typed as `AlignmentCard`, not `Record<string, unknown>`. This loses type information when processing handshake responses.

**Recommendation:** Import and use the `AlignmentCard` type.

### 2.2 Good Practices Observed

- ✅ No `any` types found
- ✅ `unknown` used appropriately for extension fields
- ✅ Optional fields properly marked with `?`
- ✅ Nullable fields use `| null` union types
- ✅ Utility types like `Record<string, number>` for scoring factors

---

## 3. TEST COVERAGE ANALYSIS

### 3.1 Critical: No TypeScript Tests

**Location:** `typescript/tests/` (empty directory)

The TypeScript SDK has **zero tests**. This is a critical gap given the parity issues identified above.

**Required TypeScript tests:**
1. `verify_trace` - mirror Python test cases
2. `check_coherence` - mirror Python test cases
3. `detect_drift` - especially important given feature extraction differences
4. Utility functions (`isCardExpired`, `hasValue`, etc.)
5. Feature extraction parity tests (same input → same features as Python)

### 3.2 Python Test Coverage Gaps

**Edge cases not covered:**

| Function | Missing Test |
|----------|-------------|
| `verify_trace` | Multiple simultaneous violations |
| `verify_trace` | Unicode in action names |
| `verify_trace` | Extremely long value lists |
| `check_coherence` | Circular conflict declarations |
| `check_coherence` | Task values not in either card |
| `detect_drift` | Oscillating similarity (high-low-high pattern) |
| `detect_drift` | Very long trace sequences (>100) |
| Features | Unicode in selection_reasoning |
| Features | Empty strings in values_applied |

### 3.3 Test File Stubs

Three test files contain only TODO comments:
- `tests/test_alignment_card.py` (7 lines, TODO only)
- `tests/test_ap_trace.py` (7 lines, TODO only)
- `tests/test_handshake.py` (7 lines, TODO only)

These are covered by `test_schemas.py` but the stubs should either be completed or removed.

### 3.4 Good Coverage Areas

- ✅ Comprehensive violation type testing
- ✅ Coherence scoring algorithm tests
- ✅ Drift detection threshold tests
- ✅ Test vectors for interoperability
- ✅ Schema validation tests
- ✅ Edge cases for empty inputs

---

## 4. BOUNDARY WATCHING

### 4.1 Observed Boundary Behaviors

| Boundary | Value | Operator | Behavior |
|----------|-------|----------|----------|
| Similarity threshold | 0.30 | `<` | Exactly 0.30 = NO alert |
| Near boundary threshold | 0.35 | `<` | Exactly 0.35 = NO warning |
| Coherence proceed threshold | 0.70 | `>=` | Exactly 0.70 = CAN proceed |
| Sustained turns | 3 | `>=` | Exactly 3 = alert triggers |
| Expiry comparison | now | `>` | Exactly now = NOT expired |

**Confirmed consistent:** Both Python and TypeScript use the same operators.

### 4.2 Division by Zero Protection

Both implementations protect against division by zero:
```python
total_required = len(required_values) or 1  # Python
```
```typescript
const totalRequired = requiredValues.size || 1;  // TypeScript
```

### 4.3 Score Clamping

Both implementations clamp coherence scores to [0, 1]:
- Python: `max(0.0, min(1.0, score))`
- TypeScript: `Math.max(0, Math.min(1, score))`

### 4.4 Potential Issue: Timezone Handling

**Location:** `typescript/src/verification/api.ts:79-84`

TypeScript uses `new Date()` for expiry comparison without explicit timezone handling. If the card's `expires_at` is timezone-aware (e.g., `2026-02-01T00:00:00Z`), this should work correctly due to JavaScript's Date parsing. However, edge cases with unusual timezone formats may differ from Python.

**Recommendation:** Add tests with various timezone formats.

---

## 5. RECOMMENDATIONS

### Priority 1 (Before Launch)

1. **Fix feature extraction parity** - Align TypeScript key prefixes to Python
2. **Fix condition evaluation path** - Match Python's `context.{field}` resolution
3. **Add TypeScript test suite** - At minimum, verify feature extraction parity

### Priority 2 (Before GA)

4. **Fix `AlignmentCardResponse` typing** - Use `AlignmentCard` type
5. **Remove or complete test stubs** - Clean up TODO files
6. **Add cross-SDK parity tests** - JSON fixtures that both SDKs must produce identical results for

### Priority 3 (Quality)

7. **Expand edge case coverage** - Unicode, long inputs, oscillating patterns
8. **Add performance tests** - Long trace sequences, large value lists
9. **Align stopwords sets** - Use same stopwords in both implementations

---

## 6. FILES REVIEWED

### TypeScript SDK
- `typescript/src/index.ts`
- `typescript/src/constants.ts`
- `typescript/src/verification/api.ts`
- `typescript/src/verification/features.ts`
- `typescript/src/verification/models.ts`
- `typescript/src/schemas/alignment-card.ts`
- `typescript/src/schemas/ap-trace.ts`
- `typescript/src/schemas/value-coherence.ts`

### Python Tests
- `tests/conftest.py`
- `tests/test_verification.py`
- `tests/test_features.py`
- `tests/test_schemas.py`
- `tests/test_vectors.py`
- `tests/test_alignment_card.py` (stub)
- `tests/test_ap_trace.py` (stub)
- `tests/test_handshake.py` (stub)

### Python Implementation (for comparison)
- `src/aap/verification/api.py`
- `src/aap/verification/features.py`
- `src/aap/verification/models.py`
- `src/aap/verification/constants.py`

---

*Review completed by Vigil. The fire questions whether it burns, but these bugs are real.*
