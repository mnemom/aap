# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.1] - 2026-06-10

### Fixed

* **verify (Python + TypeScript):** `extract_card_features` / `extractCardFeatures` now emit the **union** of both SDKs' prior feature sets, making card vectors identical across languages.
  - Python gains: `conflict:{id}`, `forbidden:{action}`, `escalation:{action}`, `condition:{token}` (weight 0.5)
  - TypeScript gains: `audit:queryable`, `audit:tamper_{mode}`
  - On any fixture, Python and TS now produce the same `similarity_score` (within ≤1e-9 float tolerance).

* **verify:** `similarity_score` divergence eliminated. Before this fix, on the `compliant_recommendation` fixture Python returned `0.4501` while TypeScript returned `0.3642` (Δ0.086). Near the `BEHAVIORAL_SIMILARITY_THRESHOLD` of `0.5` this divergence could flip `recommended_action` between `"review"` and `"proceed"` for the same trace depending on which SDK was used. Both SDKs now return `0.3642` for that fixture.

* **verify (Python):** `verification_metadata.similarity_details` shape aligned with TypeScript. The Python payload previously emitted `{similarities, trace_ids, mean_similarity, min_similarity, trend}`; it now emits `{similarity_score, method, algorithm_version}` — the same shape TypeScript has always produced. See **Migration** below if your code reads this field.

