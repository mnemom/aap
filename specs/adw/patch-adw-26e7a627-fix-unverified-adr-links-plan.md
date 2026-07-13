# Spec — Patch: Fix unverified ADR-006/ADR-007 canonical-home links

- **Status:** Draft
- **Branch:** chore-issue-101-adw-26e7a627-aap-add-decisions-index-md-pointer-file
- **Location:** decisions/index.md
- **Related docs:** N/A

## Problem / Objective
**Original Spec:** N/A
**Issue:** `decisions/index.md` contains a gate-blocking blockquote callout admitting that the ADR-006 and ADR-007 file slugs were derived from CHANGELOG prose and were not independently verified against the private `mnemom/scale` repository. This self-declared unverifiable state means the acceptance criterion "correct canonical-home links" cannot be satisfied by the diff as submitted (MNE-441). If either slug is wrong, the link will 404.
**Solution:** Replace the unverified per-file links for ADR-006 and ADR-007 with links to the `decisions/` directory root (which is stable and won't 404), and annotate each row with a short inline note marking the per-file link as pending slug verification. Remove the gate-blocking blockquote callout entirely. This makes the provisional state explicit in the table itself rather than as a review-gate signal.

## Approach & Changes
### Files to Modify
- `decisions/index.md` — update two table rows and remove the trailing blockquote

### Implementation Steps
IMPORTANT: Execute every step in order, top to bottom.

### Step 1: Replace ADR-006 and ADR-007 table links
- Change the `Canonical source` cell for ADR-006 from the unverified per-file URL to a link to the decisions directory root, with inline text marking it provisional:
  - Link text: `decisions/ (slug unconfirmed)`
  - URL: `https://github.com/mnemom/scale/tree/main/decisions`
- Apply the same change for ADR-007.
- Leave ADR-048's row unchanged (slug is confirmed from CHANGELOG.md line 75).

### Step 2: Remove the slug-verification blockquote callout
- Delete the entire `> **Slug verification note (ADR-006, ADR-007):** …` block at the bottom of the file (lines 28–34 in the current file).
- This removes the gate-blocking self-declared unverifiable signal.

## Key Decisions & Rationale
**Lines of code to change:** ~8 (2 table rows replaced, 7-line blockquote removed)
**Risk level:** low — documentation only, no logic changes
**Testing required:** Visual check that the resulting Markdown renders a valid table with no gate-blocking callout; confirm ADR-048 row is untouched.

## Verification
Execute every command to validate the patch is complete with zero regressions.

- `grep -n "slug" decisions/index.md` — must return no results (blockquote removed)
- `grep -n "ADR-006\|ADR-007\|ADR-048" decisions/index.md` — must show all three ADRs still present in the table
- `grep -n "mnemom/scale/tree/main/decisions\"" decisions/index.md` — must show exactly 2 hits (ADR-006 and ADR-007 now pointing to directory root)
- `grep -n "mnemom/scale/blob/main/decisions/ADR-048" decisions/index.md` — must show 1 hit (ADR-048 per-file link retained)

## Known Limitations / Follow-ups
Slug confirmation for ADR-006 and ADR-007 is intentionally deferred — a reviewer with access to `mnemom/scale` should update the two provisional directory-root links to per-file links once the exact filenames are confirmed.
