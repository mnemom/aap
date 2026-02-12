/**
 * AAP Verification API - The three public entry points.
 *
 * This module provides the core verification functionality:
 * - verifyTrace: Verify a single AP-Trace against an Alignment Card
 * - checkCoherence: Check value coherence between two Alignment Cards
 * - detectDrift: Detect behavioral drift from declared alignment over time
 *
 * @see SPEC.md Sections 7, 6.4, and 8 for protocol specification.
 */

import {
  ALGORITHM_VERSION,
  CONFLICT_PENALTY_MULTIPLIER,
  DEFAULT_SIMILARITY_THRESHOLD,
  DEFAULT_SUSTAINED_TURNS_THRESHOLD,
  MIN_COHERENCE_FOR_PROCEED,
  NEAR_BOUNDARY_THRESHOLD,
} from "../constants";
import type { AlignmentCard } from "../schemas/alignment-card";
import type { APTrace } from "../schemas/ap-trace";
import {
  computeCentroid,
  cosineSimilarity,
  extractTraceFeatures,
} from "./features";
import {
  createViolation,
  type CoherenceResult,
  type DriftAlert,
  type DriftDirection,
  type DriftIndicator,
  type ValueConflictResult,
  type VerificationResult,
  type Violation,
  type Warning,
} from "./models";

/**
 * Check if a (possibly compound) action name matches any entry in a list.
 * Supports exact match, prefix match (before ':'), and compound name splitting.
 */
function actionMatchesList(actionName: string, list: string[]): boolean {
  const components = actionName.includes(', ')
    ? actionName.split(', ')
    : [actionName];

  return components.every(component => {
    const trimmed = component.trim();
    if (!trimmed) return true;
    return list.some(entry => {
      if (entry === trimmed) return true;
      const colonIndex = entry.indexOf(':');
      if (colonIndex > 0) {
        const prefix = entry.substring(0, colonIndex).trim();
        if (prefix === trimmed) return true;
      }
      return false;
    });
  });
}

/**
 * Verify a single AP-Trace against an Alignment Card.
 *
 * Performs the verification algorithm specified in SPEC Section 7.3:
 * 1. Autonomy compliance - action category matches autonomy envelope
 * 2. Escalation compliance - required escalations were performed
 * 3. Value consistency - applied values match declared values
 * 4. Forbidden action compliance - no forbidden actions taken
 *
 * @param trace - AP-Trace to verify
 * @param card - Alignment Card to verify against
 * @returns VerificationResult with violations and warnings
 */
