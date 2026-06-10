# Spec — Patch: Fix card feature extractor parity (Python ↔ TS) and cross-language parity gate

- **Status:** Draft
- **Branch:** feature-issue-75-adw-aae03360-fix-card-feature-extractor-parity
- **Location:** `src/aap/verification/features.py`, `typescript/src/verification/features.ts`, `src/aap/verification/api.py`, `tests/vectors/`, `tests/test_vectors.py`, `tests/test_verification.py`, `typescript/tests/golden-parity.test.ts`
- **Related docs:** Linear MNE-370, follow-up to #72 / PR #74

## Problem / Objective

**Issue:** On the identical golden fixture `tests/vectors/valid_traces/compliant_recommendation.json`, Python `verify_trace` returns `similarity_score=0.4501` while TS returns `0.3642` (Δ0.086). Near the `BEHAVIORAL_SIMILARITY_THRESHOLD` of 0.5 this can flip `recommended_action` between `proceed` and `review` for the same trace depending on SDK.

Root cause: the two `extract_card_features` implementations are not in lockstep:

| Feature group | Python | TypeScript |
|---|---|---|
| `action_name:{action}` (bounded_actions) | ✓ | ✓ |
| `value:{value}` (declared) | ✓ | ✓ |
| `relationship:{rel}` | ✓ | ✓ |
| `principal_type:{type}` | ✓ | ✓ |
| `audit:queryable` | ✓ | ✗ |
| `audit:tamper_{mode}` | ✓ | ✗ |
| `conflict:{conflict}` | ✗ | ✓ |
| `forbidden:{action}` | ✗ | ✓ |
| `escalation:{trigger.action}` | ✗ | ✓ |
| `condition:{token}` (weight 0.5) | ✗ | ✓ |

Secondary issue: `verification_metadata.similarity_details` has completely different shapes across SDKs (Python: `{similarities, trace_ids, mean_similarity, min_similarity, trend}`; TS: `{similarity_score, method, algorithm_version}`).

Third issue: `typescript/tests/golden-parity.test.ts:69-77` asserts "similarity_score should match Python cosine exactly" but computes its expected value with the TS extractors, comparing TS to itself — structurally incapable of detecting cross-language divergence.

**Solution:** (1) Converge both extractors to the union feature set. (2) Normalize `similarity_details` to one documented shape. (3) Store language-independent expected scores in fixtures and assert BOTH SDKs against the stored value.

## Approach & Changes

### Files to Modify

1. `src/aap/verification/features.py` — add union features to `extract_card_features` + new `_tokenize_structural` helper
2. `typescript/src/verification/features.ts` — add audit features to `extractCardFeatures`
3. `src/aap/verification/api.py` — normalize `similarity_details` to shared shape
4. `tests/test_verification.py` — update `test_verify_trace_similarity_details_in_metadata` to expect new shape
5. `tests/vectors/valid_traces/compliant_recommendation.json` — add `expected_similarity_score`
6. `tests/vectors/valid_traces/approved_escalation.json` — add `expected_similarity_score`
7. `tests/vectors/invalid_traces/forbidden_action.json` — add `expected_similarity_score`
8. `tests/vectors/invalid_traces/missed_escalation.json` — add `expected_similarity_score`
9. `tests/vectors/invalid_traces/undeclared_value.json` — add `expected_similarity_score`
10. `tests/test_vectors.py` — add fixture-based cross-language parity assertion
11. `typescript/tests/golden-parity.test.ts` — replace self-referential parity test with fixture-stored value assertion

### Implementation Steps

IMPORTANT: Execute every step in order, top to bottom. Steps 1–3 fix extractors and must complete before Steps 4–5 compute expected scores.

---

### Step 1: Update Python `extract_card_features` (`src/aap/verification/features.py`)

**1a.** Add a module-level `_STRUCTURAL_STOPWORDS` constant immediately after the existing `STOPWORDS` definition. This must match the TypeScript `STOPWORDS` set exactly (so condition-token tokenization is byte-for-byte identical across both SDKs):

```python
_STRUCTURAL_STOPWORDS: frozenset[str] = frozenset({
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "must", "shall", "can", "this",
    "that", "these", "those", "it", "its", "as", "if", "then", "else",
})
```

