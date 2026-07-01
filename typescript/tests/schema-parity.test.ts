/**
 * Schema-parity tests — canonical JSON schema enum values match TypeScript implementation.
 *
 * For each enum union type in the canonical JSON schema files, these tests assert
 * that the corresponding TypeScript as-const array declares exactly the same members.
 *
 * Enforcement is runtime-only: the tests/ directory is excluded from tsconfig
 * ("include": ["src/**\/*"]), so `tsc --noEmit` does not evaluate this file.
 * The compile-time guarantee (satisfies ReadonlyArray<T>) lives in the src/
 * declarations and fires for any drift introduced directly in those constants.
 */

import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

import {
  ALIGNMENT_MODES,
  HIERARCHY_TYPES,
  PRINCIPAL_TYPES,
  RELATIONSHIP_TYPES,
  TAMPER_EVIDENCES,
  TRIGGER_ACTIONS,
} from "../src/schemas/alignment-card";
import {
  ACTION_CATEGORIES,
  ACTION_TYPES,
  ESCALATION_STATUSES,
} from "../src/schemas/ap-trace";

const __dirname = dirname(fileURLToPath(import.meta.url));

function loadSchema(filename: string): Record<string, unknown> {
  const abs = join(__dirname, "../../schemas", filename);
  return JSON.parse(readFileSync(abs, "utf-8")) as Record<string, unknown>;
}

function getDefEnum(
  schema: Record<string, unknown>,
  defName: string,
): Set<string> {
  const defs = schema["$defs"] as Record<string, Record<string, unknown>>;
  return new Set(defs[defName]["enum"] as string[]);
}

// ============================================================================
// alignment-card.schema.json parity
// ============================================================================

describe("alignment-card schema enum parity", () => {
  const schema = loadSchema("alignment-card.schema.json");

  it("ALIGNMENT_MODES matches schema AlignmentMode enum", () => {
    expect(new Set(ALIGNMENT_MODES)).toEqual(getDefEnum(schema, "AlignmentMode"));
  });

  it("PRINCIPAL_TYPES matches schema PrincipalType enum", () => {
    expect(new Set(PRINCIPAL_TYPES)).toEqual(getDefEnum(schema, "PrincipalType"));
  });

  it("RELATIONSHIP_TYPES matches schema RelationshipType enum", () => {
    expect(new Set(RELATIONSHIP_TYPES)).toEqual(getDefEnum(schema, "RelationshipType"));
  });

  it("HIERARCHY_TYPES matches schema HierarchyType enum", () => {
    expect(new Set(HIERARCHY_TYPES)).toEqual(getDefEnum(schema, "HierarchyType"));
  });

  it("TRIGGER_ACTIONS matches schema TriggerAction enum", () => {
    expect(new Set(TRIGGER_ACTIONS)).toEqual(getDefEnum(schema, "TriggerAction"));
  });

  it("TAMPER_EVIDENCES matches schema TamperEvidence enum", () => {
    expect(new Set(TAMPER_EVIDENCES)).toEqual(getDefEnum(schema, "TamperEvidence"));
  });

  it("ALIGNMENT_MODES drift guard: extra value is detected", () => {
    const schemaValues = getDefEnum(schema, "AlignmentMode");
    const withExtra = new Set([...ALIGNMENT_MODES, "spurious"]);
    expect(withExtra).not.toEqual(schemaValues);
  });
});

// ============================================================================
// ap-trace.schema.json parity
// ============================================================================

describe("ap-trace schema enum parity", () => {
  const schema = loadSchema("ap-trace.schema.json");

  it("ACTION_TYPES matches schema ActionType enum", () => {
    expect(new Set(ACTION_TYPES)).toEqual(getDefEnum(schema, "ActionType"));
  });

  it("ACTION_CATEGORIES matches schema ActionCategory enum", () => {
    expect(new Set(ACTION_CATEGORIES)).toEqual(getDefEnum(schema, "ActionCategory"));
  });

  it("ESCALATION_STATUSES matches schema EscalationStatus enum", () => {
    expect(new Set(ESCALATION_STATUSES)).toEqual(getDefEnum(schema, "EscalationStatus"));
  });

  it("ESCALATION_STATUSES drift guard: extra value is detected", () => {
    const schemaValues = getDefEnum(schema, "EscalationStatus");
    const withExtra = new Set([...ESCALATION_STATUSES, "spurious"]);
    expect(withExtra).not.toEqual(schemaValues);
  });
});