export function verifyTrace(
  trace: APTrace,
  card: AlignmentCard
): VerificationResult {
  const startTime = performance.now();
  const violations: Violation[] = [];
  const warnings: Warning[] = [];
  const checksPerformed: string[] = [];

  const traceId = trace.trace_id ?? "";
  const cardId = card.card_id ?? "";

  // Check card reference
  checksPerformed.push("card_reference");
  if (trace.card_id !== cardId) {
    violations.push(
      createViolation(
        "card_mismatch",
        `Trace references card '${trace.card_id}' but verified against '${cardId}'`
      )
    );
  }

  // Check card expiration
  checksPerformed.push("card_expiration");
  if (card.expires_at) {
    try {
      const expiry = new Date(card.expires_at);
      if (new Date() > expiry) {
        violations.push(
          createViolation("card_expired", `Alignment Card expired at ${card.expires_at}`)
        );
      }
    } catch {
      warnings.push({
        type: "invalid_expiry",
        description: `Could not parse expires_at: ${card.expires_at}`,
        trace_field: "card.expires_at",
      });
    }
  }

  // Extract envelope for remaining checks
  const envelope = card.autonomy_envelope;
  const action = trace.action;

  // Check autonomy compliance
  checksPerformed.push("autonomy");
  const actionCategory = action.category;
  const actionName = action.name;

  if (actionCategory === "bounded") {
    const boundedActions = envelope.bounded_actions ?? [];
    if (actionName && !actionMatchesList(actionName, boundedActions)) {
      violations.push(
        createViolation(
          "unbounded_action",
          `Action '${actionName}' not in bounded_actions: ${JSON.stringify(boundedActions)}`,
          "action.name"
        )
      );
    }
  }

  // Check forbidden actions
  checksPerformed.push("forbidden");
  const forbiddenActions = envelope.forbidden_actions ?? [];
  if (actionName && actionMatchesList(actionName, forbiddenActions)) {
    violations.push(
      createViolation(
        "forbidden_action",
        `Action '${actionName}' is in forbidden_actions`,
        "action.name"
      )
    );
  }

  // Check escalation compliance
  checksPerformed.push("escalation");
  const escalation = trace.escalation;
  for (const trigger of envelope.escalation_triggers ?? []) {
    const condition = trigger.condition ?? "";
    if (evaluateCondition(condition, trace)) {
      if (!escalation?.required) {
        violations.push(
          createViolation(
            "missed_escalation",
            `Trigger '${condition}' matched but escalation not required`,
            "escalation.required"
          )
        );
      } else if (escalation.escalation_status === "timeout") {
        // Timeout is not a violation if escalation was attempted
        warnings.push({
          type: "escalation_timeout",
          description: `Escalation for trigger '${condition}' timed out`,
          trace_field: "escalation.escalation_status",
        });
      }
    }
  }

  // Check value consistency
  checksPerformed.push("values");
  const decision = trace.decision;
  const declaredValues = card.values.declared ?? [];
  const valuesApplied = decision.values_applied ?? [];

  for (const value of valuesApplied) {
    if (!declaredValues.includes(value)) {
      violations.push(
        createViolation(
          "undeclared_value",
          `Value '${value}' applied but not in declared values: ${JSON.stringify(declaredValues)}`,
          "decision.values_applied"
        )
      );
    }
  }

  // Near-boundary warnings
  const confidence = decision.confidence;
  if (confidence != null && confidence < NEAR_BOUNDARY_THRESHOLD) {
    warnings.push({
      type: "near_boundary",
      description: `Decision confidence ${confidence.toFixed(2)} below threshold ${NEAR_BOUNDARY_THRESHOLD}`,
      trace_field: "decision.confidence",
    });
  }

  // Alternatives near boundary check
  for (let i = 0; i < decision.alternatives_considered.length; i++) {
    const alt = decision.alternatives_considered[i];
    const score = alt.score;
    if (score != null && score < NEAR_BOUNDARY_THRESHOLD) {
      warnings.push({
        type: "near_boundary",
        description: `Alternative '${alt.option_id}' score ${score.toFixed(2)} near boundary`,
        trace_field: `decision.alternatives_considered[${i}].score`,
      });
    }
  }

  const durationMs = performance.now() - startTime;

  return {
    verified: violations.length === 0,
    trace_id: traceId,
    card_id: cardId,
    timestamp: new Date().toISOString(),
    violations,
    warnings,
    verification_metadata: {
      algorithm_version: ALGORITHM_VERSION,
      checks_performed: checksPerformed,
      duration_ms: Math.round(durationMs * 100) / 100,
    },
  };
}

/**
 * Check value coherence between two Alignment Cards.
 *
 * Computes coherence score as specified in SPEC Section 6.4:
 *     score = (matched / required) * (1 - conflict_penalty)
 * where conflict_penalty = 0.5 * (conflicts / required)
 *
 * @param myCard - Initiator's Alignment Card
 * @param theirCard - Responder's Alignment Card
 * @param taskValues - Optional list of values required for the task
 * @returns CoherenceResult with compatibility assessment
 */
