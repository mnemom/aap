# Decisions

This file is a discovery pointer for architectural decisions that govern **aap**
(Agent Alignment Protocol). The canonical source for all cross-repo ADRs is the
private [`mnemom/scale`](https://github.com/mnemom/scale) repository under
`decisions/`. This file does not duplicate them — it lists which ones apply here
and links directly to the canonical file.

## Repo character

AAP is a dual-language (Python + TypeScript) transparency protocol for autonomous
agents. It ships an Alignment Card schema, an AP-Trace audit log, and a
verification engine. Decisions affecting the card shape, versioning contract, and
governance signal layering live in `mnemom/scale` and are referenced below.

## Cross-repo ADRs that govern this repo

| ADR | Title | Canonical file |
|-----|-------|----------------|
| ADR-006 | ADR-006: mnemom-api API Versioning Strategy | [ADR-006-api-versioning.md](https://github.com/mnemom/scale/blob/main/decisions/ADR-006-api-versioning.md) |
| ADR-007 | ADR-007: Unified YAML Agent Card (AAP 2.0) | [ADR-007-unified-agent-card-2.0.md](https://github.com/mnemom/scale/blob/main/decisions/ADR-007-unified-agent-card-2.0.md) |
| ADR-048 | ADR-048: Governance Signals Layering | [ADR-048-governance-signals-layering.md](https://github.com/mnemom/scale/blob/main/decisions/ADR-048-governance-signals-layering.md) |

> **Note (ADR-048):** The title above is derived from the filename slug. A maintainer
> with access to `mnemom/scale` should spot-check that the canonical title matches
> before this file is considered stable.

## Local decisions

No repo-local ADRs at this time. If a decision is scoped exclusively to `aap`,
add it here as `decisions/ADR-NNN-<slug>.md` and include a row in the table above
with "local" in the Canonical file column.
