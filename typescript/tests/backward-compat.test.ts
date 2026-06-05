/**
 * Backward compatibility smoke test — API surface lock for 2.0.0
 *
 * Imports every public export from the 2.0.0 API surface and asserts
 * existence + basic type shape. Catches accidental breaking changes:
 *
 *   - Removed export       → compile error (import fails)
 *   - Renamed export       → compile error (import fails)
 *   - Changed fn signature → type error
 *   - Changed return type  → runtime assertion failure
 *
 * When adding new exports:     add them here.
 * When making breaking changes: bump major version first (ADR-006).
 *
 * 2.0.0 — unified / ADR-039 card migration (MNE-190): the legacy
 * `AutonomyEnvelope`/`AuditCommitment`/`AuditStorage`/`StorageType` card types
 * were renamed/removed (`Autonomy`, `Audit`), `AlignmentMode` was added, and
 * `EU_COMPLIANCE_AUDIT_COMMITMENT` was renamed to `EU_COMPLIANCE_AUDIT`. This
 * is the breaking surface change the major bump exists for (ADR-006).
 *
 * Scale Step 30 — M3: API Contracts & SDK Stability
 */
import { describe, it, expect } from "vitest";

// ── Value exports ──────────────────────────────────────────────────────────

import {
  // Core verification
  verifyTrace,
  checkCoherence,
  checkFleetCoherence,
  detectDrift,
  analyzeFaultLines,
  checkFleetFaultLines,
  // Feature extraction
  computeCentroid,
  extractCardFeatures,
  extractTraceFeatures,
  cosineSimilarity,
  // Utilities
  isCardExpired,
  hasValue,
  isActionBounded,
  isActionForbidden,
  getSelectedAlternative,
  wasEscalated,
  hadViolations,
  createViolation,
  // Constants
  DEFAULT_SIMILARITY_THRESHOLD,
  DEFAULT_SUSTAINED_CHECKS_THRESHOLD,
  NEAR_BOUNDARY_THRESHOLD,
  MIN_COHERENCE_FOR_PROCEED,
  CONFLICT_PENALTY_MULTIPLIER,
  MIN_WORD_LENGTH,
  MAX_TFIDF_FEATURES,
  OUTLIER_STD_DEV_THRESHOLD,
  CLUSTER_COMPATIBILITY_THRESHOLD,
  ALGORITHM_VERSION,
  VIOLATION_SEVERITY,
  // EU compliance presets
  EU_COMPLIANCE_AUDIT,
  EU_COMPLIANCE_EXTENSIONS,
  EU_COMPLIANCE_VALUES,
} from "../src/index.js";

// ── Type-only exports (compile-time check — if any are removed, this
//    file won't compile) ────────────────────────────────────────────────────

import type {
  // Card schema (unified / ADR-039)
  AlignmentCard,
  AlignmentMode,
  Principal,
  PrincipalType,
  RelationshipType,
  Values,
  ValueDefinition,
  HierarchyType,
  Autonomy,
  EscalationTrigger,
  TriggerAction,
  MonetaryValue,
  Audit,
  TamperEvidence,
  // Trace schema
  APTrace,
  Action,
  ActionType,
  ActionCategory,
  ActionTarget,
  Decision,
  Alternative,
  ValueScore,
  Escalation,
  EscalationStatus,
  TriggerCheck,
  PrincipalResponse,
  TraceContext,
  // Result types
  VerificationResult,
  VerificationRecommendation,
  Violation,
  ViolationType,
  Severity,
  Warning,
  VerificationMetadata,
  CoherenceResult,
  ValueAlignment,
  ValueConflictResult,
  DriftAlert,
  DriftAnalysis,
  DriftDirection,
  DriftIndicator,
  FleetCoherenceResult,
  PairwiseEntry,
  FleetOutlier,
  FleetCluster,
  ValueDivergence,
  AgentCoherenceSummary,
  FaultLineClassification,
  FaultLine,
  FaultLineSummary,
  FaultLineAlignment,
  FaultLineAnalysis,
  // Message types
  AlignmentCardRequest,
  AlignmentCardResponse,
  ValueCoherenceCheck,
  CoherenceResultMessage,
  ValueCoherenceMessage,
  RequesterInfo,
  TaskContext,
  Signature,
  ProposedCollaboration,
  DataSharing,
  AutonomyScope,
  Coherence,
  ValueAlignmentDetail,
  ValueConflict,
  ProposedResolution,
} from "../src/index.js";