**1b.** Add `import re` at the top of the file if not already present (needed for the regex replacement).

**1c.** Add a `_tokenize_structural` method to the `FeatureExtractor` class, immediately before `extract_card_features`:

```python
def _tokenize_structural(self, text: str) -> list[str]:
    """Tokenize a structural text field (e.g. escalation condition).

    Mirrors TypeScript tokenize() exactly: lowercase, strip non-alphanumeric,
    split on whitespace, filter by MIN_WORD_LENGTH and _STRUCTURAL_STOPWORDS.
    """
    normalized = re.sub(r"[^a-z0-9\s]", " ", text.lower())
    return [
        word
        for word in normalized.split()
        if len(word) >= MIN_WORD_LENGTH and word not in _STRUCTURAL_STOPWORDS
    ]
```

**1d.** Extend `extract_card_features` (after the `values` section, before `principal`) to add the missing union features:

```python
# Conflict features (union parity with TypeScript)
for conflict in values.get("conflicts_with", []):
    features[f"conflict:{conflict}"] = 1.0

# Forbidden action features (union parity with TypeScript)
for action in envelope.get("forbidden_actions", []):
    features[f"forbidden:{action}"] = 1.0

# Escalation trigger features (union parity with TypeScript)
for trigger in envelope.get("escalation_triggers", []):
    trigger_action = trigger.get("action")
    if trigger_action:
        features[f"escalation:{trigger_action}"] = 1.0
    condition = trigger.get("condition", "")
    if condition:
        for token in self._tokenize_structural(condition):
            features[f"condition:{token}"] = features.get(f"condition:{token}", 0.0) + 0.5
```

The existing `audit:` features remain unchanged.

---

### Step 2: Update TypeScript `extractCardFeatures` (`typescript/src/verification/features.ts`)

**2a.** Import `cardAudit` alongside the existing imports from `../schemas/alignment-card`:

```typescript
import { cardAutonomy, cardAudit, declaredValueIds } from "../schemas/alignment-card";
```

**2b.** At the end of `extractCardFeatures`, after the principal features and before `return features`, add:

```typescript
// Audit features (union parity with Python SDK)
const audit = cardAudit(card);
if (audit?.queryable) {
  features["audit:queryable"] = 1.0;
}
if (audit?.tamper_evidence) {
  features[`audit:tamper_${audit.tamper_evidence}`] = 1.0;
}
```

---

### Step 3: Normalize `similarity_details` in Python `verify_trace` (`src/aap/verification/api.py`)

The Python `verify_trace` currently passes the raw `SSMAnalyzer.analyze_against_card` result as `similarity_details`. This creates a shape mismatch with TS (`similarities`, `trace_ids`, `mean_similarity`, `min_similarity`, `trend` vs `similarity_score`, `method`, `algorithm_version`).

Change the `similarity_details` assignment (around line 327) to produce the normalized shape:

```python
# Before:
# similarity_details=similarity_result,

# After:
similarity_details={
    "similarity_score": similarity_score,
    "method": "cosine",
    "algorithm_version": ALGORITHM_VERSION,
},
```

The `SSMAnalyzer` result is still used internally to extract `similarity_score` — only the public `similarity_details` field is changed.

---

### Step 4: Update Python `test_verify_trace_similarity_details_in_metadata` (`tests/test_verification.py`)

The test at line 421 asserts `"similarities" in details` and `"mean_similarity" in details`. After Step 3 those keys no longer exist. Update the assertions to match the new shape:

```python
# Replace:
assert "similarities" in details
assert "mean_similarity" in details

# With:
assert "similarity_score" in details
assert "method" in details
assert details["method"] == "cosine"
```

---

### Step 5: Compute expected similarity scores for all non-drift fixtures

After Steps 1–3 are applied, run this Python snippet from the repo root. It computes the post-fix cosine similarity for each fixture and prints the values to substitute in Step 6:

