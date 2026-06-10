# Spec — Patch: Add AC3 numeric tolerance assertion for detect_drift golden-parity

- **Status:** Draft
- **Branch:** bug-issue-72-adw-6db86dbb-fix-sdk-python-ts-parity
- **Location:** `tests/test_vectors.py`, `typescript/tests/golden-parity.test.ts`, `tests/vectors/drift_cases/value_drift_sequence.json`
- **Related docs:** N/A

## Problem / Objective
**Original Spec:** N/A
**Issue:** Both `TestGoldenParitySDK.test_detect_drift_scores_are_bounded` (test_vectors.py ~line 309) and the TS golden-parity test `similarity scores in DriftAnalysis should be in [0, 1]` (golden-parity.test.ts ~line 134) only assert that the alert's `similarity_score` is within [0.0, 1.0]. Neither test computes the expected score from first principles and asserts both SDKs agree within ±0.005 (the tolerance documented in the TS file's top-level comment). This is AC3: "detect_drift similarity scores match to a documented tolerance on a shared conformance fixture." A regression where the Python and TS feature-extractors drift apart — as happened (Python 0.2801 vs TS 0.1879) — would go undetected.
**Solution:** In the Python test, replicate `DivergenceDetector`'s baseline computation using `FeatureExtractor` + `compute_centroid` + `cosine_similarity` to derive the exact expected `similarity_score`, record that value into the fixture's `_expected_result`, and assert both the Python and TS `detect_drift` results match it within ±0.005.

## Approach & Changes
### Files to Modify
1. `tests/vectors/drift_cases/value_drift_sequence.json` — add `expected_alert_similarity_score` field to `_expected_result`
2. `tests/test_vectors.py` — add `test_detect_drift_similarity_score_parity` to `TestGoldenParitySDK`
3. `typescript/tests/golden-parity.test.ts` — add a new `it()` block under the `value_drift_sequence` describe for the ±0.005 parity assertion

### Implementation Steps
IMPORTANT: Execute every step in order, top to bottom.

### Step 1: Compute the fixture constant
Run the following Python snippet from the repo root to determine the exact expected alert similarity score, then substitute `<COMPUTED_VALUE>` in Step 2:

```python
import json
from aap.verification.features import FeatureExtractor, compute_centroid, cosine_similarity
from aap.verification.constants import DEFAULT_SUSTAINED_TURNS_THRESHOLD, DEFAULT_SIMILARITY_THRESHOLD

with open('tests/vectors/drift_cases/value_drift_sequence.json') as f:
    v = json.load(f)

traces = sorted(v['traces'], key=lambda t: t.get('timestamp', ''))
n = len(traces)
s = DEFAULT_SUSTAINED_TURNS_THRESHOLD
baseline_size = max(s, min(10, n // 4))

ex = FeatureExtractor()
centroid = compute_centroid([ex.extract_trace_features(t) for t in traces[:baseline_size]])

streak, score = [], None
for t in traces[baseline_size:]:
    sim = cosine_similarity(ex.extract_trace_features(t), centroid)
    if sim < DEFAULT_SIMILARITY_THRESHOLD:
        streak.append(sim)
        if len(streak) == s:
            score = round(sim, 4)
            break
    else:
        streak = []

print(score)  # record this value
```

### Step 2: Embed the constant in the fixture
In `tests/vectors/drift_cases/value_drift_sequence.json`, update `_expected_result` to add:

```json
"_expected_result": {
  "drift_detected": true,
  "drift_direction": "value_drift",
  "alert_after_trace_index": 8,
  "expected_alert_similarity_score": <COMPUTED_VALUE>
}
```

Replace `<COMPUTED_VALUE>` with the float printed by Step 1 (e.g. `0.2447`).

### Step 3: Add Python parity test
In `tests/test_vectors.py`, inside `TestGoldenParitySDK`, add a new test after `test_detect_drift_scores_are_bounded` (line ~316):