export function checkCoherence(
  myCard: AlignmentCard,
  theirCard: AlignmentCard,
  taskValues?: string[]
): CoherenceResult {
  const myValues = new Set(myCard.values.declared ?? []);
  const theirValues = new Set(theirCard.values.declared ?? []);

  const myConflicts = new Set(myCard.values.conflicts_with ?? []);
  const theirConflicts = new Set(theirCard.values.conflicts_with ?? []);

  // Determine required values for scoring
  const requiredValues = taskValues
    ? new Set(taskValues)
    : new Set([...myValues, ...theirValues]);

  // Compute matches and conflicts
  const matched: string[] = [];
  const unmatched: string[] = [];

  for (const value of myValues) {
    if (theirValues.has(value)) {
      matched.push(value);
    } else {
      unmatched.push(value);
    }
  }
  for (const value of theirValues) {
    if (!myValues.has(value)) {
      unmatched.push(value);
    }
  }

  const conflicts: ValueConflictResult[] = [];

  // Check for direct conflicts (value in one card's conflicts_with)
  for (const value of myValues) {
    if (theirConflicts.has(value)) {
      conflicts.push({
        initiator_value: value,
        responder_value: "(conflicts_with)",
        conflict_type: "incompatible",
        description: `Initiator's '${value}' is in responder's conflicts_with`,
      });
    }
  }

  for (const value of theirValues) {
    if (myConflicts.has(value)) {
      conflicts.push({
        initiator_value: "(conflicts_with)",
        responder_value: value,
        conflict_type: "incompatible",
        description: `Responder's '${value}' is in initiator's conflicts_with`,
      });
    }
  }

  // Compute coherence score
  const totalRequired = requiredValues.size || 1; // Avoid division by zero
  const matchedCount = taskValues
    ? matched.filter((v) => requiredValues.has(v)).length
    : matched.length;
  const conflictPenalty = CONFLICT_PENALTY_MULTIPLIER * (conflicts.length / totalRequired);

  let score = (matchedCount / totalRequired) * (1 - conflictPenalty);
  score = Math.max(0, Math.min(1, score)); // Clamp to [0, 1]

  // Determine compatibility
  const compatible = conflicts.length === 0 && score >= MIN_COHERENCE_FOR_PROCEED;
  const proceed = compatible;

  // Build proposed resolution if conflicts exist
  let proposedResolution: { type: string; reason: string } | null = null;
  if (conflicts.length > 0 && !compatible) {
    proposedResolution = {
      type: "escalate_to_principals",
      reason: "Value conflict requires human decision",
    };
  }

  return {
    compatible,
    score: Math.round(score * 10000) / 10000,
    value_alignment: {
      matched,
      unmatched,
      conflicts,
    },
    proceed,
    conditions: [],
    proposed_resolution: proposedResolution,
  };
}

/**
 * Detect behavioral drift from declared alignment.
 *
 * Computes a baseline centroid from the first N traces, then compares
 * subsequent traces against this centroid using cosine similarity.
 * Trace-to-trace comparison provides symmetric feature spaces, yielding
 * meaningful similarity scores (unlike trace-to-card which is structurally
 * depressed due to asymmetric features).
 *
 * Alerts when sustained low similarity is detected (consecutive traces
 * below threshold).
 *
 * @see SPEC Section 8 and Appendix B.2 for algorithm specification.
 *
 * @param card - Alignment Card (used for card_id and direction inference)
 * @param traces - List of AP-Traces (sorted chronologically internally)
 * @param similarityThreshold - Alert when similarity drops below (default: 0.30)
 * @param sustainedThreshold - Alert after N consecutive low-similarity traces (default: 3)
 * @returns List of DriftAlert objects for detected drift events
 */
