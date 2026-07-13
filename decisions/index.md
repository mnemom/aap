# Architectural Decision Records

Design decisions that govern this repository live in
[mnemom/scale](https://github.com/mnemom/scale/tree/main/decisions).
This file is a pointer index — one row per ADR that directly shapes `aap`.

| ADR | Title | Status | Canonical source |
|-----|-------|--------|-----------------|
| ADR-006 | SDK Versioning Support Policy | Accepted | [ADR-006-sdk-versioning-support-policy.md](https://github.com/mnemom/scale/blob/main/decisions/ADR-006-sdk-versioning-support-policy.md) |
| ADR-007 | Unified Agent-Card Roadmap | Accepted | [ADR-007-unified-agent-card-roadmap.md](https://github.com/mnemom/scale/blob/main/decisions/ADR-007-unified-agent-card-roadmap.md) |
| ADR-048 | Governance Signals Layering | Accepted | [ADR-048-governance-signals-layering.md](https://github.com/mnemom/scale/blob/main/decisions/ADR-048-governance-signals-layering.md) |

## Notes

**ADR-006** governs the 18-month major-version support window and the
`Deprecation` / `Sunset` / `Link` header cadence declared in `CHANGELOG.md`
at the 1.0.0 stability commitment.

**ADR-007** records the roadmap decision to unify AAP alignment cards and CLPI
policy YAML into a single YAML agent card in a future 2.0 release.

**ADR-048** introduced the operator-facing governance signal surface
(`sideband.coherence`, `sideband.fault_line`, `sideband.fleet`,
`sideband.drift`) and its 2026-05-07 amendment retracted §7 (application-owned
sovereign-agent composition), which triggered the removal of
`examples/sovereign-agent-composer.ts` in the 1.2.0 release.

> **Slug verification note (ADR-006, ADR-007):** The filenames for ADR-006 and
> ADR-007 are derived from CHANGELOG prose and have not been independently
> verified against the `mnemom/scale` repository (which is private). A reviewer
> with internal access should confirm that
> `ADR-006-sdk-versioning-support-policy.md` and
> `ADR-007-unified-agent-card-roadmap.md` are the actual filenames before
> merging. ADR-048's filename is confirmed from the link at CHANGELOG.md line 75.
