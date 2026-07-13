# Decisions Index Pointer File

**ADW ID:** 26e7a627
**Date:** 2026-07-13
**Plan-Spec:** /home/runner/work/aap/aap/agents/26e7a627/plan/issue-101-adw-26e7a627-add-decisions-index-md-pointer-plan.md

## Overview

Adds a `decisions/index.md` pointer file to the `aap` repository that surfaces the architectural decision records (ADRs) from the central `mnemom/scale` repository that directly govern this codebase. The file serves as a navigational index — one row per relevant ADR — so contributors can discover governing decisions without leaving the repo.

## What Was Built

- A new `decisions/index.md` file containing a pointer table linking to three ADRs in `mnemom/scale`
- Per-ADR prose summaries explaining how each decision concretely affects this repository
- A reviewer callout noting that ADR-006 and ADR-007 filenames are derived from CHANGELOG prose and require internal verification before merge

## Technical Implementation

### Files Modified

- `decisions/index.md`: New file — ADR pointer index table (ADR-006, ADR-007, ADR-048) with contextual notes

### Key Changes

- Introduces `decisions/` directory at repo root as the conventional location for decision records
- ADR table links to canonical sources in the private `mnemom/scale` repository under `decisions/`
- **ADR-006** (SDK Versioning Support Policy): governs the 18-month major-version support window and `Deprecation`/`Sunset`/`Link` header cadence tied to the 1.0.0 stability commitment in `CHANGELOG.md`
- **ADR-007** (Unified Agent-Card Roadmap): records the planned unification of AAP alignment cards and CLPI policy YAML into a single YAML agent card in a future 2.0 release
- **ADR-048** (Governance Signals Layering): introduced the operator-facing sideband signal surface; its 2026-05-07 amendment retracted §7 and triggered removal of `examples/sovereign-agent-composer.ts` in release 1.2.0

## How to Use

1. Open `decisions/index.md` at the repo root to see which ADRs govern this codebase.
2. Follow the `Canonical source` link for any ADR to read the full decision text in `mnemom/scale` (requires internal access).
3. When adding a new feature, check the index to determine whether an existing ADR constrains the approach.
4. When a new ADR in `mnemom/scale` affects `aap`, add a row to the table and a prose note in the `## Notes` section.

## Configuration

No configuration required. The file is static documentation.

## Testing

No automated tests apply to this change. Verify manually:

- Confirm `decisions/index.md` renders correctly in GitHub (table, links, blockquote)
- A reviewer with access to `mnemom/scale` should verify that `ADR-006-sdk-versioning-support-policy.md` and `ADR-007-unified-agent-card-roadmap.md` are the actual filenames (ADR-048's filename is confirmed via `CHANGELOG.md` line 75)

## Notes

ADR-006 and ADR-007 filename slugs were inferred from CHANGELOG prose rather than directly verified against the private `mnemom/scale` repository. The file includes an explicit reviewer callout (blockquote) flagging this before merge. Once verified, the callout may be removed.
