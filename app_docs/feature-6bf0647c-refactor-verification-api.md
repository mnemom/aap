# Refactor: verification/api.py Tech-Debt Hotspot

**ADW ID:** 6bf0647c
**Date:** 2026-07-09
**Plan-Spec:** /home/runner/work/aap/aap/agents/6bf0647c/plan/issue-94-adw-6bf0647c-refactor-verification-api-plan.md

## Overview

This change addresses a tech-debt hotspot in `src/aap/verification/api.py` by extracting two large inline logic blocks from `check_coherence()` and `check_fleet_coherence()` into focused private helper functions. The refactor reduces cognitive complexity in the two public functions without changing any external behavior or return types.

## What Was Built

- `_collect_value_conflicts()` — new private helper that encapsulates the pairwise conflict-detection loop previously inlined inside `check_coherence()`
- `_compute_fleet_clusters()` — new private helper that encapsulates the BFS connected-component traversal, internal-coherence calculation, and `FleetCluster` construction previously inlined inside `check_fleet_coherence()`
- Simplified pair-membership check in internal-coherence loop from a two-condition `or` expression to a set-equality comparison (`{pair.agent_a, pair.agent_b} == {component[ci], component[cj]}`)
- Replaced the explicit `cluster_id` integer counter with `enumerate()` over a generator expression

## Technical Implementation

### Files Modified

- `src/aap/verification/api.py`: Extracted two private helper functions; `check_coherence()` and `check_fleet_coherence()` now delegate to them

### Key Changes

- `_collect_value_conflicts(my_values, their_values, my_conflicts, their_conflicts)` takes four `set[str]` arguments and returns `list[ValueConflict]`; it is called by `check_coherence()` in place of the previous 23-line inline block
- `_compute_fleet_clusters(agent_ids, adjacency, pairwise_matrix, cards)` performs BFS over the compatibility graph and assembles `FleetCluster` objects; it replaces a 64-line inline block inside `check_fleet_coherence()`
- The internal-coherence pair lookup now uses `{pair.agent_a, pair.agent_b} == {component[ci], component[cj]}` (set equality), removing a duplicate condition
- `cluster_id` counter variable removed; `enumerate()` with a filtered generator (`a for a in agent_ids if a not in visited`) drives cluster ID assignment directly

## How to Use

These are internal implementation changes — the public API (`verify_trace`, `check_coherence`, `check_fleet_coherence`) is unchanged. Callers require no updates.

## Configuration

No configuration changes.

## Testing

Run the existing test suite to verify no behavioral regression:

```bash
pytest src/aap/verification/
```

Type-check with mypy (enforced in CI):

```bash
mypy src/
```

## Notes

- Behavior is identical to the pre-refactor implementation; only structure changed.
- The extracted helpers are module-private (underscore-prefixed) and are not part of the public API surface.
- The set-equality simplification in `_compute_fleet_clusters` is semantically equivalent to the previous two-branch `or` condition.
