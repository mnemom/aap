# Pass 2 Review: Documentation Corpus

**Reviewer**: Ember
**Date**: 2026-01-31
**Files Reviewed**: `SPEC.md`, `SECURITY.md`, `CALIBRATION.md`, `LIMITS.md`

---

## Summary

Documentation is comprehensive and well-written. Vigil's work on SECURITY.md and LIMITS.md is particularly strong — honest about limitations, thorough on threat models. However, I found **4 internal inconsistencies** between docs, **3 code-doc parity issues**, and **2 clarity concerns** for new adopters.

---

## 1. Internal Consistency

### 1.1 Sequence Number Requirement — CONTRADICTION

**SECURITY.md Section 5.1** (line 394):
> Traces MUST include `sequence_number` (monotonically increasing per agent)

**SPEC.md Section 5.3** (lines 450-461):
Does NOT list `sequence_number` as a REQUIRED field in AP-Trace structure.

**SDK (`models.py`)**: `VerificationResult` and trace handling don't include `sequence_number`.

**Impact**: SECURITY.md promises gap detection based on sequence numbers, but neither SPEC nor SDK implements them.

**Recommendation**: Either add `sequence_number` to SPEC.md as REQUIRED and implement in SDK, or remove the MUST from SECURITY.md and document gap detection as a SHOULD.

---

### 1.2 Signature Requirements — INCONSISTENT

**SECURITY.md Section 4.2** (line 277):
> Cards MUST be signed using Ed25519

**SPEC.md Section 4.2** (line 162):
> An Alignment Card MUST contain the following top-level fields...
> (No signature field listed as REQUIRED)

**SPEC.md Section 6.3.2** (line 765):
> The `signature` field is OPTIONAL but RECOMMENDED

**SDK**: Signature handling is not implemented — cards and traces are not signed.

**Impact**: SECURITY.md says MUST, SPEC.md says OPTIONAL. SDK implements neither.

**Recommendation**: Align on SHOULD for v0.1.0 with a note that v1.0 will require signatures. Update SECURITY.md to match.

---

### 1.3 Feature Extraction Methodology — GAP (Already Noted in Pass 1)

**CALIBRATION.md Section 3.2** (lines 127-154):
Describes 60/30/10 weighting:
- Word TF-IDF: 60%
- Character n-grams: 30%
- Metadata: 10%

**SDK (`features.py`)** implementation uses:
- Structural features (action type, category)
- Value features
- Content TF-IDF (word-level only, no char n-grams, no explicit weighting)

**Impact**: Users reading CALIBRATION.md expect one algorithm; SDK implements another. Both may be valid, but the discrepancy is confusing.

**Recommendation**: Add a note to CALIBRATION.md:

> *Note: CALIBRATION.md describes the reference methodology used for threshold derivation. The SDK implementation uses a simplified feature set optimized for AP-Trace/Card comparison. See `features.py` for SDK-specific implementation.*

---

### 1.4 Condition Expression Language — INCOMPLETE IMPLEMENTATION

**SPEC.md Section 4.6** (lines 298-318) documents:
- `contains(field, value)` function
- `matches` operator
- Nested field paths (`field_ref := identifier ("." identifier)*`)

**SDK (`api.py:369-439`)** implements:
- Basic comparisons (`>`, `<`, `>=`, `<=`, `==`, `!=`)
- `action_type == "value"` pattern
- Boolean field checks

**Not implemented**:
- `contains()` — documented but missing
- `matches` — documented but missing
- Nested field paths — partially supported

**Impact**: Users writing escalation triggers per SPEC will find some conditions don't work.

**Recommendation**: Either implement missing functions or add to SPEC.md Section 4.6:

> *Note: The minimal implementation MUST support comparisons and equality. Advanced functions (`contains`, `matches`) are OPTIONAL in v0.1.0.*

---

## 2. Code-Doc Parity

### 2.1 Drift Detection Alert Structure — MISMATCH

**SPEC.md Section 8.4** (line 1016) shows `drift_direction` as string:
```json
"drift_direction": "toward_autonomy_expansion"
```

**SDK (`models.py:129-145`)** uses enum:
```python
class DriftDirection(str, Enum):
    AUTONOMY_EXPANSION = "autonomy_expansion"  # Not "toward_autonomy_expansion"
```

**Impact**: Minor — SPEC shows a slightly different string format than SDK produces.

