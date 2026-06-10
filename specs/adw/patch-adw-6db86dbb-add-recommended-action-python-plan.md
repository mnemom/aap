# Spec — Patch: Add `recommended_action` to Python VerificationResult

- **Status:** Draft
- **Branch:** bug-issue-72-adw-6db86dbb-fix-sdk-python-ts-parity
- **Location:** `src/aap/verification/models.py`, `src/aap/verification/api.py`, `tests/test_vectors.py`
- **Related docs:** N/A

## Problem / Objective
**Original Spec:** N/A
**Issue:** TypeScript's `VerificationResult` (typescript/src/verification/models.ts line 95, api.ts lines 291–295) includes a `recommended_action: 'proceed' | 'review' | 'deny'` field derived from violations/warnings. Python's `VerificationResult` (src/aap/verification/models.py lines 109–132) has no such field. The acceptance criterion AC1 requires "identical normalized verify_trace result schema across SDKs (same fields, same checks)". A consumer diffing the two payloads will still see a field-level mismatch.
**Solution:** Add a `Literal["proceed", "review", "deny"]` type alias and `recommended_action` field to Python's `VerificationResult`, then populate it in `verify_trace` using the identical logic as the TS implementation: `"deny"` when violations exist, `"review"` when no violations but warnings exist, `"proceed"` otherwise. Add a parity test to `tests/test_vectors.py`.

## Approach & Changes
### Files to Modify
- `src/aap/verification/models.py` — add `VerificationRecommendation` type alias + `recommended_action` field
- `src/aap/verification/api.py` — populate `recommended_action` in `verify_trace` return
- `tests/test_vectors.py` — add test asserting `recommended_action` is present and correct

### Implementation Steps
IMPORTANT: Execute every step in order, top to bottom.

### Step 1: Add `VerificationRecommendation` type alias and `recommended_action` field to `models.py`

In `src/aap/verification/models.py`:

- Add `Literal` to the `typing` import (line 12): change `from typing import Any` → `from typing import Any, Literal`
- After the `VerificationMetadata` class (after line 107), add a type alias:
  ```python
  VerificationRecommendation = Literal["proceed", "review", "deny"]
  ```
- In `VerificationResult` (lines 109–132), insert `recommended_action` as the **second field** (immediately after `verified: bool`), matching TS field order:
  ```python
  recommended_action: VerificationRecommendation = Field(
      ...,
      description=(
          "Explicit action recommendation derived from violations and warnings. "
          "Prefer this over branching on `verified` alone — it distinguishes "
          "warning-only results ('review') from clean results ('proceed')."
      ),
  )
  ```

### Step 2: Populate `recommended_action` in `verify_trace` in `api.py`

In `src/aap/verification/api.py`:

- Add `VerificationRecommendation` to the models import (the existing block around lines 30–48):
  ```python
  from aap.verification.models import (
      ...
      VerificationRecommendation,
      ...
  )
  ```
- In the `verify_trace` return statement (lines 284–297), add the `recommended_action` field using the same ternary logic as TypeScript (api.ts lines 291–295):
  ```python
  return VerificationResult(
      verified=len(violations) == 0,
      recommended_action=(
          "deny" if violations
          else "review" if warnings
          else "proceed"
      ),
      trace_id=trace_id,
      ...
  )
  ```

### Step 3: Add parity test in `tests/test_vectors.py`

In the `TestGoldenParitySDK` class (around line 220), add a new test method after the existing `test_verify_trace_low_behavioral_similarity_warning` test:

```python
def test_verify_trace_recommended_action_present_and_correct(self):
    """verify_trace must return recommended_action matching violations/warnings state."""
    vector = load_vector(VECTORS_DIR / "valid_traces" / "compliant_recommendation.json")
    result = verify_trace(vector["trace"], vector["card"])

    assert hasattr(result, "recommended_action")
    assert result.recommended_action in ("proceed", "review", "deny")
    if result.violations:
        assert result.recommended_action == "deny"
    elif result.warnings:
        assert result.recommended_action == "review"
    else:
        assert result.recommended_action == "proceed"
```

## Key Decisions & Rationale
**Lines of code to change:** ~15 lines added across 3 files
**Risk level:** low
**Testing required:** Run existing Python test suite + new parity test to confirm no regressions and correct field population.

Using `Literal["proceed", "review", "deny"]` (not `str`) mirrors the TypeScript `VerificationRecommendation` union type and provides static type-checker validation. The ternary order (`deny` → `review` → `proceed`) is identical to the TS implementation to avoid divergence.

## Verification
Execute every command to validate the patch is complete with zero regressions.

- **lint:** `ruff check src/aap/verification/models.py src/aap/verification/api.py tests/test_vectors.py`
- **typecheck:** `mypy src/aap/verification/models.py src/aap/verification/api.py`
- **test:** `pytest tests/test_vectors.py -v`

## Known Limitations / Follow-ups
The `VerificationRecommendation` type alias is not exported from `src/aap/verification/__init__.py` yet — that can be done as a follow-up if consumers need to import it directly.
