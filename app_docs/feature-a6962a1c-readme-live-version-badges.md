# README Live Version Badges

**ADW ID:** a6962a1c
**Date:** 2026-07-27
**Plan-Spec:** agents/a6962a1c/plan/issue-112-adw-a6962a1c-update-readme-version-block-plan.md

## Overview

Replaces the hard-coded `**Current Version**: 0.4.0` string in the README `## Status` section with live shields.io badges that pull the current version directly from PyPI and npm. This eliminates a stale version string that was two major versions behind (package is at 2.0.0) and ensures the displayed version self-updates on every publish with no future maintenance.

## What Was Built

- Replaced the static `0.4.0` version string in `README.md` line 312 with inline shields.io badges for both the Python (PyPI) and TypeScript (npm) packages
- Reused the exact badge URLs already present at the top of the README (lines 6–7) to maintain consistency

## Technical Implementation

### Files Modified

- `README.md`: Line 312 — swapped `**Current Version**: 0.4.0` for two inline shields.io version badges

### Key Changes

- The PyPI badge (`https://img.shields.io/pypi/v/agent-alignment-protocol.svg`) links to the PyPI project page and displays the live published version
- The npm badge (`https://img.shields.io/npm/v/@mnemom/agent-alignment-protocol.svg`) links to the npm package page and displays the live published version
- Change is docs-only — no source code, tests, or workflow files were touched
- Badge URLs are identical to those already used at the top of the README, introducing no new external dependencies

## How to Use

The version badges render automatically in any Markdown renderer (GitHub, npm, PyPI) with internet access. No action is required — the badges update whenever a new version is published to either registry.

## Configuration

No configuration required. The badges resolve live from shields.io on each page load.

## Testing

This is a docs-only change. Verify the README renders correctly on GitHub after merging. To confirm the live badge values match the actual published versions:

```bash
curl -s https://pypi.org/pypi/agent-alignment-protocol/json | python3 -c "import sys,json; d=json.load(sys.stdin); print('PyPI:', d['info']['version'])"
curl -s https://registry.npmjs.org/@mnemom/agent-alignment-protocol/latest | python3 -c "import sys,json; d=json.load(sys.stdin); print('npm:', d['version'])"
```

For functional regression checks:

```bash
ruff check . && ruff format --check .
mypy src/
pytest
hatch build
```

## Notes

- Shields.io badges require internet access to resolve; they may render stale or unavailable in offline CI preview environments. This is the accepted trade-off for live badges over a hand-maintained string.
- If a version bump lands after this PR merges, the badges will automatically reflect the newer version — this is the desired behavior.