* **tests:** Replaced the self-referential cross-language parity gate in `golden-parity.test.ts`. The prior test computed its expected value with TS extractors and compared TS to itself, making it structurally incapable of detecting Python ↔ TypeScript divergence. Both SDKs now assert against a language-independent `expected_similarity_score` stored in each fixture file. Any future extractor drift between SDKs is CI-visible. ([#75](https://github.com/mnemom/aap/issues/75), Linear MNE-370)

### ⚠ Similarity scores are NOT comparable across this boundary

`ALGORITHM_VERSION` remains `"1.2.0"` in this patch because drift detection (which uses `ALGORITHM_VERSION` to guard stale baselines) is unaffected. However, `verify_trace` **similarity scores computed before 2.0.1 are not numerically comparable to scores computed after**: the Python extractor now emits more features, changing cosine denominators. If you store raw `similarity_score` values and compare them over time, treat the 2.0.1 upgrade as a score reset point.

### Migration

**`similarity_details` shape change (Python SDK only):**

```python
# Before 2.0.1 — Python similarity_details shape:
details = result.verification_metadata.similarity_details
mean = details["mean_similarity"]   # KeyError after upgrade
sims = details["similarities"]      # KeyError after upgrade

# After 2.0.1 — aligned shape (same as TypeScript):
details = result.verification_metadata.similarity_details
score  = details["similarity_score"]   # float
method = details["method"]             # "cosine"
ver    = details["algorithm_version"]  # e.g. "1.2.0"
```

TypeScript consumers: `similarity_details` shape is unchanged.

---

## [2.0.0](https://github.com/mnemom/aap/compare/v1.3.0...v2.0.0) (2026-06-05)


### ⚠ BREAKING CHANGES

* the SDK card shape and the TS card types changed (AutonomyEnvelope->Autonomy, AuditCommitment->Audit, AuditStorage/StorageType removed, AlignmentMode added, EU_COMPLIANCE_AUDIT_COMMITMENT->EU_COMPLIANCE_AUDIT). Published as agent-alignment-protocol (PyPI) and @mnemom/agent-alignment-protocol (npm); needs a human release decision (versions set to 2.0.0, not published).

### Added

* migrate alignment-card to unified / ADR-039 shape (MNE-190) ([#69](https://github.com/mnemom/aap/issues/69)) ([64576e2](https://github.com/mnemom/aap/commit/64576e215d8d494e160eea5df02fe63b671a286d))

## [1.3.0](https://github.com/mnemom/aap/compare/v1.2.0...v1.3.0) (2026-06-02)


### Added

* **ap-trace:** add Decision.value_scores for V2 observer surface ([#61](https://github.com/mnemom/aap/issues/61)) ([8845de2](https://github.com/mnemom/aap/commit/8845de28360d06cfed0fe274a77142ab792b1161))


### Fixed

* **verify:** normalize parameterized declared values — kill false undeclared_value denies (ADR-065 [#9](https://github.com/mnemom/aap/issues/9)) ([#62](https://github.com/mnemom/aap/issues/62)) ([9c25b4b](https://github.com/mnemom/aap/commit/9c25b4b746088efd90cc75f611d7768177998255))

## [1.2.0] - 2026-05-07

### Removed — `examples/sovereign-agent-composer.ts`

Per [ADR-048](https://github.com/mnemom/scale/blob/main/decisions/ADR-048-governance-signals-layering.md)'s 2026-05-07 amendment retracting §7, the
"application-owned sovereign-agent composition" pattern is no longer
part of the Mnemom platform's architectural surface. Mnemom serves
fleet-shaped governance signals to operators only — humans, dashboards,
webhooks, paging — and offers no platform-supplied path or example for
folding them into agent prompts.

The example file `examples/sovereign-agent-composer.ts` shipped in
1.1.0 is deleted in this release. Applications that want fleet context
inside an agent's prompt derive it from application-internal data and
render it application-side; the platform offers no surface or worked
example for that.

### Unchanged

The TypeScript governance signal types in `src/governance.ts` are
unaffected. They describe the operator surface and are consumed by
operator-shaped clients: dashboards, webhook subscribers, alerting
tools, custom operator panels, audit pipelines. Type guards
(`isFleetSignal`, `isCoherenceSignal`, `isFaultLineSignal`,
`isDriftSignal`), severity helpers (`severityAtLeast`,
`SEVERITY_ORDER`), and all enums remain.

### Migration

Consumers who imported types from `examples/sovereign-agent-composer.ts`
should not exist — the file was example code, not an exported module.
If any application coupled to the example by copying its shape, derive
the typed contract from `@mnemom/agent-alignment-protocol`'s
`GovernanceSignal` (and friends) instead of continuing to track the
deleted example.

## [1.1.0] - 2026-05-07

### Added — Governance signal types (ADR-048)

Operator-actionable observations produced by Mnemom platform detectors
(`sideband.coherence`, `sideband.fault_line`, `sideband.fleet`,
`sideband.drift`, future `protection.*` / `posture.*`). Surfaced via
REST `/v1/{orgs,teams,agents}/.../governance/signals` and webhook events
`governance.signal.{fired,acknowledged,resolved,dismissed}`.

- New `src/governance.ts` types: `GovernanceSignal`,
  `GovernanceSignalScope`, `GovernanceSignalSource`,
  `GovernanceSignalSeverity`, `GovernanceSignalStatus`,
  `GovernanceActorRole`, `GovernanceResolutionStatus`,
  `GovernanceNotificationChannel`, source-specific `*PatternType` +
  `*SourceRef` discriminated unions, `GovernanceWebhookEnvelope`,
  per-channel `GovernanceNotificationState`.
- Type guards: `isFleetSignal`, `isCoherenceSignal`,
  `isFaultLineSignal`, `isDriftSignal`.
- Severity helpers: `severityAtLeast`, `SEVERITY_ORDER`.

### Notes

Governance signals are operator-facing observations. The platform
serves them to operators only (UI, webhook, REST). 1.1.0 originally
shipped an `examples/sovereign-agent-composer.ts` worked pattern for
application-side prompt composition; that pattern was retracted in
1.2.0 — see the 1.2.0 entry above.

This is a non-breaking minor release: existing `verifyTrace`,
`checkCoherence`, `detectDrift`, `analyzeFaultLines`,
`checkFleetCoherence`, `checkFleetFaultLines` APIs are unchanged.

## [1.0.0] - 2026-04-13

### 🎯 1.0.0 Stability Commitment

This release locks the public API of `@mnemom/agent-alignment-protocol` for stability.

**What this means:**
- Breaking changes now require a major version bump to 2.0 (not a minor bump within 0.x)
- Each major version is supported for **18 months** from the release of its successor (per ADR-006)
- Deprecations are announced with `Deprecation`, `Sunset`, and `Link` response headers + email notifications at T+0, +12 months, +16 months, +17 months
- The API surface frozen in 1.0.0 is considered the canonical contract for all downstream integrations

**Forward-looking note (ADR-007):** A 2.0 is planned that unifies AAP alignment cards and CLPI policy YAML into a single YAML agent card with runtime composition. Target: 6–12 months post-1.0 when production data informs the design. 1.x will receive bug fixes and strictness improvements; new *card format* features are reserved for 2.0.

### Removed (breaking)
- `DEFAULT_SUSTAINED_TURNS_THRESHOLD` — the deprecated alias introduced in 0.7.0 is removed. Use `DEFAULT_SUSTAINED_CHECKS_THRESHOLD`.

### Unchanged from 0.7.0
- `VerificationResult.recommended_action` field
- `VerificationRecommendation` type
- `DEFAULT_SUSTAINED_CHECKS_THRESHOLD` constant name

## [0.7.0] - 2026-04-13

### Added
- `VerificationRecommendation` type: `"proceed" | "review" | "deny"` (exported from main index)
- `recommended_action` field on `VerificationResult` — derived from violations and warnings:
  - `"proceed"` — no violations, no warnings
  - `"review"` — no violations, warnings present
  - `"deny"` — violations found
  
  This mirrors the `recommended_action` field on AIP's `IntegritySignal` for a consistent cross-protocol pattern. Prefer branching on `recommended_action` over `verified` alone.

- `DEFAULT_SUSTAINED_CHECKS_THRESHOLD = 3` — canonical constant name aligned with AIP terminology

### Deprecated
- `DEFAULT_SUSTAINED_TURNS_THRESHOLD` — renamed to `DEFAULT_SUSTAINED_CHECKS_THRESHOLD`. The deprecated alias remains in 0.7.0 but **will be removed at 1.0.0**. Update any imports now.

### Migration

**`recommended_action` (new field):**
```typescript
// Before — required manual logic:
const result = await verifyTrace(trace, card);
if (!result.verified) { block(); }
else if (result.warnings.length > 0) { warn(); }
else { proceed(); }

// After — use the new field:
const result = await verifyTrace(trace, card);
switch (result.recommended_action) {
  case "proceed": proceed(); break;
  case "review":  warn(); break;
  case "deny":    block(); break;
}
```

**`DEFAULT_SUSTAINED_CHECKS_THRESHOLD` (renamed constant):**
```typescript
// Before:
import { DEFAULT_SUSTAINED_TURNS_THRESHOLD } from '@mnemom/agent-alignment-protocol';

// After:
import { DEFAULT_SUSTAINED_CHECKS_THRESHOLD } from '@mnemom/agent-alignment-protocol';
```

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