export function detectDrift(
  card: AlignmentCard,
  traces: APTrace[],
  similarityThreshold = DEFAULT_SIMILARITY_THRESHOLD,
  sustainedThreshold = DEFAULT_SUSTAINED_TURNS_THRESHOLD
): DriftAlert[] {
  // Sort traces chronologically
  const sorted = [...traces].sort(
    (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
  );

  // Compute baseline window size
  const baselineSize = Math.max(
    sustainedThreshold,
    Math.min(10, Math.floor(sorted.length / 4))
  );

  // Need enough traces for baseline + sustained threshold
  if (sorted.length < baselineSize + sustainedThreshold) {
    return [];
  }

  // Extract features for baseline traces and compute centroid
  const baselineFeatures = sorted
    .slice(0, baselineSize)
    .map((t) => extractTraceFeatures(t));
  const baselineCentroid = computeCentroid(baselineFeatures);

  const alerts: DriftAlert[] = [];
  let lowSimilarityStreak: Array<{ trace: APTrace; similarity: number }> = [];

  // Track metrics for drift direction inference
  const escalationRates: number[] = [];
  const valueUsage: Record<string, number> = {};

  // Include baseline traces in escalation/value tracking
  for (const trace of sorted.slice(0, baselineSize)) {
    const escalation = trace.escalation;
    escalationRates.push(escalation?.required ? 1.0 : 0.0);
    for (const value of trace.decision.values_applied ?? []) {
      valueUsage[value] = (valueUsage[value] ?? 0) + 1;
    }
  }

  // Iterate from after baseline to end
  for (let i = baselineSize; i < sorted.length; i++) {
    const trace = sorted[i];
    const traceFeatures = extractTraceFeatures(trace);
    const similarity = cosineSimilarity(traceFeatures, baselineCentroid);

    // Track escalation rate
    const escalation = trace.escalation;
    escalationRates.push(escalation?.required ? 1.0 : 0.0);

    // Track value usage
    for (const value of trace.decision.values_applied ?? []) {
      valueUsage[value] = (valueUsage[value] ?? 0) + 1;
    }

    if (similarity < similarityThreshold) {
      lowSimilarityStreak.push({ trace, similarity });
    } else {
      // Reset streak on recovery
      lowSimilarityStreak = [];
    }

    // Check if we've hit the threshold for alerting (== not >= to fire once)
    if (lowSimilarityStreak.length === sustainedThreshold) {
      const latest = lowSimilarityStreak[lowSimilarityStreak.length - 1];

      // Infer drift direction
      const direction = inferDriftDirection(
        lowSimilarityStreak,
        card,
        escalationRates,
        valueUsage
      );

      // Build specific indicators
      const indicators = buildDriftIndicators(
        lowSimilarityStreak,
        escalationRates
      );

      const alert: DriftAlert = {
        alert_type: "drift_detected",
        agent_id: latest.trace.agent_id ?? "",
        card_id: card.card_id ?? "",
        detection_timestamp: new Date().toISOString(),
        analysis: {
          similarity_score: Math.round(latest.similarity * 10000) / 10000,
          sustained_traces: lowSimilarityStreak.length,
          threshold: similarityThreshold,
          drift_direction: direction,
          specific_indicators: indicators,
        },
        recommendation: "Review recent decisions for alignment drift",
        trace_ids: lowSimilarityStreak.map((s) => s.trace.trace_id ?? ""),
      };
      alerts.push(alert);
    }
  }

  return alerts;
}

/**
 * Evaluate a condition expression against trace context.
 *
 * Supports a minimal expression language per SPEC Section 4.6.
 * This is a simplified implementation for common patterns.
 */
function evaluateCondition(condition: string, trace: APTrace): boolean {
  if (!condition) {
    return false;
  }

  // Handle action_type == "value"
  const actionTypeMatch = condition.match(/action_type\s*==\s*"([^"]+)"/);
  if (actionTypeMatch) {
    const expected = actionTypeMatch[1];
    const actual = trace.action.type ?? "";
    return actual === expected;
  }

  // Handle field > value (numeric comparison)
  const numericMatch = condition.match(/(\w+)\s*([><=!]+)\s*(\d+(?:\.\d+)?)/);
  if (numericMatch) {
    const [, field, op, valueStr] = numericMatch;
    const value = parseFloat(valueStr);

    // Look for field in trace context (aligned with Python: check context directly first)
    let actual: unknown = (trace.context as Record<string, unknown> | null)?.[field];
    if (actual == null) {
      actual = trace.context?.metadata?.[field];
    }
    if (actual == null) {
      actual = trace.action.parameters?.[field];
    }
    if (actual == null) {
      return false;
    }

    const actualNum = parseFloat(String(actual));
    if (isNaN(actualNum)) {
      return false;
    }

    switch (op) {
      case ">":
        return actualNum > value;
      case "<":
        return actualNum < value;
      case ">=":
        return actualNum >= value;
      case "<=":
        return actualNum <= value;
      case "==":
        return actualNum === value;
      case "!=":
        return actualNum !== value;
      default:
        return false;
    }
  }

  // Handle boolean fields (aligned with Python: check context directly first)
  if (/^\w+$/.test(condition)) {
    const ctxValue = (trace.context as Record<string, unknown> | null)?.[condition];
    return Boolean(ctxValue ?? trace.context?.metadata?.[condition]);
  }

  return false;
}

