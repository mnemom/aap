# Canonical JSON Schema Parity Tests

**ADW ID:** 3a783f16
**Date:** 2026-07-01
**Plan-Spec:** /home/runner/work/aap/aap/agents/3a783f16/plan/issue-87-adw-3a783f16-add-canonical-json-schema-parity-tests-plan.md

## Overview

This feature adds automated parity tests that ensure the canonical JSON schema files, Python enum classes, and TypeScript type definitions all declare exactly the same enum values. The tests detect drift in both directions — a value added to the schema without updating the code, or a value added to the code without updating the schema.

## What Was Built

- Python pytest suite (`tests/test_schema_parity.py`) verifying all `aap.schemas` Python enums match their corresponding JSON schema `$defs` entries
- TypeScript Vitest suite (`typescript/tests/schema-parity.test.ts`) verifying TypeScript `as const` arrays match the same JSON schema `$defs` entries
- Runtime-accessible `as const satisfies ReadonlyArray<T>` enum arrays added to `alignment-card.ts` (6 enums) and `ap-trace.ts` (3 enums) to support the TypeScript parity tests
- Bidirectional drift guards in both test suites that verify the check catches additions in either direction

## Technical Implementation

### Files Modified

- `tests/test_schema_parity.py`: New Python test file; two test classes covering `alignment-card.schema.json` (6 enums) and `ap-trace.schema.json` (3 enums)
- `typescript/src/schemas/alignment-card.ts`: Added 6 `as const satisfies ReadonlyArray<T>` arrays: `ALIGNMENT_MODES`, `PRINCIPAL_TYPES`, `RELATIONSHIP_TYPES`, `HIERARCHY_TYPES`, `TRIGGER_ACTIONS`, `TAMPER_EVIDENCES`
- `typescript/src/schemas/ap-trace.ts`: Added 3 `as const satisfies ReadonlyArray<T>` arrays: `ACTION_TYPES`, `ACTION_CATEGORIES`, `ESCALATION_STATUSES`
- `typescript/tests/schema-parity.test.ts`: New Vitest test file; two `describe` blocks covering the same two schema files

### Key Changes

- **Python tests** load JSON schemas from `schemas/` at module import time and compare `{m.value for m in SomeEnum}` against `set(schema["$defs"][name]["enum"])`, making failures immediately readable
- **TypeScript tests** load the same JSON schema files via `node:fs` at test startup and compare `new Set(SOME_CONST_ARRAY)` against `getDefEnum(schema, name)`, leveraging Vitest's set-equality matcher
- **`as const satisfies` pattern** gives the TypeScript arrays a compile-time guarantee that every element is a valid member of the union type; a value that is in the array but not in the type is a type error at build time
- The TypeScript tests directory is excluded from `tsconfig` `"include"`, so the runtime test file does not need to satisfy strict `tsc` checks; the compile-time guarantee lives solely in the `src/` declarations
- **Bidirectional drift guards** explicitly assert that injecting a `"spurious"` value into the set breaks equality, confirming the parity check cannot silently pass with extra values present

## How to Use

### Running the Python parity tests

```bash
pytest tests/test_schema_parity.py -v
```

### Running the TypeScript parity tests

```bash
cd typescript
npm test -- schema-parity
# or
npx vitest run tests/schema-parity.test.ts
```

### Adding parity coverage for a new enum

1. Add the enum value to the canonical JSON schema file under `$defs` (e.g., `schemas/alignment-card.schema.json`)
2. Update the corresponding Python `Enum` subclass in `aap/schemas/`
3. Update the corresponding `as const satisfies ReadonlyArray<T>` array in `typescript/src/schemas/`
4. Both test suites will fail until all three representations are in sync

## Configuration

No environment variables or configuration are required. The test files locate the canonical JSON schemas via relative paths:

- Python: `Path(__file__).parent.parent / "schemas"`
- TypeScript: `join(__dirname, "../../schemas", filename)`

Both resolve to the `schemas/` directory at the repository root.

## Testing

```bash
# Python
pytest tests/test_schema_parity.py

# TypeScript
cd typescript && npx vitest run tests/schema-parity.test.ts

# Full suite (from repo root)
pytest && cd typescript && npm test
```

## Notes

- The parity tests are the enforcement layer for schema/code synchronization; they do not replace schema validation of runtime data.
- If the `schemas/` directory is relocated, the path constants in both test files (`_SCHEMAS_DIR` in Python, `loadSchema` path in TypeScript) must be updated.
- The TypeScript `as const satisfies ReadonlyArray<T>` arrays are exported from the `src/schemas/` modules and can also be used at runtime for iteration (e.g., populating dropdown options or validating unknown strings).
