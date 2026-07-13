# Decisions Index Pointer File

**ADW ID:** 8c41614a
**Date:** 2026-07-13
**Plan-Spec:** /home/runner/work/aap/aap/agents/8c41614a/plan/issue-104-adw-8c41614a-add-decisions-index-md-pointer-file-plan.md

## Overview

Adds a `decisions/index.md` file to the `aap` repository that serves as a discovery pointer to cross-repo architectural decision records (ADRs) stored in the canonical `mnemom/scale` repository. The file does not duplicate ADR content — it identifies which ADRs govern this repo and links directly to their canonical sources.

## What Was Built

- `decisions/index.md`: A new pointer file that documents the repo's character, lists governing cross-repo ADRs (ADR-006, ADR-007, ADR-048) with direct links to their canonical locations in `mnemom/scale`, and describes the convention for future local ADRs.

## Technical Implementation

### Files Modified

- `decisions/index.md`: New file created (32 lines). Provides a discovery index for architectural decisions governing `aap`, with a table linking to three cross-repo ADRs and a section reserving space for future repo-local decisions.

### Key Changes

- Establishes `decisions/` as the conventional directory for architectural decision records in this repo.
- References ADR-006 (API Versioning Strategy), ADR-007 (Unified YAML Agent Card / AAP 2.0), and ADR-048 (Governance Signals Layering) as the governing cross-repo ADRs.
- Canonical source is `mnemom/scale` under `decisions/`; this file is a pointer only, not a mirror.
- Includes a maintainer note on ADR-048 flagging that its title should be spot-checked against the canonical file.
- Documents the convention for future repo-local ADRs (`decisions/ADR-NNN-<slug>.md`).

## How to Use

1. Navigate to `decisions/index.md` at the repo root to discover which ADRs govern `aap`.
2. Follow the links in the table to read the full ADR text in `mnemom/scale`.
3. To add a repo-local ADR, create `decisions/ADR-NNN-<slug>.md` and add a row to the table with `"local"` in the Canonical file column.

## Configuration

No configuration required. This is a documentation-only change with no runtime impact.

## Testing

No automated tests apply to this documentation file. Verify manually by confirming:
- `decisions/index.md` renders correctly on GitHub.
- All three ADR links resolve to valid files in `mnemom/scale`.
- The maintainer note on ADR-048 is addressed by a `mnemom/scale` contributor before the file is considered stable.

## Notes

- The ADR-048 title in the table is derived from the filename slug. A maintainer with access to `mnemom/scale` should confirm the canonical title matches before treating this file as stable.
- No repo-local ADRs exist at the time of writing.
- This change is documentation-only and carries no risk of runtime regression.
