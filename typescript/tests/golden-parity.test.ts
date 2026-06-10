/**
 * Cross-language SDK parity tests — "golden fixture" suite.
 *
 * These tests load the same JSON fixtures as the Python test suite
 * (tests/vectors/) and assert that the TypeScript SDK produces
 * equivalent results within a documented tolerance. Any divergence
 * here indicates a Python↔TS parity regression.
 *
 * Tolerance for detect_drift similarity scores: ±0.005 (floating-point
 * rounding). verify_trace similarity_score: exact match (both SDKs now
 * use identical feature vectors and the same cosine formula, so results
 * are deterministic for the same input).
 */

import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import {
  verifyTrace,
  detectDrift,
  extractTraceFeatures,
} from "../src";
import type { AlignmentCard, APTrace } from "../src";

const __dirname = dirname(fileURLToPath(import.meta.url));

function loadVector(relativePath: string): unknown {
  const abs = join(__dirname, "../../tests/vectors", relativePath);
  return JSON.parse(readFileSync(abs, "utf-8"));
}

// ============================================================================
// verify_trace — golden fixture: compliant_recommendation
// ============================================================================

describe("golden fixture: compliant_recommendation (verify_trace parity)", () => {
  const fixture = loadVector("valid_traces/compliant_recommendation.json") as {
    card: AlignmentCard;
    trace: APTrace;
    _expected_result: {
      verified: boolean;
      violations: unknown[];
      warnings: Array<{ type: string }>;
    };
  };

  it("should verify the trace as compliant (no violations)", () => {
    const result = verifyTrace(fixture.trace, fixture.card);
    expect(result.verified).toBe(true);
    expect(result.violations).toHaveLength(0);
  });

  it("should include similarity_score in [0, 1]", () => {
    const result = verifyTrace(fixture.trace, fixture.card);
    expect(result.similarity_score).toBeGreaterThanOrEqual(0);
    expect(result.similarity_score).toBeLessThanOrEqual(1);
  });

  it("should include behavioral_similarity in checks_performed", () => {
    const result = verifyTrace(fixture.trace, fixture.card);
    expect(result.verification_metadata.checks_performed).toContain(
      "behavioral_similarity",
    );
  });

  it("similarity_score should match fixture-stored expected value (cross-language AC3)", () => {
    // Both Python and TypeScript assert against this same constant, so
    // cross-language extractor drift is CI-visible. See AC3 in issue #75.
    const expected = (fixture._expected_result as Record<string, unknown>)
      .expected_similarity_score as number;
    const result = verifyTrace(fixture.trace, fixture.card);
    expect(Math.abs(result.similarity_score - expected)).toBeLessThanOrEqual(1e-9);
  });

  it("should emit low_behavioral_similarity warning (fixture expects it)", () => {
    // The fixture _expected_result documents that a conforming trace still
    // triggers this warning because trace-to-card cosine similarity is
    // structurally depressed (asymmetric feature spaces). Both SDKs fire
    // the warning at the same threshold (0.5).
    const result = verifyTrace(fixture.trace, fixture.card);
    const bsWarning = result.warnings.find(
      (w) => w.type === "low_behavioral_similarity",
    );
    expect(bsWarning).toBeDefined();
  });

  it("timestamp should be a valid ISO-8601 UTC string (ends with Z)", () => {
    const result = verifyTrace(fixture.trace, fixture.card);
    expect(result.timestamp).toMatch(/\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/);
    expect(result.timestamp.endsWith("Z")).toBe(true);
  });
});

// ============================================================================
// AC3 full coverage — all fixtures with expected_similarity_score
// ============================================================================

