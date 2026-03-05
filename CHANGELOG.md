# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.0] - 2026-03-04

### Changed
- `aap_version` default bumped from `"0.1.0"` to `"0.5.0"` across all schemas, fixtures, and examples

### Added
- YAML policy DSL support in mnemom-api (accepts `text/yaml` and `application/yaml` content types)
- Trust edges REST API (`GET`/`POST`/`DELETE /v1/agents/:id/trust-edges`)

### Fixed
- Test fixture version inconsistencies (`"1.0"` → `"0.5.0"`) across smoltbot observer/gateway

### Migration
- Existing cards should update `aap_version` field to `"0.5.0"` via `PUT /v1/agents/:id/card`

## [0.4.0] - 2026-02-22

### Changed
- Coordinated Mnemom 0.4.0 release. Unified version across all Mnemom SDK packages.

## [0.3.0] - 2026-02-21

### Removed
- **Reputation module extracted to standalone packages.** All reputation types, API methods, and gating have been moved to `@mnemom/types` and `@mnemom/reputation` (npm) / `mnemom-types` and `mnemom-reputation` (PyPI). This is a breaking change for code that imports reputation symbols from AAP.

### Migration Guide
Replace AAP reputation imports with the new packages:

**TypeScript:**
```typescript
// Before (0.2.x)
import { getReputation, createReputationGate } from '@mnemom/agent-alignment-protocol';
import type { ReputationScore } from '@mnemom/agent-alignment-protocol';

// After (0.3.0)
import { getReputation, createReputationGate } from '@mnemom/reputation';
import type { ReputationScore } from '@mnemom/types';
```

**Python:**
```python
# Before (0.2.x)
from aap import get_reputation, ReputationGate, ReputationScore

# After (0.3.0)
from mnemom_reputation import get_reputation, ReputationGate
from mnemom_types import ReputationScore
```

Install: `npm install @mnemom/types @mnemom/reputation` or `pip install mnemom-types mnemom-reputation`

## [0.2.0] - 2026-02-20

### Added
- `checkFleetCoherence()` (TypeScript) / `check_fleet_coherence()` (Python) — N-way fleet coherence analysis
- New types: `FleetCoherenceResult`, `PairwiseEntry`, `FleetOutlier`, `FleetCluster`, `ValueDivergence`, `AgentCoherenceSummary`
- Constants: `OUTLIER_STD_DEV_THRESHOLD`, `CLUSTER_COMPATIBILITY_THRESHOLD`
- Fleet score computation (mean of all pairwise scores)
- Outlier detection (>1σ below fleet mean)
- Cluster analysis (connected components at compatibility threshold)
- Divergence report (per-value agent alignment analysis)

## [0.1.8] - 2026-02-12

### Added
- `action_matches_list()` function in Python SDK — full parity with TypeScript `actionMatchesList()`
- Colon-prefix matching, compound name splitting, and word-boundary matching in Python SDK
- 15 new tests (10 unit + 5 integration) for Python action matching

## [0.1.7] - 2026-02-11

### Added
- `actionMatchesList()` function in TypeScript SDK for flexible action name matching
- Colon-prefix matching: `"exec: execute shell commands"` matches action name `"exec"`
- Compound name splitting: `"exec, read"` validates each component independently
- Word-boundary matching prevents false positives (e.g., `"execute"` no longer matches `"exec"`)

## [0.1.6] - 2026-02-08

### Changed
- Hardened publish workflow with version validation and CI gate
- Publish now verifies git tag matches pyproject.toml and package.json versions
- Publish now runs full test suite (Python + TypeScript) before releasing

## [0.1.5] - 2026-02-08

### Changed
- **ALGORITHM_VERSION bumped to 1.2.0** — trace-to-trace drift detection
- Drift detection now compares traces to a baseline centroid (first N traces) instead of to the card, eliminating false positives from asymmetric card/trace feature spaces
- Fixed TypeScript SDK category namespace collision (`category:` used for both principal.type and action.category)
- TypeScript SDK now uses `principal_type:` and `relationship:` prefixes matching Python SDK

## [0.1.2] - 2026-02-08

### Changed
- Improved npm package: added README and LICENSE to published package
- Removed broken eslint configuration

## [0.1.1] - 2026-02-07

### Changed
- **ALGORITHM_VERSION bumped to 1.1.0** — drift detection now uses structural features only
- Excluded content features (`content:*` tokens from reasoning text) from trace feature extraction for drift detection. Alignment Cards contain only structural declarations, so content tokens from reasoning diluted cosine similarity without adding alignment signal, causing false positive drift alerts on well-aligned traces. Content features remain available for text-to-text similarity via `compute_similarity()`.
- Fixed TypeScript SDK `detectDrift` to generate one alert per drift event (`==` threshold) instead of one per trace after threshold (`>=`), matching Python SDK behavior.

### Updated
- SPEC.md Section 8 — clarified that drift detection uses structural features only
- CALIBRATION.md Section 3.5 — documented rationale for excluding content features

## [0.1.0] - TBD

Initial release.

### Added
- Alignment Card schema and implementation
- AP-Trace audit log format
- Value Coherence Handshake protocol
- A2A integration extension
- MCP integration extension
- Example implementations