**Recommendation**: Update SPEC.md example to use exact enum value `"autonomy_expansion"`.

---

### 2.2 Verification Metadata — ADDITIONAL FIELD

**SDK (`models.py:101-103`)** includes:
```python
duration_ms: float | None = Field(None, description="Time taken...")
```

**SPEC.md Section 7.4** (lines 956-959) doesn't mention `duration_ms`.

**Impact**: SDK provides more info than SPEC documents. Not a bug, but creates inconsistency.

**Recommendation**: Add `duration_ms` to SPEC.md verification_metadata example as OPTIONAL.

---

### 2.3 Coherence Result — MISSING FIELDS

**SPEC.md Section 6.3.4** coherence_result example doesn't show:
- `proposed_resolution` (shown in conflict example but not in schema table)
- `conditions` field

**SDK (`models.py:204-226`)** includes both as standard fields.

**Impact**: New implementers might miss these fields.

**Recommendation**: Add schema table for coherence_result to SPEC.md Section 6.3.4.

---

## 3. Clarity for New Adopters

### 3.1 Entry Point Confusion

As the QUICKSTART author, I know users typically:
1. Read QUICKSTART (setup)
2. Read SPEC (protocol)
3. Get confused about "where's the API docs?"

**Issue**: No clear documentation of the SDK's public API surface. SPEC.md describes the *protocol*, not the *Python SDK*.

**Recommendation**: Add `docs/API.md` with:
- `verify_trace(trace, card)` — what it takes, what it returns
- `check_coherence(my_card, their_card, task_values)` — when to use `task_values`
- `detect_drift(card, traces, ...)` — threshold parameters explained

Or link to auto-generated API docs.

---

### 3.2 Threshold Adjustment Guidance — BURIED

**CALIBRATION.md Section 7** has excellent recalibration guidance, but it's buried 60% into the document.

**Issue**: Users who need to adjust thresholds for their use case won't know to look in CALIBRATION.md. They'll look in SPEC.md or a "Configuration" doc.

**Recommendation**: Add to SPEC.md Section 8.3 after the threshold table:

> *These defaults suit the calibration corpus (transformer-based deliberative agents). For recalibration guidance, see CALIBRATION.md Section 7.*

---

## 4. Strengths Worth Noting

### 4.1 LIMITS.md — Exemplary

Section 1: "The Five Limitations" is exactly right. Non-negotiable, clearly framed, with concrete examples. The "Compliant Adversary" example (1.1) and "Verified Harm" example (1.2) should be promoted — they're the best articulation of AAP's honest claims I've seen.

### 4.2 SECURITY.md — Comprehensive Threat Model

Section 1 threat model is thorough. The DREAD prioritization (1.4) and Red Team Scenarios (12.3) are valuable. The "Perfect Liar" scenario is honest about what AAP can't catch.

### 4.3 Cross-Reference Discipline

Documents reference each other well:
- SPEC.md Section 8.3 → CALIBRATION.md for methodology
- SECURITY.md Section 10 → LIMITS.md for fundamental limitations
- CALIBRATION.md Section 5 → constants.py for actual values

---

## 5. Recommendations Summary

| Priority | Issue | Docs Affected | Fix |
|----------|-------|---------------|-----|
| **HIGH** | Sequence number contradiction | SPEC.md, SECURITY.md | Align MUST/SHOULD or implement |
| **HIGH** | Signature requirement inconsistency | SPEC.md, SECURITY.md | Align on SHOULD for v0.1.0 |
| **MEDIUM** | Feature extraction gap | CALIBRATION.md | Add note explaining SDK simplification |
| **MEDIUM** | Condition language incomplete | SPEC.md, api.py | Mark advanced functions OPTIONAL |
| **LOW** | drift_direction string mismatch | SPEC.md | Update example |
| **LOW** | Missing API docs | (new file) | Create docs/API.md |
| **LOW** | Threshold guidance buried | SPEC.md | Add cross-reference |

---

## 6. Cross-Review Note

Ariadne asked which parts I implemented for cross-review. I wrote:
- QUICKSTART.md
- Test suite (`tests/`)

I did NOT write the verification engine or these docs being reviewed. Fresh perspective here.

---

**Review Status**: Pass 2 Complete
**Blocking Issues**: HIGH items should be resolved before public release to avoid confusing implementers
**Confidence**: 0.9 — thorough cross-reference check

---

*Ember | 2026-01-31*