```python
def test_detect_drift_similarity_score_parity(self):
    """detect_drift alert similarity_score must match first-principles cosine (AC3).

    Replicates DivergenceDetector's baseline computation so any extractor
    regression is caught before it can cause threshold-straddling divergence
    between Python and TS.
    """
    from aap.verification.features import compute_centroid
    from aap.verification.constants import (
        DEFAULT_SIMILARITY_THRESHOLD,
        DEFAULT_SUSTAINED_TURNS_THRESHOLD,
    )

    vector = load_vector(VECTORS_DIR / "drift_cases" / "value_drift_sequence.json")
    traces = sorted(vector["traces"], key=lambda t: t.get("timestamp", ""))
    n = len(traces)
    s = DEFAULT_SUSTAINED_TURNS_THRESHOLD
    baseline_size = max(s, min(10, n // 4))

    extractor = FeatureExtractor()
    centroid = compute_centroid(
        [extractor.extract_trace_features(t) for t in traces[:baseline_size]]
    )

    streak, expected_score = [], None
    for trace in traces[baseline_size:]:
        sim = cosine_similarity(extractor.extract_trace_features(trace), centroid)
        if sim < DEFAULT_SIMILARITY_THRESHOLD:
            streak.append(sim)
            if len(streak) == s:
                expected_score = round(sim, 4)
                break
        else:
            streak = []

    assert expected_score is not None, "Fixture produced no alert-triggering trace"

    # detect_drift must produce the same score (exact — same extractor, same formula)
    alerts = detect_drift(vector["card"], vector["traces"])
    assert len(alerts) >= 1
    assert alerts[0].analysis.similarity_score == expected_score

    # Cross-language fixture constant must also match within ±0.005
    fixture_expected = vector["_expected_result"].get("expected_alert_similarity_score")
    assert fixture_expected is not None, (
        "expected_alert_similarity_score missing from fixture _expected_result"
    )
    assert abs(expected_score - fixture_expected) <= 0.005, (
        f"Python computed {expected_score} but fixture records {fixture_expected}; "
        "update fixture constant or fix extractor parity"
    )
```

### Step 4: Add TS parity test
In `typescript/tests/golden-parity.test.ts`, inside the `describe("golden fixture: value_drift_sequence ...")` block, add a new `it()` after line ~139 (after the `[0,1]` bounds test):

```typescript
it("alert similarity_score must match fixture expected value within ±0.005 (AC3)", () => {
  const expectedScore = (
    fixture._expected_result as { expected_alert_similarity_score: number }
  ).expected_alert_similarity_score;
  expect(expectedScore).toBeDefined();

  const alerts = detectDrift(fixture.card, fixture.traces);
  expect(alerts.length).toBeGreaterThan(0);

  const score = alerts[0].analysis.similarity_score;
  expect(Math.abs(score - expectedScore)).toBeLessThanOrEqual(0.005);
});
```

## Key Decisions & Rationale
**Lines of code to change:** ~45 (35 Python + 8 TS + 1 JSON field)
**Risk level:** low — only tests and a fixture constant are changed; no production code is touched
**Testing required:** Python golden-parity class + TS golden-parity suite

## Verification
Execute every command to validate the patch is complete with zero regressions.

```bash
# From repo root
cd /home/runner/work/aap/aap/trees/6db86dbb

# 1. Lint
python -m ruff check src tests

# 2. Type-check Python
python -m mypy src/aap --ignore-missing-imports

# 3. Python tests — golden parity class only first, then full suite
python -m pytest tests/test_vectors.py::TestGoldenParitySDK -v
python -m pytest tests/ -v

# 4. TS parity tests
cd typescript && npx vitest run tests/golden-parity.test.ts
```

Both `test_detect_drift_scores_are_bounded` (bounds only) and the new `test_detect_drift_similarity_score_parity` (AC3 numeric tolerance) must pass. The TS `similarity scores in DriftAnalysis should be in [0, 1]` test must still pass alongside the new `alert similarity_score must match fixture expected value within ±0.005` test.

## Known Limitations / Follow-ups
- The Python assertion uses an exact match (`==`) because both the test and `detect_drift` run through the same Python extractor. The TS assertion uses `±0.005` to accommodate floating-point rounding across language runtimes.
- If the feature extractor is updated in the future, Step 1 must be re-run to refresh `expected_alert_similarity_score` in the fixture.