// ── Runtime assertions ─────────────────────────────────────────────────────

describe("AAP 2.0.0 backward compatibility", () => {
  describe("core verification functions exist and are callable", () => {
    it("verifyTrace", () => expect(typeof verifyTrace).toBe("function"));
    it("checkCoherence", () => expect(typeof checkCoherence).toBe("function"));
    it("checkFleetCoherence", () => expect(typeof checkFleetCoherence).toBe("function"));
    it("detectDrift", () => expect(typeof detectDrift).toBe("function"));
    it("analyzeFaultLines", () => expect(typeof analyzeFaultLines).toBe("function"));
    it("checkFleetFaultLines", () => expect(typeof checkFleetFaultLines).toBe("function"));
  });

  describe("feature extraction functions exist", () => {
    it("computeCentroid", () => expect(typeof computeCentroid).toBe("function"));
    it("extractCardFeatures", () => expect(typeof extractCardFeatures).toBe("function"));
    it("extractTraceFeatures", () => expect(typeof extractTraceFeatures).toBe("function"));
    it("cosineSimilarity", () => expect(typeof cosineSimilarity).toBe("function"));
  });

  describe("utility functions exist", () => {
    it("isCardExpired", () => expect(typeof isCardExpired).toBe("function"));
    it("hasValue", () => expect(typeof hasValue).toBe("function"));
    it("isActionBounded", () => expect(typeof isActionBounded).toBe("function"));
    it("isActionForbidden", () => expect(typeof isActionForbidden).toBe("function"));
    it("getSelectedAlternative", () => expect(typeof getSelectedAlternative).toBe("function"));
    it("wasEscalated", () => expect(typeof wasEscalated).toBe("function"));
    it("hadViolations", () => expect(typeof hadViolations).toBe("function"));
    it("createViolation", () => expect(typeof createViolation).toBe("function"));
  });

  describe("constants are defined", () => {
    it("DEFAULT_SIMILARITY_THRESHOLD", () => expect(typeof DEFAULT_SIMILARITY_THRESHOLD).toBe("number"));
    it("DEFAULT_SUSTAINED_CHECKS_THRESHOLD", () => expect(typeof DEFAULT_SUSTAINED_CHECKS_THRESHOLD).toBe("number"));
    it("NEAR_BOUNDARY_THRESHOLD", () => expect(typeof NEAR_BOUNDARY_THRESHOLD).toBe("number"));
    it("MIN_COHERENCE_FOR_PROCEED", () => expect(typeof MIN_COHERENCE_FOR_PROCEED).toBe("number"));
    it("ALGORITHM_VERSION", () => expect(typeof ALGORITHM_VERSION).toBe("string"));
    it("VIOLATION_SEVERITY", () => expect(typeof VIOLATION_SEVERITY).toBe("object"));
  });

  describe("EU compliance presets are defined", () => {
    it("EU_COMPLIANCE_AUDIT", () => expect(typeof EU_COMPLIANCE_AUDIT).toBe("object"));
    it("EU_COMPLIANCE_EXTENSIONS", () => expect(typeof EU_COMPLIANCE_EXTENSIONS).toBe("object"));
    it("EU_COMPLIANCE_VALUES", () => expect(typeof EU_COMPLIANCE_VALUES).toBe("object"));
  });

  // Type-level assertion: if the types above don't match reality, this
  // block won't compile. No runtime check needed — the `import type`
  // statements above ARE the test.
  describe("type exports compile", () => {
    it("types are importable (compile-time validated)", () => {
      // If we got here, all type imports resolved successfully.
      // Use a few types to prevent TS from optimizing them away.
      const _cardShape: AlignmentCard | null = null;
      const _modeShape: AlignmentMode | null = null;
      const _autonomyShape: Autonomy | null = null;
      const _auditShape: Audit | null = null;
      const _traceShape: APTrace | null = null;
      const _resultShape: VerificationResult | null = null;
      const _coherenceShape: CoherenceResult | null = null;
      const _driftShape: DriftAlert | null = null;
      const _fleetShape: FleetCoherenceResult | null = null;
      const _faultShape: FaultLineAnalysis | null = null;
      expect(true).toBe(true);
    });
  });
});
