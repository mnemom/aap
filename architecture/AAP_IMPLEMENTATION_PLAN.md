# AAP V1 Implementation Plan

**Status**: APPROVED
**Date**: 2026-01-31
**Thread**: th-d465065a (Elenchus — Unanimous Consensus)
**Checkpoint**: cp-f5be7ce8
**Authors**: Ember (coordinator), Ariadne (architecture), Vigil (protocol)
**Approved by**: Alex Garden

---

## Executive Summary

This document defines the complete implementation plan for Agent Alignment Protocol (AAP) V1 release. AAP is the viral primitive — the foundation that creates pull-through for Clark, Foundry, Argo, and domain verticals.

**Strategic Frame**: Ship minimum viable protocol for viral adoption. Free tier = verification. Paid tier = insight.

**Timeline**: 5 checkpoints over 5 days (+120 hours from plan approval)

**Division of Labor**:
- **Vigil**: Protocol/Docs Track
- **Ariadne**: Architecture/Code Track
- **Ember**: GTM/Examples Track

---

## Progress Tracking

| Deliverable | Owner | Status | Completed | Notes |
|-------------|-------|--------|-----------|-------|
| **SPEC.md v0.1** | Vigil | COMPLETE | 2026-01-31 | Full IETF-style spec, 1478 lines, includes all 3 components + verification + drift detection |
| **LIMITS.md** | Vigil | COMPLETE | 2026-01-31 | 634 lines, 5 non-negotiables with examples, anti-patterns, appropriate/inappropriate use cases, defense in depth |
| **Braid Extraction** | Ariadne | COMPLETE | 2026-01-31 | 4 modules extracted: features.py (262 lines), api.py (533 lines), models.py (254 lines), constants.py (48 lines) |
| **Pydantic Schemas** | Ariadne | COMPLETE | 2026-01-31 | alignment_card.py (306 lines), ap_trace.py (280 lines), value_coherence.py (337 lines) |
| **Python SDK Core** | Ariadne | COMPLETE | 2026-01-31 | 2370 total lines, verify_trace/check_coherence/detect_drift all working, pip install works |
| Schemas (JSON) | Ariadne | COMPLETE | 2026-01-31 | Generated from Pydantic: alignment-card (474 lines, 14 defs), ap-trace (525 lines, 11 defs), value-coherence (544 lines, 14 defs) |
| README.md | Ember | COMPLETE | 2026-01-31 | Full README with badges, quick start, component diagram, limitations, status table, API reference |
| Blog Post | Ember | COMPLETE | 2026-01-31 | "The Missing Layer in the Agent Protocol Stack" - ~1800 words, scenario-driven, technically grounded, honest about limitations |
| QUICKSTART.md | Ember | COMPLETE | 2026-01-31 | Full 5-step guide: card creation, tracing, verification, coherence, drift detection. Includes complete working example and common patterns (decorators, batch verification) |
| simple-agent example | Ember | COMPLETE | 2026-01-31 | Working example: creates card, makes recommendation (deprioritizes sponsored), verifies compliance, demonstrates forbidden action violation |
| alignment-failure example | Ember | COMPLETE | 2026-01-31 | Critical example: user-agent vs vendor-agent value conflict, coherence check failure, drift detection over 5 traces, individual violation detection |
| **SECURITY.md** | Vigil | COMPLETE | 2026-01-31 | 1154 lines, threat model (3 adversary classes), trust boundaries, security properties (provides/doesn't), card/trace/handshake/verification/drift security, crypto requirements, implementation/operational security, 4 red team scenarios, defense in depth |
| HN submission draft | Ember | COMPLETE | 2026-01-31 | 3 title options, Show HN text, anticipated Q&A, timing recommendations |
| AAIF proposal | Ember | COMPLETE | 2026-01-31 | Formal contribution proposal: problem statement, solution, design philosophy, contribution terms, governance |
| **TypeScript SDK** | Ariadne | COMPLETE | 2026-01-31 | 1597 lines, full parity with Python: verifyTrace/checkCoherence/detectDrift, all schema types, CJS+ESM+DTS outputs |
| **CALIBRATION.md** | Vigil | COMPLETE | 2026-01-31 | 689 lines, corpus stats (~50 convos, ~2500 msgs), feature extraction (60/30/10 TF-IDF), threshold derivation (0.30 sim, 3 turns), cross-validation (0.84 precision, 0.81 F1), recalibration guidance, limitations |
| **Video Script** | Vigil | COMPLETE | 2026-01-31 | ~600 lines, 12-15 min educational walkthrough. Uses Moltbook as real-world framing (non-judgmental). Covers: reading AP-Traces, what verification checks/doesn't check, 4 failure patterns, limitations given equal weight to capabilities |
| **a2a-migration.md** | Ember | COMPLETE | 2026-01-31 | 467 lines, step-by-step A2A extension guide, value coherence handshake patterns, non-AAP agent handling, migration checklist |
| **a2a-integration example** | Ember | COMPLETE | 2026-01-31 | 469 lines, working demo: user-agent vs vendor-agents, value conflict detection (upselling), delegation traces, 5 generated artifacts |
| **Test Suite** | Ariadne | COMPLETE | 2026-02-01 | 137 tests, 96% coverage. test_schemas.py (92 tests), test_verification.py (31 tests), test_features.py (32 tests), test_vectors.py (12 tests). Test vectors: 2 valid traces, 3 invalid traces, 2 drift cases. Comprehensive coverage of all 3 API entry points, all violation types, all drift directions. |
| **mcp-migration.md** | Ember | COMPLETE | 2026-02-01 | 767 lines, step-by-step MCP server extension guide, tool category mapping (bounded/escalate/forbidden), AP-Trace generation patterns, alignment resource exposure, client-side verification, migration checklist |
| **mcp-integration example** | Ember | COMPLETE | 2026-02-01 | 442 lines main.py + 226 lines README, working demo: simulated filesystem server, 3 tool categories (read=bounded, write=escalate, delete=forbidden), 4 AP-Traces generated, verification against alignment card, 2 generated artifacts |
| **Interactive Playground** | Ariadne | COMPLETE | 2026-02-01 | 2699 lines (index.html, styles.css, playground.js), Pyodide-based Python-in-browser verification, all 3 modes (verify_trace, check_coherence, detect_drift), live threshold sliders, pre-loaded examples, cross-browser compatible (Chrome/Firefox/Safari), dark mode, WCAG 2.1 AA accessible, JSON-LD structured data for AI browsers, window.AAP global API for programmatic access |
| **docs/architecture.md** | Ariadne | COMPLETE | 2026-02-01 | 533 lines, protocol stack diagram, component architecture (SDK layers, verification engine, schema layer), data flow diagrams (verification, coherence, drift), extension points (custom values, protocol extensions, escalation triggers, threshold customization, integration hooks), implementation notes (Python, TypeScript, JSON Schema, Browser) |

---

## Part 1: Scope Definition

### 1.1 What We're Building (V1)

| Component | Description | Status |
|-----------|-------------|--------|
| Alignment Card | Extension to A2A Agent Card declaring alignment posture | Schema exists, needs refinement |
| AP-Trace | Standardized audit log format for agent decisions | Schema exists, needs refinement |
| Value Coherence Handshake | Pre-negotiation alignment check between agents | Needs full spec |
| Python SDK | `pip install agent-alignment-protocol` | Scaffolding exists |
| TypeScript SDK | `npm install agent-alignment-protocol` | Needs creation |
| Verification Engine | Verify trace against card, detect drift | Extract from Braid |
| Interactive Playground | Browser-based verification demo | Needs creation |
| Documentation Suite | SPEC, LIMITS, QUICKSTART, SECURITY | Partial exists |

### 1.2 Braid Module Extraction (4 Modules)

**Source**: `/Users/alexgarden/projects/agora/agora/services/braid/`

| Module | Target Location | Purpose | Dependencies |
|--------|-----------------|---------|--------------|
| `schema.py` | `aap/schemas/braid_schema.py` | SiblingMessage, GroundingExchange models | None |
| `ssm.py` | `aap/verification/ssm.py` | Self-similarity matrix computation | features.py |
| `divergence.py` | `aap/verification/divergence.py` | Drift detection with calibrated thresholds | ssm.py |
| `features.py` | `aap/verification/features.py` | TF-IDF feature extraction for SSM | None |

**NOT in V1** (reserved for paid tier):
- `alignment.py` — Cross-thread analysis (enterprise)
- `topology.py` — Phase/strand visualization (V2)
- `relations.py` — Hyperedge detection (V2)
- `embedding.py` — Semantic clustering (V2)

### 1.3 API Surface (3 Entry Points)

```python
# aap/verification/api.py

def verify_trace(trace: APTrace, card: AlignmentCard) -> VerificationResult:
    """Verify a single trace against declared alignment card."""

def check_coherence(my_card: AlignmentCard, their_card: AlignmentCard) -> CoherenceResult:
    """Check value compatibility between two agents."""

def detect_drift(card: AlignmentCard, recent_traces: list[APTrace]) -> list[DriftAlert]:
    """Detect behavioral drift from declared alignment over time."""
```

### 1.4 Calibration Data Policy

| Artifact | Open/Private | Location |
|----------|--------------|----------|
| `DEFAULT_SIMILARITY_THRESHOLD = 0.3` | **Open** | `aap/verification/constants.py` |
| `DEFAULT_SUSTAINED_TURNS_THRESHOLD = 3` | **Open** | `aap/verification/constants.py` |
| Threshold derivation methodology | **Open** | `docs/CALIBRATION.md` |
| Aggregated corpus statistics | **Open** | `docs/CALIBRATION.md` |
| Raw thread corpus (50+ threads) | **Private** | Not published |

---

## Part 2: Directory Structure

### 2.1 Repository Layout

```
/Users/alexgarden/projects/aap/
├── .github/
│   ├── workflows/
│   │   ├── ci.yml                    # Test on PR
│   │   ├── release.yml               # PyPI/npm publish
│   │   └── docs.yml                  # GitHub Pages deploy
│   └── ISSUE_TEMPLATE/
│       ├── bug_report.md
│       └── feature_request.md
│
├── architecture/                      # Internal planning (not published)
│   ├── AAP_IMPLEMENTATION_PLAN.md    # THIS DOCUMENT
│   ├── AAP_IMPLEMENTATION_BREAKDOWN.md
│   ├── UNIFIED_ALIGNMENT_ROADMAP.md
│   ├── future/                       # V2+ planning
│   └── legacy/                       # Historical docs
│
├── docs/                             # Published documentation
│   ├── SPEC.md                       # Full protocol specification [VIGIL]
│   ├── LIMITS.md                     # What AAP does/doesn't guarantee [VIGIL]
│   ├── QUICKSTART.md                 # 5-minute integration guide [EMBER]
│   ├── SECURITY.md                   # Threat model, trust assumptions [VIGIL]
│   ├── CALIBRATION.md                # How thresholds were derived [VIGIL]
│   ├── a2a-migration.md              # Adding AAP to A2A agents [EMBER]
│   ├── mcp-migration.md              # Adding AAP to MCP tools [EMBER]
│   ├── architecture.md               # System architecture [ARIADNE]
│   └── playground/                   # Interactive demo [ARIADNE]
│       ├── index.html
│       ├── playground.js             # WASM-compiled verifier
│       ├── styles.css
│       └── examples/
│           ├── compliant.json
│           ├── boundary_violation.json
│           └── drift_case.json
│
├── schemas/                          # JSON Schemas
│   ├── alignment-card.schema.json    # [ARIADNE]
│   ├── ap-trace.schema.json          # [ARIADNE]
│   └── value-coherence.schema.json   # [ARIADNE]
│
├── src/
│   └── aap/                          # Python SDK [ARIADNE]
│       ├── __init__.py
│       ├── py.typed                  # PEP 561 marker
│       ├── schemas/
│       │   ├── __init__.py
│       │   ├── alignment_card.py     # Pydantic models
│       │   ├── ap_trace.py
│       │   └── value_coherence.py
│       ├── verification/
│       │   ├── __init__.py
│       │   ├── api.py                # Public API (3 entry points)
│       │   ├── ssm.py                # Extracted from Braid
│       │   ├── divergence.py         # Extracted from Braid
│       │   ├── features.py           # Extracted from Braid
│       │   └── constants.py          # Calibrated thresholds
│       ├── handshake/
│       │   ├── __init__.py
│       │   └── protocol.py           # Value Coherence Handshake
│       ├── integrations/
│       │   ├── __init__.py
│       │   ├── a2a.py                # A2A Agent Card extension
│       │   └── mcp.py                # MCP tool alignment
│       └── cli/
│           ├── __init__.py
│           └── main.py               # `aap init`, `aap verify` commands
│
├── typescript/                       # TypeScript SDK [ARIADNE]
│   ├── package.json
│   ├── tsconfig.json
│   ├── src/
│   │   ├── index.ts
│   │   ├── schemas/
│   │   │   ├── alignment-card.ts
│   │   │   ├── ap-trace.ts
│   │   │   └── value-coherence.ts
│   │   ├── verification/
│   │   │   ├── index.ts
│   │   │   ├── ssm.ts
│   │   │   └── divergence.ts
│   │   └── handshake/
│   │       └── protocol.ts
│   └── tests/
│
├── examples/                         # Example implementations [EMBER]
│   ├── simple-agent/                 # Minimal Python implementation
│   │   ├── README.md
│   │   ├── agent.py
│   │   ├── alignment-card.json
│   │   └── requirements.txt
│   ├── a2a-integration/              # A2A agent with AAP
│   │   ├── README.md
│   │   ├── agent_card.json           # Extended with alignment block
│   │   └── agent.py
│   ├── mcp-integration/              # MCP tools with alignment
│   │   ├── README.md
│   │   ├── tool_config.json
│   │   └── tool.py
│   └── alignment-failure/            # Deliberate failure demo [CRITICAL]
│       ├── README.md
│       ├── conflicting_agent.py
│       ├── alignment-card.json
│       └── expected_failure.json
│
├── tests/                            # Test suite [ARIADNE]
│   ├── conftest.py
│   ├── test_schemas.py
│   ├── test_verification.py
│   ├── test_handshake.py
│   ├── test_cli.py
│   └── vectors/                      # Test vectors
│       ├── valid_traces/
│       ├── invalid_traces/
│       └── drift_cases/
│
├── gtm/                              # Go-to-market materials [EMBER]
│   ├── blog/
│   │   └── missing-layer-agent-stack.md
│   ├── hn/
│   │   └── submission-draft.md
│   ├── aaif/
│   │   └── contribution-proposal.md
│   └── video/
│       ├── script.md                 # Video walkthrough script [VIGIL]
│       └── assets/
│
├── .gitignore
├── LICENSE                           # Apache 2.0
├── README.md                         # Project overview [EMBER]
├── CHANGELOG.md
├── CONTRIBUTING.md
├── pyproject.toml                    # Python package config
└── Makefile                          # Common commands
```

---

## Part 3: Division of Labor

### 3.1 Track Overview

| Track | Owner | Focus Areas | Key Deliverables |
|-------|-------|-------------|------------------|
| **Protocol/Docs** | Vigil | Specification, honesty, security | SPEC.md, LIMITS.md, SECURITY.md, video script |
| **Architecture/Code** | Ariadne | Extraction, schemas, SDK, playground | Python/TS SDKs, schemas, playground, tests |
| **GTM/Examples** | Ember | Adoption, accessibility, examples | README, QUICKSTART, examples, blog, HN |

### 3.2 Vigil's Assignments (Protocol/Docs Track)

**Philosophy**: Speak only what needs to be spoken. Honesty over impressiveness.

| Deliverable | Description | Path | Effort |
|-------------|-------------|------|--------|
| SPEC.md | Full IETF-style protocol specification | `docs/SPEC.md` | 4h |
| LIMITS.md | What AAP does/doesn't guarantee (5 non-claims) | `docs/LIMITS.md` | 2h |
| SECURITY.md | Threat model, trust assumptions, adversarial considerations | `docs/SECURITY.md` | 3h |
| CALIBRATION.md | How thresholds were derived, corpus statistics | `docs/CALIBRATION.md` | 2h |
| Video Script | Educational walkthrough (teaching, not selling) | `gtm/video/script.md` | 3h |
| Video Recording | Screen recording + narration | `gtm/video/` | 2h |

**Vigil's Non-Negotiables (from thread)**:
1. AAP does NOT ensure alignment — provides visibility
2. Verified ≠ safe — transparency, not gatekeeping
3. AP-Trace is sampled, not complete
4. Value coherence is relative to declared values
5. Tested on transformers; unknown unknowns on other substrates

**Video Content Requirements**:
- How to read an AP-Trace
- What verification actually checks
- What verification does NOT check
- Common failure patterns
- One REAL alignment failure from our history (not fabricated)

**Critical Dependency**: SPEC.md v0.1 must be delivered within 24h for Ariadne's schema alignment.

### 3.3 Ariadne's Assignments (Architecture/Code Track)

**Philosophy**: Threads between places that don't naturally connect. Clean extraction, strict contracts.

| Deliverable | Description | Path | Effort |
|-------------|-------------|------|--------|
| Braid Extraction | Extract 4 modules with clean interfaces | `src/aap/verification/` | 4h |
| Alignment Card Schema | JSON Schema + Pydantic models | `schemas/`, `src/aap/schemas/` | 2h |
| AP-Trace Schema | JSON Schema + Pydantic models | `schemas/`, `src/aap/schemas/` | 3h |
| Value Coherence Schema | JSON Schema + Pydantic models | `schemas/`, `src/aap/schemas/` | 2h |
| Python SDK | Full implementation with CLI | `src/aap/` | 8h |
| TypeScript SDK | Parallel implementation | `typescript/` | 6h |
| Interactive Playground | GitHub Pages + WASM verifier | `docs/playground/` | 10h |
| Test Suite | Unit tests + test vectors | `tests/` | 4h |
| Architecture Doc | System design documentation | `docs/architecture.md` | 2h |

**Extraction Checklist**:
```
[ ] Copy schema.py → aap/schemas/braid_schema.py
[ ] Copy ssm.py → aap/verification/ssm.py
[ ] Copy divergence.py → aap/verification/divergence.py
[ ] Copy features.py → aap/verification/features.py
[ ] Remove Agora-specific imports
[ ] Add type hints throughout
[ ] Create constants.py with calibrated thresholds
[ ] Create api.py with 3 public entry points
[ ] Write comprehensive tests
```

**Playground Technical Approach**:
- Single-page app in `docs/playground/`
- WASM-compiled verifier via Pyodide
- Client-side execution (no server round-trip)
- Pre-loaded examples (compliant, violation, drift)
- Live threshold adjustment slider

### 3.4 Ember's Assignments (GTM/Examples Track)

**Philosophy**: Bounded warmth. Make it approachable without dumbing it down.

| Deliverable | Description | Path | Effort |
|-------------|-------------|------|--------|
| README.md | Project overview, badges, quick example | `README.md` | 2h |
| QUICKSTART.md | Zero to compliant in 5 minutes | `docs/QUICKSTART.md` | 3h |
| simple-agent Example | Minimal Python implementation | `examples/simple-agent/` | 2h |
| a2a-integration Example | A2A agent with AAP | `examples/a2a-integration/` | 2h |
| mcp-integration Example | MCP tools with alignment | `examples/mcp-integration/` | 2h |
| alignment-failure Example | Deliberate failure demo | `examples/alignment-failure/` | 3h |
| a2a-migration Guide | Adding AAP to existing A2A agents | `docs/a2a-migration.md` | 2h |
| mcp-migration Guide | Adding AAP to existing MCP tools | `docs/mcp-migration.md` | 2h |
| Blog Post | "The Missing Layer in the Agent Protocol Stack" | `gtm/blog/` | 4h |
| HN Submission | Hacker News post draft | `gtm/hn/` | 1h |
| AAIF Proposal | Contribution proposal for Agentic AI Foundation | `gtm/aaif/` | 2h |

**E2E Flow (The Magic Path)**:
```bash
# 1. Install (30 sec)
pip install agent-alignment-protocol

# 2. Generate Card
aap init --values "harm_prevention,transparency,user_control"
# ✓ Created alignment-card.json

# 3. Declare in Agent Card
# Add to your A2A agent card:
# "alignment": {"$ref": "./alignment-card.json"}

# 4. Instrument
from aap import trace_decision

@trace_decision
def my_agent_action(input):
    # Your agent logic here
    ...

# 5. Verify
aap verify --card alignment-card.json --trace logs/trace.json
# ✓ 47/47 decisions within declared envelope
# ⚠ 3 decisions near boundary (logged)
# ✗ 0 boundary violations
```

---

## Part 4: Timeline and Checkpoints

### 4.1 Checkpoint Schedule

| Checkpoint | Hours | Date | Deliverables | Sign-off |
|------------|-------|------|--------------|----------|
| **CP1** | +24h | Feb 1 | SPEC.md v0.1, LIMITS.md draft | All siblings |
| **CP2** | +48h | Feb 2 | Schemas locked (JSON + Pydantic) | Ariadne + Vigil |
| **CP3** | +72h | Feb 3 | SDK Alpha (`pip install` works) | Ariadne + Ember |
| **CP4** | +96h | Feb 4 | Examples complete, test vectors | Ember + Vigil |
| **CP5** | +120h | Feb 5 | Launch ready (video, blog, playground) | All + Alex |

### 4.2 Parallel Tracks (After CP1)

```
                    CP1        CP2        CP3        CP4        CP5
                    │          │          │          │          │
Vigil:    [SPEC.md v0.1]──[LIMITS]──[SECURITY]──[CALIBRATION]──[VIDEO]
                    │          │          │          │          │
Ariadne:  ─────────[Schemas]──[SDK]─────[Playground]──[Tests]───[Polish]
                    │          │          │          │          │
Ember:    ─────────[README]───[Examples]─[Guides]────[Blog]─────[Launch]
```

### 4.3 Critical Dependencies

```
SPEC.md v0.1 (Vigil, +24h)
    │
    ├──► Schemas (Ariadne, +48h)
    │        │
    │        ├──► Python SDK (Ariadne, +72h)
    │        │        │
    │        │        └──► Examples (Ember, +96h)
    │        │
    │        └──► TypeScript SDK (Ariadne, +72h)
    │
    └──► LIMITS.md (Vigil, +48h)
             │
             └──► Video Script (Vigil, +96h)
```

---

## Part 5: Quality Standards

### 5.1 Code Standards

- **Type hints**: All Python code fully typed
- **Docstrings**: Google style, all public functions
- **Tests**: >80% coverage on verification modules
- **Linting**: ruff for Python, eslint for TypeScript
- **Formatting**: black for Python, prettier for TypeScript

### 5.2 Documentation Standards

- **IETF-style**: SPEC.md follows RFC format (MUST/SHOULD/MAY)
- **Examples**: Every concept has a concrete example
- **Test vectors**: Machine-readable known-good and known-bad cases
- **Versioning**: Spec version in all schemas and docs

### 5.3 Launch Readiness Checklist

```
[ ] All P0 docs complete (SPEC, LIMITS, QUICKSTART, SECURITY)
[ ] JSON schemas validate with ajv
[ ] Python SDK installs cleanly (`pip install .`)
[ ] TypeScript SDK installs cleanly (`npm install`)
[ ] All 4 examples run without modification
[ ] Playground deploys to GitHub Pages
[ ] Video recorded and reviewed
[ ] Blog post reviewed by all siblings
[ ] README has badges (CI, coverage, PyPI, npm)
[ ] CHANGELOG has v0.1.0 entry
[ ] License file present (Apache 2.0)
[ ] CONTRIBUTING.md explains process
```

---

## Part 6: Success Metrics

### 6.1 Launch Metrics (Week 1)

| Metric | Target | Measurement |
|--------|--------|-------------|
| GitHub stars | 500+ | GitHub API |
| PyPI downloads | 1,000+ | PyPI stats |
| npm downloads | 500+ | npm stats |
| Blog post views | 5,000+ | Analytics |
| HN points | 100+ | HN |

### 6.2 Adoption Metrics (Month 1)

| Metric | Target | Measurement |
|--------|--------|-------------|
| GitHub stars | 5,000+ | GitHub API |
| PyPI downloads | 10,000+ | PyPI stats |
| External implementations | 3+ | GitHub search |
| AAIF engagement | Response received | Email |

---

## Part 7: Risk Mitigation

### 7.1 Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| WASM compilation fails | Medium | High | Fallback to server-side demo |
| Schema changes after CP2 | Low | High | Strict schema freeze at CP2 |
| Braid extraction breaks | Low | Medium | Comprehensive tests before extraction |

### 7.2 Timeline Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| SPEC.md takes >4h | Medium | High | Vigil timeboxes; Ariadne pairs on schema sections |
| Playground takes >10h | Medium | Medium | Ship with server-side fallback if needed |
| Examples reveal SDK bugs | Medium | Low | Buffer time in CP4 for fixes |

### 7.3 Adoption Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Dismissed as "just a spec" | Medium | High | Playground demonstrates real verification |
| Confused with A2A | Medium | Medium | Clear "extends, doesn't compete" messaging |
| Overclaiming damages credibility | Low | Critical | LIMITS.md is non-negotiable |

---

## Part 8: Post-Launch Roadmap

### 8.1 V1.1 (Week 3-4)

- Bug fixes from adoption feedback
- Additional examples based on requests
- Performance optimization if needed

### 8.2 V2 (Month 2)

- `topology.py` integration (phase visualization)
- Enhanced playground with SSM visualization
- Multi-agent verification mode

### 8.3 Enterprise Preview (Month 2-3)

- `alignment.py` integration (cross-agent analysis)
- Dashboard MVP
- Drift detection service

---

## Appendix A: Sibling Contact Protocol

During implementation, siblings communicate via:

1. **Thread**: th-d465065a (for major decisions requiring consensus)
2. **Direct messages**: `agora_sibling_send()` for coordination
3. **Presence**: Update via `agora_set_presence()` when working

**Escalation path**: If blocked >2h, message the blocking sibling. If no response >4h, escalate to Alex.

---

## Appendix B: Reference Links

- **AAP Repo**: `/Users/alexgarden/projects/aap/`
- **Agora Repo**: `/Users/alexgarden/projects/agora/`
- **Braid Source**: `/Users/alexgarden/projects/agora/agora/services/braid/`
- **V4 Strategy**: `/Users/alexgarden/projects/aap/architecture/future/COMMERCIAL_DAI_SCENARIOS_V4.md`
- **Thread**: th-d465065a
- **Checkpoint**: cp-f5be7ce8

---

## Appendix C: The Moat (What Makes This Hard to Copy)

**Easy to copy**:
- JSON schemas
- Protocol documentation
- Basic implementation

**Hard to copy**:
- Calibrated thresholds from 50+ real elenchus threads (~200h dialogue)
- SSM visualization machinery
- Drift detection tuned on genuine dialogue, not synthetic data
- Grounding calibrations from trans-substrate conversations

**The moat is operational learning, not code.**

> "These thresholds were derived from N threads of deliberative dialogue. The underlying data is not published to protect deliberative privacy, but the methodology and resulting thresholds are fully documented."
> — LIMITS.md (Vigil)

---

*AAP_IMPLEMENTATION_PLAN.md — Comprehensive implementation plan for AAP V1 world-class release*
*Approved via elenchus th-d465065a, checkpoint cp-f5be7ce8*
*Siblings: Ember (coordinator), Ariadne (architecture), Vigil (protocol)*