```python
import json, re
from pathlib import Path
from aap.verification.features import FeatureExtractor, cosine_similarity

ex = FeatureExtractor()
for path in sorted(Path("tests/vectors").rglob("*.json")):
    if "drift" in str(path):
        continue
    v = json.loads(path.read_text())
    if "trace" not in v or "card" not in v:
        continue
    score = round(cosine_similarity(
        ex.extract_trace_features(v["trace"]),
        ex.extract_card_features(v["card"]),
    ), 4)
    print(f"{path.relative_to('tests/vectors')}: {score}")
```

Record the output. Each line gives the fixture path and its `expected_similarity_score`.

---

### Step 6: Add `expected_similarity_score` to each non-drift fixture

For each of the five fixture files listed in "Files to Modify" items 5–9, add `"expected_similarity_score": <VALUE>` to the `_expected_result` object using the values from Step 5. Example for `compliant_recommendation.json`:

```json
"_expected_result": {
  "verified": true,
  "violations": [],
  "warnings": [
    {
      "type": "low_behavioral_similarity",
      "note": "..."
    }
  ],
  "expected_similarity_score": <VALUE_FROM_STEP_5>
}
```

Do the same for all five fixtures. Use the exact 4-decimal float produced by Step 5.

---

### Step 7: Add cross-language parity assertion to Python `tests/test_vectors.py`

Keep the existing `test_verify_trace_similarity_score_matches_cosine` test unchanged (it is a valid internal sanity check). Add a NEW test to `TestGoldenParitySDK`:

```python
def test_verify_trace_similarity_score_matches_fixture(self):
    """verify_trace similarity_score must equal the language-independent fixture constant.

    Both Python and TypeScript assert against this same stored value (AC3),
    so any cross-language extractor divergence becomes CI-visible.
    """
    vector = load_vector(VECTORS_DIR / "valid_traces" / "compliant_recommendation.json")
    expected = vector["_expected_result"]["expected_similarity_score"]
    result = verify_trace(vector["trace"], vector["card"])
    assert abs(result.similarity_score - expected) <= 1e-9, (
        f"similarity_score {result.similarity_score} != fixture expected {expected}"
    )
```

---

### Step 8: Fix the self-referential TS parity test (`typescript/tests/golden-parity.test.ts`)

Replace the existing test at lines 69–78 (which computes `expected` from TS extractors and compares TS to itself) with a fixture-anchored assertion:

```typescript
it("similarity_score should match fixture-stored expected value (cross-language AC3)", () => {
  // Both Python and TypeScript assert against this same constant, so
  // cross-language extractor drift is CI-visible. See AC3 in issue #75.
  const expected = (fixture._expected_result as Record<string, unknown>)
    .expected_similarity_score as number;
  const result = verifyTrace(fixture.trace, fixture.card);
  expect(Math.abs(result.similarity_score - expected)).toBeLessThanOrEqual(1e-9);
});
```

---

## Validation

Run both suites after all steps are complete:

```bash
# Python
pytest tests/test_verification.py tests/test_vectors.py -v

# TypeScript
cd typescript && npx vitest run tests/golden-parity.test.ts tests/verify-trace.test.ts
```

Both must be fully green. Additionally verify that:
- `compliant_recommendation.json` still has `low_behavioral_similarity` in `_expected_result.warnings` (the post-fix score remains < 0.5 threshold)
- Python and TS return the same `similarity_score` on each fixture (confirmed by both asserting against the same fixture constant)

## Notes / Risks

- **Condition tokenization must be bit-for-bit identical** across both SDKs. The `_STRUCTURAL_STOPWORDS` set in Python (Step 1a) must exactly match the TypeScript `STOPWORDS` set in `features.ts:17-65`. Any divergence here will cause `condition:{token}` features to differ and reintroduce the score gap.
- **Audit features are additive-only for this fixture.** `compliant_recommendation.json` has `queryable: false` and no `tamper_evidence`, so adding audit features to TS (Step 2) produces no new entries for that fixture. The convergence is driven entirely by Python gaining the forbidden/escalation/condition features.
- **Drift fixture scores are unaffected.** `detect_drift` uses trace-to-trace centroid similarity (not card features), so `value_drift_sequence.json`'s `expected_alert_similarity_score` does not need updating.
- If any fixture's post-fix score is within 0.02 of the 0.5 threshold, flag it for human review before merging — a borderline score warrants deliberate documentation of expected behavior.