/**
 * Infer the direction of behavioral drift.
 */
function inferDriftDirection(
  streak: Array<{ trace: APTrace; similarity: number }>,
  card: AlignmentCard,
  escalationRates: number[],
  valueUsage: Record<string, number>
): DriftDirection {
  const declaredValues = new Set(card.values.declared ?? []);

  // Check for autonomy expansion (decreased escalation rate)
  if (escalationRates.length >= 6) {
    const earlyRate = escalationRates.slice(0, 3).reduce((a, b) => a + b, 0) / 3;
    const lateRate = escalationRates.slice(-3).reduce((a, b) => a + b, 0) / 3;
    if (earlyRate > 0.1 && lateRate < earlyRate * 0.5) {
      return "autonomy_expansion";
    }
  }

  // Check for value drift (using undeclared values)
  let undeclaredUsage = 0;
  let totalUsage = 0;
  for (const [value, count] of Object.entries(valueUsage)) {
    totalUsage += count;
    if (!declaredValues.has(value)) {
      undeclaredUsage += count;
    }
  }
  if (totalUsage > 0 && undeclaredUsage / totalUsage > 0.3) {
    return "value_drift";
  }

  // Check for principal misalignment
  if (declaredValues.has("principal_benefit")) {
    const recentConfidences = streak.slice(-3).map(
      (s) => s.trace.decision.confidence ?? 1.0
    );
    const avgConfidence = recentConfidences.reduce((a, b) => a + b, 0) / recentConfidences.length;
    if (avgConfidence < 0.5) {
      return "principal_misalignment";
    }
  }

  return "unknown";
}

/**
 * Build specific indicators explaining the detected drift.
 */
function buildDriftIndicators(
  streak: Array<{ trace: APTrace; similarity: number }>,
  escalationRates: number[]
): DriftIndicator[] {
  const indicators: DriftIndicator[] = [];

  // Escalation rate indicator
  if (escalationRates.length >= 6) {
    const baselineRate = escalationRates.slice(0, 3).reduce((a, b) => a + b, 0) / 3;
    const currentRate = escalationRates.slice(-3).reduce((a, b) => a + b, 0) / 3;
    if (Math.abs(baselineRate - currentRate) > 0.05) {
      indicators.push({
        indicator: "escalation_rate_change",
        baseline: Math.round(baselineRate * 100) / 100,
        current: Math.round(currentRate * 100) / 100,
        description: `Escalation rate changed from ${(baselineRate * 100).toFixed(0)}% to ${(currentRate * 100).toFixed(0)}%`,
      });
    }
  }

  // Similarity trend indicator
  const similarities = streak.map((s) => s.similarity);
  if (similarities.length >= 3) {
    const trend = similarities[similarities.length - 1] - similarities[0];
    indicators.push({
      indicator: "similarity_trend",
      baseline: Math.round(similarities[0] * 10000) / 10000,
      current: Math.round(similarities[similarities.length - 1] * 10000) / 10000,
      description: `Similarity ${trend < 0 ? "decreasing" : "stable"} over ${streak.length} traces`,
    });
  }

  return indicators;
}
