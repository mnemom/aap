# AGENTS.md — aap

You are a coding agent working on the **Agent Alignment Protocol (AAP)**.
Audience: AI coding tools (Claude Code, Cursor, Cline, Aider) and humans
onboarding via them. This file is the canonical entry point for coding
agents.

For the user-facing protocol explanation, start at the README. For the
public agent-readability commitment that depends on this repo staying
Apache 2.0, see https://www.mnemom.ai/for-agents (commitment #6).

## What this repo is

AAP is the alignment-card schema + verification toolkit that binds an
agent's declared intent (the Alignment Card) to its runtime behavior.
Dual-language: Python is the reference, TypeScript mirrors it. Both
are published on the same release cadence under matching versions.

- **Python package**: `agent-alignment-protocol` on PyPI
- **npm package**: `@mnemom/agent-alignment-protocol` on npm
- **License**: Apache-2.0 (forever — see commitment #6 on /for-agents)

## Stack

- **Python** (reference implementation): `src/aap/`, hatchling build,
  pydantic v2 models, jsonschema validation, click CLI.
- **TypeScript** (mirror): `typescript/src/`, tsup bundler, vitest,
  TypeScript strict.
- **Schemas**: `schemas/*.schema.json` are the normative spec. Both
  language implementations validate against these.

## Install + dev — Python

```bash
# From repo root
pip install -e ".[dev]"        # editable install with dev extras
pytest                         # run all tests
ruff check .                   # lint
mypy src/aap                   # type-check
python -m aap.cli --help       # exercise the CLI
```

## Install + dev — TypeScript

```bash
cd typescript
npm install
npm test                       # vitest run
npm run typecheck              # tsc --noEmit
npm run build                  # tsup → dist/
npm run dev                    # tsup --watch
```

## Project layout

```
schemas/                       # NORMATIVE — both impls validate against these
  alignment-card.schema.json
  ap-trace.schema.json
  value-coherence.schema.json
src/aap/                       # Python implementation (reference)
typescript/src/                # TypeScript implementation (mirror)
typescript/tests/
tests/                         # Python tests
examples/                      # Example alignment cards + traces
docs/                          # Protocol docs (longer-form than README)
scripts/                       # Build + release helpers
*.json                         # Sample agent cards used in tests + docs
```

## Conventions

- **Schemas are the source of truth.** When you change a schema, both
  Python and TypeScript implementations must update to match. CI fails
  the cross-language consistency check otherwise.
- **Versions stay in lockstep.** `pyproject.toml::project.version` and
  `typescript/package.json::version` must match before release.
- **Apache-2.0 only.** This is a public commitment (see /for-agents
  commitment #6). Do not relicense.
- Commit messages: imperative, concise, describe the **why**.
- No README/doc files unless explicitly requested.
- The agent-card example JSONs at the repo root (`user-agent-card.json`,
  `vendor-agent-card.json`, `compatible-vendor-card.json`) are
  fixture data referenced by tests + docs. Don't break their shape.

## Branch protection + deploy

- **Never commit directly to `main`.** Always feature branch first
  (matches every Mnemom repo).
- Branch protection is enforced.
- Flow: feature branch → PR → merge → orchestrator (`mnemom/deploy`)
  publishes to npm + PyPI on tagged releases.
- Do not modify the deploy orchestrator. It is third-party-managed.

## What you should NOT do

- Don't add new runtime dependencies without explicit approval. AAP
  is intentionally minimal — pydantic + jsonschema + click on Python,
  zero deps on TypeScript runtime.
- Don't relicense.
- Don't skip pre-commit hooks (`--no-verify`).
- Don't `git push --force` to `main`.
- Don't drift the Python and TypeScript implementations apart. If you
  add a feature on one side, file an issue or PR on the other within
  the same release window.
- Don't bump the version unilaterally. Releases are coordinated.

## Cross-links

- **Sister protocol**: [Agent Integrity Protocol (AIP)](https://github.com/mnemom/aip) —
  runtime checkpoints that AAP cards govern.
- **OTel exporter**: [aip-otel-exporter](https://github.com/mnemom/aip-otel-exporter) —
  ships AIP/AAP verdicts into OpenTelemetry pipelines.
- **Public commitment depending on this repo**:
  https://www.mnemom.ai/for-agents — commitment #6 ("Open protocols")
  asserts AAP stays Apache 2.0; the watchdog verifies the LICENSE
  string nightly.
- **Mintlify-hosted protocol docs**: https://docs.mnemom.ai/protocols/aap
