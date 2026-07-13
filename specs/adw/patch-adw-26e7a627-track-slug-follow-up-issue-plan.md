# Spec — Patch: File tracking issue and reference it for ADR-006/ADR-007 slug confirmation

- **Status:** Draft
- **Branch:** chore-issue-101-adw-26e7a627-aap-add-decisions-index-md-pointer-file
- **Location:** decisions/index.md
- **Related docs:** specs/adw/patch-adw-26e7a627-fix-unverified-adr-links-plan.md

## Problem / Objective
**Original Spec:** N/A
**Issue:** The review gate blocks on MNE-441/MNE-443: `decisions/index.md` lists ADR-006 and ADR-007 with directory-root links labelled "(slug unconfirmed)", but no filed GitHub Issue or Linear ticket tracks the slug confirmation. The acceptance criterion "correct canonical-home links" is therefore open-ended with no resolution path.
**Solution:** File a GitHub Issue in `mnemom/aap` explicitly scoped to confirming the exact filenames for ADR-006 and ADR-007 in the private `mnemom/scale` repository, then update `decisions/index.md` to reference the issue number in each affected row, converting the implicit deferral into a tracked item with a concrete resolution path.

## Approach & Changes
### Files to Modify
- `decisions/index.md` — update ADR-006 and ADR-007 `Canonical source` cells to embed the issue reference

### Implementation Steps
IMPORTANT: Execute every step in order, top to bottom.

### Step 1: File the tracking GitHub Issue
Run the following command and capture the returned issue URL (from which the issue number is extracted):

```bash
gh issue create \
  --repo mnemom/aap \
  --title "Confirm exact filenames (slugs) for ADR-006 and ADR-007 in mnemom/scale" \
  --body "## Context
decisions/index.md currently links ADR-006 and ADR-007 to the \`mnemom/scale\` decisions/ directory root because the exact filenames could not be independently verified (the repo is private).

## Action required
A team member with read access to mnemom/scale should:
1. Open https://github.com/mnemom/scale/tree/main/decisions
2. Locate the files for ADR-006 (SDK Versioning Support Policy) and ADR-007 (Unified Agent-Card Roadmap).
3. Update the two provisional rows in decisions/index.md with per-file blob links, e.g.:
   - \`https://github.com/mnemom/scale/blob/main/decisions/ADR-006-sdk-versioning-support-policy.md\`
   - \`https://github.com/mnemom/scale/blob/main/decisions/ADR-007-unified-agent-card-roadmap.md\`
4. Open a follow-up PR updating those two rows and close this issue.

## Acceptance criteria
- Both ADR-006 and ADR-007 rows in decisions/index.md point to per-file blob URLs that resolve without 404.
- The '(slug unconfirmed)' annotation is removed from both rows."
```

- Note the returned issue number (e.g. `#NNN`) from the output URL.

### Step 2: Update decisions/index.md to reference the filed issue
Replace the two provisional table rows so each embeds the issue reference. Use the actual issue number captured in Step 1 (substitute `NNN` accordingly):

- **ADR-006 row** — change the `Canonical source` cell to:
  `[decisions/ (slug unconfirmed, tracked in #NNN)](https://github.com/mnemom/scale/tree/main/decisions)`
- **ADR-007 row** — change the `Canonical source` cell to:
  `[decisions/ (slug unconfirmed, tracked in #NNN)](https://github.com/mnemom/scale/tree/main/decisions)`
- Leave the ADR-048 row entirely unchanged.

## Key Decisions & Rationale
**Lines of code to change:** 2 table rows in decisions/index.md
**Risk level:** low — documentation only, no logic changes
**Testing required:** Verify both rows contain the issue reference; verify ADR-048 row is untouched; verify the filed issue is open and reachable.

## Verification
Execute every command to validate the patch is complete with zero regressions.

- `gh issue view NNN --repo mnemom/aap` — confirm the tracking issue is open and its title matches "Confirm exact filenames (slugs) for ADR-006 and ADR-007 in mnemom/scale"
- `grep -n "tracked in #" decisions/index.md` — must return exactly 2 lines (one for ADR-006, one for ADR-007)
- `grep -n "ADR-006\|ADR-007\|ADR-048" decisions/index.md` — must show all three ADRs present in the table
- `grep -n "mnemom/scale/blob/main/decisions/ADR-048" decisions/index.md` — must show 1 hit (ADR-048 per-file link still correct)

## Known Limitations / Follow-ups
- Option (a) — confirming the actual filenames directly — is preferred once a team member with `mnemom/scale` read access is available. The filed issue (Step 1) is the resolution path for that work.
- The PR body for this branch should be updated to reference the newly filed issue number so reviewers can verify the tracked state.