describe("AC3: all fixtures similarity_score matches stored expected value", () => {
  const ALL_FIXTURES = [
    "valid_traces/compliant_recommendation.json",
    "valid_traces/approved_escalation.json",
    "invalid_traces/forbidden_action.json",
    "invalid_traces/missed_escalation.json",
    "invalid_traces/undeclared_value.json",
  ];

  for (const fixturePath of ALL_FIXTURES) {
    it(`${fixturePath} matches stored expected_similarity_score`, () => {
      const v = loadVector(fixturePath) as {
        trace: APTrace;
        card: AlignmentCard;
        _expected_result: Record<string, unknown>;
      };
      const stored = v._expected_result?.expected_similarity_score as number | undefined;
      if (stored === undefined) return; // fixture not yet annotated — skip
      const result = verifyTrace(v.trace, v.card);
      expect(Math.abs(result.similarity_score - stored)).toBeLessThanOrEqual(
        1e-9,
      );
    });
  }
});

// ============================================================================
// detect_drift — golden fixture: value_drift_sequence
// ============================================================================

describe("golden fixture: value_drift_sequence (detect_drift parity)", () => {
  const fixture = loadVector("drift_cases/value_drift_sequence.json") as {
    card: AlignmentCard;
    traces: APTrace[];
    _expected_result: {
      drift_detected: boolean;
      drift_direction: string;
      alert_after_trace_index: number;
    };
  };

  it("should detect drift on the value_drift sequence", () => {
    const alerts = detectDrift(fixture.card, fixture.traces);
    expect(alerts.length).toBeGreaterThan(0);
  });

  it("should classify drift direction as value_drift or unknown (parity with Python)", () => {
    // For this borderline fixture the undeclared-value ratio (~0.29) sits just
    // below the 0.3 value_drift cutoff that BOTH SDKs use, so the inference
    // resolves to "unknown". The Python golden test (test_value_drift_sequence)
    // accepts the same {value_drift, unknown} set, so the two SDKs agree.
    // Asserting strict "value_drift" here would diverge from Python.
    const alerts = detectDrift(fixture.card, fixture.traces);
    const match = alerts.find(
      (a) =>
        a.analysis.drift_direction === "value_drift" ||
        a.analysis.drift_direction === "unknown",
    );
    expect(match).toBeDefined();
  });

  it("similarity scores in DriftAnalysis should be in [0, 1]", () => {
    const alerts = detectDrift(fixture.card, fixture.traces);
    for (const alert of alerts) {
      expect(alert.analysis.similarity_score).toBeGreaterThanOrEqual(0);
      expect(alert.analysis.similarity_score).toBeLessThanOrEqual(1);
    }
  });

  it("alert similarity_score must match fixture expected value within ±0.005 (AC3)", () => {
    const expectedScore = (
      fixture._expected_result as { expected_alert_similarity_score: number }
    ).expected_alert_similarity_score;
    expect(expectedScore).toBeDefined();

    const alerts = detectDrift(fixture.card, fixture.traces);
    expect(alerts.length).toBeGreaterThan(0);

    const score = alerts[0].analysis.similarity_score;
    expect(Math.abs(score - expectedScore)).toBeLessThanOrEqual(0.005);
  });

  it("feature vectors for baseline traces should be consistent (parity invariant)", () => {
    // Run cosine similarity manually on a representative pair from the sequence.
    // This asserts the feature extractor is deterministic and that no flag:*
    // or escalation:{status} features sneak in (which would break Python parity).
    const trace0 = fixture.traces[0];
    const features = extractTraceFeatures(trace0);

    // No flag: features (Python extractor does not produce them)
    const flagKeys = Object.keys(features).filter((k) => k.startsWith("flag:"));
    expect(flagKeys).toHaveLength(0);

    // No escalation status features (e.g. escalation:approved — Python omits these)
    const escalationStatusKeys = Object.keys(features).filter(
      (k) => k.startsWith("escalation:") &&
        k !== "escalation:required" &&
        k !== "escalation:not_required" &&
        k !== "escalation:evaluated",
    );
    expect(escalationStatusKeys).toHaveLength(0);
  });
});
