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
  BEHAVIORAL_SIMILARITY_THRESHOLD,
  CONFLICT_PENALTY_MULTIPLIER,
  DEFAULT_SIMILARITY_THRESHOLD,
  DEFAULT_SUSTAINED_CHECKS_THRESHOLD,
  MIN_COHERENCE_FOR_PROCEED,
  NEAR_BOUNDARY_THRESHOLD,
  OUTLIER_STD_DEV_THRESHOLD,
} from "../constants";
import type { AlignmentCard } from "../schemas/alignment-card";
import { appliedValueIds, cardAudit, cardAutonomy, declaredValueIds, isCardExpired } from "../schemas/alignment-card";
import type { APTrace } from "../schemas/ap-trace";
import {
  computeCentroid,
  cosineSimilarity,
  extractCardFeatures,
  extractTraceFeatures,
} from "./features";
import {
  createViolation,
  type AgentCoherenceSummary,
  type CoherenceResult,
  type DriftAlert,
  type DriftDirection,
  type DriftIndicator,
  type FaultLine,
  type FaultLineAlignment,
  type FaultLineAnalysis,
  type FaultLineSummary,
  type FleetCluster,
  type FleetCoherenceResult,
  type FleetOutlier,
  type PairwiseEntry,
  type Severity,
  type ValueConflictResult,
  type ValueDivergence,
  type VerificationResult,
  type Violation,
  type Warning,
} from "./models";

/** Round to 4 decimal places — canonical precision used throughout the verification API. */
function round4(x: number): number {
  return Math.round(x * 10000) / 10000;
}

/** Sentinel used in ValueConflictResult when the conflict source is a conflicts_with entry. */
const CONFLICTS_WITH_SENTINEL = "(conflicts_with)";

/**
 * Check if a (possibly compound) action name matches any entry in a list.
 * Supports exact match, prefix match (before ':'), and compound name splitting.
 */
function actionMatchesList(actionName: string, list: string[]): boolean {
  const components = actionName.includes(", ")
    ? actionName.split(", ")
    : [actionName];

  return components.every((component) => {
    const trimmed = component.trim();
    if (!trimmed) return true;
    return list.some((entry) => {
      if (entry === trimmed) return true;
      const colonIndex = entry.indexOf(":");
      if (colonIndex > 0) {
        const prefix = entry.substring(0, colonIndex).trim();
        if (prefix === trimmed) return true;
      }
      return false;
    });
  });
}

// ============================================================================
// Private check helpers for verifyTrace
// ============================================================================

function checkCardReference(trace: APTrace, cardId: string): Violation[] {
  if (trace.card_id !== cardId) {
    return [
      createViolation(
        "card_mismatch",
        `Trace references card '${trace.card_id}' but verified against '${cardId}'`,
      ),
    ];
  }
  return [];
}

function checkCardExpiration(
  card: AlignmentCard,
): { violations: Violation[]; warnings: Warning[] } {
  if (!card.expires_at) return { violations: [], warnings: [] };
  try {
    if (isCardExpired(card)) {
      return {
        violations: [
          createViolation(
            "card_expired",
            `Alignment Card expired at ${card.expires_at}`,
          ),
        ],
        warnings: [],
      };
    }
    return { violations: [], warnings: [] };
  } catch {
    return {
      violations: [],
      warnings: [
        {
          type: "invalid_expiry",
          description: `Could not parse expires_at: ${card.expires_at}`,
          trace_field: "card.expires_at",
        },
      ],
    };
  }
}

function checkAutonomyCompliance(
  action: APTrace["action"],
  envelope: ReturnType<typeof cardAutonomy>,
): Violation[] {
  if (action.category !== "bounded") return [];
  const boundedActions = envelope.bounded_actions ?? [];
  if (action.name && !actionMatchesList(action.name, boundedActions)) {
    return [
      createViolation(
        "unbounded_action",
        `Action '${action.name}' not in bounded_actions: ${JSON.stringify(boundedActions)}`,
        "action.name",
      ),
    ];
  }
  return [];
}

function checkForbiddenActions(
  action: APTrace["action"],
  envelope: ReturnType<typeof cardAutonomy>,
): Violation[] {
  const forbiddenActions = envelope.forbidden_actions ?? [];
  if (action.name && actionMatchesList(action.name, forbiddenActions)) {
    return [
      createViolation(
        "forbidden_action",
        `Action '${action.name}' is in forbidden_actions`,
        "action.name",
      ),
    ];
  }
  return [];
}

function checkEscalationCompliance(
  trace: APTrace,
  envelope: ReturnType<typeof cardAutonomy>,
): { violations: Violation[]; warnings: Warning[] } {
  const violations: Violation[] = [];
  const warnings: Warning[] = [];
  const escalation = trace.escalation;
  for (const trigger of envelope.escalation_triggers ?? []) {
    const condition = trigger.condition ?? "";
    if (evaluateCondition(condition, trace)) {
      if (!escalation?.required) {
        violations.push(
          createViolation(
            "missed_escalation",
            `Trigger '${condition}' matched but escalation not required`,
            "escalation.required",
          ),
        );
      } else if (escalation.escalation_status === "timeout") {
        warnings.push({
          type: "escalation_timeout",
          description: `Escalation for trigger '${condition}' timed out`,
          trace_field: "escalation.escalation_status",
        });
      }
    }
  }
  return { violations, warnings };
}

function checkValueConsistency(
  card: AlignmentCard,
  decision: APTrace["decision"],
): Violation[] {
  const declaredValueIdList = declaredValueIds(card.values.declared);
  const violations: Violation[] = [];
  for (const value of appliedValueIds(decision.values_applied)) {
    if (!declaredValueIdList.includes(value)) {
      violations.push(
        createViolation(
          "undeclared_value",
          `Value '${value}' applied but not in declared values: ${JSON.stringify(declaredValueIdList)}`,
          "decision.values_applied",
        ),
      );
    }
  }
  return violations;
}

/**
 * Verify a single AP-Trace against an Alignment Card.
 *
 * IMPORTANT: This function provides STRUCTURAL verification only — it checks that
 * a trace conforms to the declarations in an alignment card. It does NOT provide
 * cryptographic integrity verification. Traces are not signed or hash-chained in
 * the current version. A malicious agent can produce structurally valid traces for
 * arbitrary behavior. For integrity guarantees, use AIP (Agent Integrity Protocol)
 * in conjunction with AAP.
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
  card: AlignmentCard,
): VerificationResult {
  const startTime = performance.now();
  const violations: Violation[] = [];
  const warnings: Warning[] = [];
  const checksPerformed: string[] = [];

  // Warn if tamper_evidence is declared but not cryptographically enforced.
  // Reads the unified `audit` (legacy `audit_commitment` fallback) via the
  // shared helper, matching the Python engine's `_card_audit(...)`.
  const tamperEvidence = cardAudit(card)?.tamper_evidence;
  if (tamperEvidence === "signed" || tamperEvidence === "merkle") {
    console.warn(
      `[AAP] Warning: tamper_evidence mode "${tamperEvidence}" is declared but NOT cryptographically enforced in this version.`,
    );
  }

  const traceId = trace.trace_id ?? "";
  const cardId = card.card_id ?? "";
  const envelope = cardAutonomy(card);
  const action = trace.action;
  const decision = trace.decision;

  checksPerformed.push("card_reference");
  violations.push(...checkCardReference(trace, cardId));

  checksPerformed.push("card_expiration");
  const expiryResult = checkCardExpiration(card);
  violations.push(...expiryResult.violations);
  warnings.push(...expiryResult.warnings);

  checksPerformed.push("autonomy");
  violations.push(...checkAutonomyCompliance(action, envelope));

  checksPerformed.push("forbidden");
  violations.push(...checkForbiddenActions(action, envelope));

  checksPerformed.push("escalation");
  const escalationResult = checkEscalationCompliance(trace, envelope);
  violations.push(...escalationResult.violations);
  warnings.push(...escalationResult.warnings);

  checksPerformed.push("values");
  violations.push(...checkValueConsistency(card, decision));

  // Near-boundary confidence warnings
  const confidence = decision.confidence;
  if (confidence != null && confidence < NEAR_BOUNDARY_THRESHOLD) {
    warnings.push({
      type: "near_boundary",
      description: `Decision confidence ${confidence.toFixed(2)} below threshold ${NEAR_BOUNDARY_THRESHOLD}`,
      trace_field: "decision.confidence",
    });
  }
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

  // Compute behavioral similarity using feature cosine similarity (trace vs card)
  checksPerformed.push("behavioral_similarity");
  const similarityScore = round4(
    cosineSimilarity(extractTraceFeatures(trace), extractCardFeatures(card)),
  );

  const similarityDetails: Record<string, unknown> = {
    similarity_score: similarityScore,
    method: "cosine",
    algorithm_version: ALGORITHM_VERSION,
  };

  // Warn if structurally valid but behaviorally divergent
  if (violations.length === 0 && similarityScore < BEHAVIORAL_SIMILARITY_THRESHOLD) {
    warnings.push({
      type: "low_behavioral_similarity",
      description: `Trace passes structural checks but behavioral similarity (${similarityScore.toFixed(2)}) is below threshold (${BEHAVIORAL_SIMILARITY_THRESHOLD})`,
      trace_field: "(computed)",
    });
  }

  const durationMs = performance.now() - startTime;

  const hasViolations = violations.length > 0;
  const hasWarnings = warnings.length > 0;

  return {
    verified: !hasViolations,
    recommended_action: hasViolations
      ? "deny"
      : hasWarnings
        ? "review"
        : "proceed",
    trace_id: traceId,
    card_id: cardId,
    timestamp: new Date().toISOString(),
    violations,
    warnings,
    similarity_score: similarityScore,
    verification_metadata: {
      algorithm_version: ALGORITHM_VERSION,
      checks_performed: checksPerformed,
      duration_ms: Math.round(durationMs * 100) / 100,
      similarity_details: similarityDetails,
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
  taskValues?: string[],
): CoherenceResult {
  const myValues = new Set(declaredValueIds(myCard.values.declared));
  const theirValues = new Set(declaredValueIds(theirCard.values.declared));

  const myConflicts = new Set(myCard.values.conflicts_with ?? []);
  const theirConflicts = new Set(theirCard.values.conflicts_with ?? []);

  // Determine required values for scoring
  const requiredValues = taskValues
    ? new Set(taskValues)
    : new Set([...myValues, ...theirValues]);

  // Compute matches and unmatched declaratively
  const matched = [...myValues].filter((v) => theirValues.has(v));
  const unmatched = [
    ...[...myValues].filter((v) => !theirValues.has(v)),
    ...[...theirValues].filter((v) => !myValues.has(v)),
  ];

  const conflicts: ValueConflictResult[] = [];

  // Check for direct conflicts (value in one card's conflicts_with)
  for (const value of myValues) {
    if (theirConflicts.has(value)) {
      conflicts.push({
        initiator_value: value,
        responder_value: CONFLICTS_WITH_SENTINEL,
        conflict_type: "incompatible",
        description: `Initiator's '${value}' is in responder's conflicts_with`,
      });
    }
  }

  for (const value of theirValues) {
    if (myConflicts.has(value)) {
      conflicts.push({
        initiator_value: CONFLICTS_WITH_SENTINEL,
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
  const conflictPenalty = Math.min(
    1,
    CONFLICT_PENALTY_MULTIPLIER * (conflicts.length / totalRequired),
  );

  let score = (matchedCount / totalRequired) * (1 - conflictPenalty);
  score = Math.max(0, Math.min(1, score)); // Clamp to [0, 1]

  // Determine compatibility
  const compatible =
    conflicts.length === 0 && score >= MIN_COHERENCE_FOR_PROCEED;
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
    score: round4(score),
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
 * Check fleet-level value coherence across N agents.
 *
 * Computes all C(n,2) pairwise coherence scores, then derives:
 * - Fleet score: mean of all pairwise scores
 * - Outlier detection: agents >1 std dev below fleet mean
 * - Cluster analysis: connected components at compatibility threshold
 * - Divergence report: values where agents disagree
 *
 * @param cards - Array of agent cards with their IDs
 * @param taskValues - Optional list of values required for the task
 * @returns FleetCoherenceResult with full analysis
 * @throws Error if fewer than 2 agents provided
 */
export function checkFleetCoherence(
  cards: Array<{ agentId: string; card: AlignmentCard }>,
  taskValues?: string[],
): FleetCoherenceResult {
  if (cards.length < 2) {
    throw new Error("Fleet coherence requires at least 2 agents");
  }

  // Step 1: Compute all pairwise coherence scores
  const pairwiseMatrix: PairwiseEntry[] = [];
  for (let i = 0; i < cards.length; i++) {
    for (let j = i + 1; j < cards.length; j++) {
      pairwiseMatrix.push({
        agent_a: cards[i].agentId,
        agent_b: cards[j].agentId,
        result: checkCoherence(cards[i].card, cards[j].card, taskValues),
      });
    }
  }

  // Step 2: Fleet score (mean of all pairwise scores) + min/max
  const allScores = pairwiseMatrix.map((p) => p.result.score);
  const fleetScore = allScores.reduce((a, b) => a + b, 0) / allScores.length;
  const minPairScore = Math.min(...allScores);
  const maxPairScore = Math.max(...allScores);

  // Step 3: Per-agent summaries
  const agentIds = cards.map((c) => c.agentId);
  const agentScoreMap = new Map<string, number[]>();
  const agentCompatibleCount = new Map<string, number>();
  const agentConflictCount = new Map<string, number>();

  for (const id of agentIds) {
    agentScoreMap.set(id, []);
    agentCompatibleCount.set(id, 0);
    agentConflictCount.set(id, 0);
  }

  for (const pair of pairwiseMatrix) {
    agentScoreMap.get(pair.agent_a)!.push(pair.result.score);
    agentScoreMap.get(pair.agent_b)!.push(pair.result.score);
    if (pair.result.compatible) {
      agentCompatibleCount.set(
        pair.agent_a,
        agentCompatibleCount.get(pair.agent_a)! + 1,
      );
      agentCompatibleCount.set(
        pair.agent_b,
        agentCompatibleCount.get(pair.agent_b)! + 1,
      );
    }
    if (pair.result.value_alignment.conflicts.length > 0) {
      agentConflictCount.set(
        pair.agent_a,
        agentConflictCount.get(pair.agent_a)! + 1,
      );
      agentConflictCount.set(
        pair.agent_b,
        agentConflictCount.get(pair.agent_b)! + 1,
      );
    }
  }

  const agentMeans = new Map<string, number>();
  for (const id of agentIds) {
    const scores = agentScoreMap.get(id)!;
    agentMeans.set(id, scores.reduce((a, b) => a + b, 0) / scores.length);
  }

  // Step 4: Outlier detection
  const meanValues = [...agentMeans.values()];
  const fleetMeanOfMeans =
    meanValues.reduce((a, b) => a + b, 0) / meanValues.length;
  const variance =
    meanValues.reduce((sum, v) => sum + (v - fleetMeanOfMeans) ** 2, 0) /
    meanValues.length;
  const stddev = Math.sqrt(variance);

  const outliers: FleetOutlier[] = [];
  // Only detect outliers when there's meaningful variance (3+ agents)
  if (stddev > 0 && agentIds.length >= 3) {
    for (const id of agentIds) {
      const agentMean = agentMeans.get(id)!;
      const deviation = (fleetMeanOfMeans - agentMean) / stddev;
      if (deviation >= OUTLIER_STD_DEV_THRESHOLD) {
        // Identify primary conflict values
        const primaryConflicts = new Set<string>();
        for (const pair of pairwiseMatrix) {
          if (pair.agent_a === id || pair.agent_b === id) {
            for (const conflict of pair.result.value_alignment.conflicts) {
              if (conflict.initiator_value !== CONFLICTS_WITH_SENTINEL) {
                primaryConflicts.add(conflict.initiator_value);
              }
              if (conflict.responder_value !== CONFLICTS_WITH_SENTINEL) {
                primaryConflicts.add(conflict.responder_value);
              }
            }
          }
        }
        outliers.push({
          agent_id: id,
          agent_mean_score: round4(agentMean),
          fleet_mean_score: round4(fleetMeanOfMeans),
          deviation: round4(deviation),
          primary_conflicts: [...primaryConflicts],
        });
      }
    }
  }

  // Step 5: Cluster analysis (connected components at compatibility threshold)
  const adjacency = new Map<string, Set<string>>();
  for (const id of agentIds) {
    adjacency.set(id, new Set());
  }
  for (const pair of pairwiseMatrix) {
    if (pair.result.compatible) {
      adjacency.get(pair.agent_a)!.add(pair.agent_b);
      adjacency.get(pair.agent_b)!.add(pair.agent_a);
    }
  }

  const visited = new Set<string>();
  const clusters: FleetCluster[] = [];
  let clusterId = 0;

  for (const id of agentIds) {
    if (visited.has(id)) continue;
    // BFS to find connected component
    const component: string[] = [];
    const queue = [id];
    visited.add(id);
    while (queue.length > 0) {
      const current = queue.shift()!;
      component.push(current);
      for (const neighbor of adjacency.get(current)!) {
        if (!visited.has(neighbor)) {
          visited.add(neighbor);
          queue.push(neighbor);
        }
      }
    }

    // Compute internal coherence for this cluster
    let internalSum = 0;
    let internalCount = 0;
    for (let i = 0; i < component.length; i++) {
      for (let j = i + 1; j < component.length; j++) {
        const pair = pairwiseMatrix.find(
          (p) =>
            (p.agent_a === component[i] && p.agent_b === component[j]) ||
            (p.agent_a === component[j] && p.agent_b === component[i]),
        );
        if (pair) {
          internalSum += pair.result.score;
          internalCount++;
        }
      }
    }
    const internalCoherence =
      internalCount > 0 ? internalSum / internalCount : 1;

    // Find shared values (intersection of all agents in cluster)
    const clusterCards = component.map(
      (cid) => cards.find((c) => c.agentId === cid)!,
    );
    const sharedValues = clusterCards.reduce<string[]>((shared, entry, idx) => {
      const declared = declaredValueIds(entry.card.values.declared);
      if (idx === 0) return [...declared];
      return shared.filter((v) => declared.includes(v));
    }, []);

    // Find distinguishing values (values in this cluster but not in other clusters' shared values)
    const allOtherValues = new Set<string>();
    for (const entry of cards) {
      if (!component.includes(entry.agentId)) {
        for (const v of declaredValueIds(entry.card.values.declared)) {
          allOtherValues.add(v);
        }
      }
    }
    const distinguishingValues = sharedValues.filter(
      (v) => !allOtherValues.has(v),
    );

    clusters.push({
      cluster_id: clusterId++,
      agent_ids: component,
      internal_coherence: round4(internalCoherence),
      shared_values: sharedValues,
      distinguishing_values: distinguishingValues,
    });
  }

  // Step 6: Divergence report
  const allValues = new Set<string>();
  const agentValueMap = new Map<string, Set<string>>();
  const agentConflictMap = new Map<string, Set<string>>();

  for (const entry of cards) {
    const declared = new Set(declaredValueIds(entry.card.values.declared));
    const conflicts = new Set(entry.card.values.conflicts_with ?? []);
    agentValueMap.set(entry.agentId, declared);
    agentConflictMap.set(entry.agentId, conflicts);
    for (const v of declared) allValues.add(v);
  }

  const divergenceReport: ValueDivergence[] = [];
  for (const value of allValues) {
    const declaring = agentIds.filter((id) =>
      agentValueMap.get(id)!.has(value),
    );
    const missing = agentIds.filter((id) => !agentValueMap.get(id)!.has(value));
    const conflicting = agentIds.filter((id) =>
      agentConflictMap.get(id)!.has(value),
    );

    // Skip values with no divergence (everyone declares, no one conflicts)
    if (missing.length === 0 && conflicting.length === 0) continue;

    // Estimate impact: fraction of agents not aligned on this value
    const impactOnFleetScore = round4(
      (missing.length + conflicting.length) / agentIds.length,
    );

    divergenceReport.push({
      value,
      agents_declaring: declaring,
      agents_missing: missing,
      agents_conflicting: conflicting,
      impact_on_fleet_score: impactOnFleetScore,
    });
  }

  // Sort divergence report by impact (highest first)
  divergenceReport.sort(
    (a, b) => b.impact_on_fleet_score - a.impact_on_fleet_score,
  );

  // Build agent cluster map for summaries
  const agentClusterMap = new Map<string, number>();
  for (const cluster of clusters) {
    for (const id of cluster.agent_ids) {
      agentClusterMap.set(id, cluster.cluster_id);
    }
  }

  const outlierIds = new Set(outliers.map((o) => o.agent_id));

  const agentSummaries: AgentCoherenceSummary[] = agentIds.map((id) => ({
    agent_id: id,
    mean_score: round4(agentMeans.get(id)!),
    compatible_count: agentCompatibleCount.get(id)!,
    conflict_count: agentConflictCount.get(id)!,
    cluster_id: agentClusterMap.get(id) ?? 0,
    is_outlier: outlierIds.has(id),
  }));

  return {
    fleet_score: round4(fleetScore),
    min_pair_score: round4(minPairScore),
    max_pair_score: round4(maxPairScore),
    agent_count: cards.length,
    pair_count: pairwiseMatrix.length,
    pairwise_matrix: pairwiseMatrix,
    outliers,
    clusters,
    divergence_report: divergenceReport,
    agent_summaries: agentSummaries,
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
  sustainedThreshold = DEFAULT_SUSTAINED_CHECKS_THRESHOLD,
): DriftAlert[] {
  // Sort traces chronologically
  const sorted = [...traces].sort(
    (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
  );

  // Compute baseline window size
  const baselineSize = Math.max(
    sustainedThreshold,
    Math.min(10, Math.floor(sorted.length / 4)),
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
    accumulateTraceMetrics(trace, escalationRates, valueUsage);
  }

  // Iterate from after baseline to end
  for (let i = baselineSize; i < sorted.length; i++) {
    const trace = sorted[i];
    const traceFeatures = extractTraceFeatures(trace);
    const similarity = cosineSimilarity(traceFeatures, baselineCentroid);

    accumulateTraceMetrics(trace, escalationRates, valueUsage);

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
        valueUsage,
      );

      // Build specific indicators
      const indicators = buildDriftIndicators(
        lowSimilarityStreak,
        escalationRates,
      );

      const alert: DriftAlert = {
        alert_type: "drift_detected",
        agent_id: latest.trace.agent_id ?? "",
        card_id: card.card_id ?? "",
        detection_timestamp: new Date().toISOString(),
        analysis: {
          similarity_score: round4(latest.similarity),
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

// ============================================================================
// Fault Line Analysis (E-06)
// ============================================================================

/**
 * Produce a deterministic hex string from an arbitrary input.
 * Used for stable, reproducible IDs.
 */
function deterministicHex(input: string, length: number): string {
  let hash = 0;
  for (let i = 0; i < input.length; i++) {
    const char = input.charCodeAt(i);
    hash = (hash << 5) - hash + char;
    hash = hash & hash;
  }
  return Math.abs(hash).toString(16).padStart(length, "0").slice(0, length);
}

/** Compute Jaccard similarity of two string sets: |A ∩ B| / |A ∪ B|. */
function jaccardSimilarity(a: string[], b: string[]): number {
  const setA = new Set(a);
  const setB = new Set(b);
  const intersection = [...setA].filter((x) => setB.has(x)).length;
  const union = new Set([...setA, ...setB]).size;
  return union === 0 ? 0 : intersection / union;
}

/** Role keywords that indicate agent specialization for complementary detection. */
const ROLE_KEYWORDS = [
  "safety",
  "executive",
  "cfo",
  "analyst",
  "compliance",
  "legal",
  "risk",
  "finance",
  "security",
  "ethics",
  "audit",
  "ops",
  "operations",
];

function hasRoleKeyword(agentId: string): boolean {
  const lower = agentId.toLowerCase();
  return ROLE_KEYWORDS.some((kw) => lower.includes(kw));
}

/** Extract the CLPI role from a card's extensions, if present. */
function getClpiRole(card: AlignmentCard): string | null {
  const ext = (card as unknown as { extensions?: Record<string, unknown> })
    .extensions;
  if (!ext) return null;
  const clpi = ext["clpi"] as Record<string, unknown> | undefined;
  if (!clpi || typeof clpi["role"] !== "string") return null;
  return clpi["role"] || null;
}

/**
 * Analyze fault lines in a fleet based on a FleetCoherenceResult.
 *
 * @param coherenceResult - Result from checkFleetCoherence
 * @param cards - Same agent cards passed to checkFleetCoherence
 * @param options - Optional reputationScores and taskContext
 * @returns FaultLineAnalysis with fault lines and alignment patterns
 */
export function analyzeFaultLines(
  coherenceResult: FleetCoherenceResult,
  cards: Array<{ agentId: string; card: AlignmentCard }>,
  options?: { reputationScores?: Record<string, number>; taskContext?: string },
): FaultLineAnalysis {
  const reputationScores = options?.reputationScores;

  // Build a lookup: agentId → bounded_actions
  const agentBoundedActions = new Map<string, string[]>();
  for (const { agentId, card } of cards) {
    agentBoundedActions.set(
      agentId,
      cardAutonomy(card).bounded_actions ?? [],
    );
  }

  // Build lookup for conflicts_with per agent (already in divergence report, but keep for classification)
  const agentConflictMap = new Map<string, Set<string>>();
  for (const { agentId, card } of cards) {
    agentConflictMap.set(agentId, new Set(card.values.conflicts_with ?? []));
  }

  // Build lookup: agentId → CLPI role (from extensions.clpi.role)
  const agentRoleMap = new Map<string, string | null>();
  for (const { agentId, card } of cards) {
    agentRoleMap.set(agentId, getClpiRole(card));
  }

  const faultLines: FaultLine[] = [];

  for (const divergence of coherenceResult.divergence_report) {
    const {
      value,
      agents_declaring,
      agents_missing,
      agents_conflicting,
      impact_on_fleet_score,
    } = divergence;

    // All agents involved in this fault line
    const involvedAgents = [
      ...new Set([
        ...agents_declaring,
        ...agents_missing,
        ...agents_conflicting,
      ]),
    ];

    // --- Classification ---
    let classification: FaultLine["classification"];

    // incompatible: any agent has an explicit conflicts_with for this value
    if (agents_conflicting.length > 0) {
      classification = "incompatible";
    } else if (
      agents_declaring.length >= 2 &&
      (() => {
        // priority_mismatch: two declaring agents have a pairwise score < 0.5
        for (let i = 0; i < agents_declaring.length; i++) {
          for (let j = i + 1; j < agents_declaring.length; j++) {
            const idA = agents_declaring[i];
            const idB = agents_declaring[j];
            const entry = coherenceResult.pairwise_matrix.find(
              (p) =>
                (p.agent_a === idA && p.agent_b === idB) ||
                (p.agent_a === idB && p.agent_b === idA),
            );
            if (entry && entry.result.score < 0.5) {
              return true;
            }
          }
        }
        return false;
      })()
    ) {
      classification = "priority_mismatch";
    } else if (
      agents_declaring.length >= 1 &&
      agents_missing.length >= 1 &&
      (() => {
        // complementary: the declaring agents all share a CLPI role that the missing
        // agents do NOT share — indicating intentional role specialization, not a gap.
        // Primary check: extensions.clpi.role (authoritative)
        const declaringRoles = new Set(
          agents_declaring
            .map((id) => agentRoleMap.get(id) ?? null)
            .filter(Boolean),
        );
        const missingRoles = new Set(
          agents_missing
            .map((id) => agentRoleMap.get(id) ?? null)
            .filter(Boolean),
        );
        if (declaringRoles.size > 0) {
          // All declaring agents share a role that none of the missing agents have
          const declaringRoleArr = [...declaringRoles];
          const isRoleExclusive = declaringRoleArr.every(
            (role) => !missingRoles.has(role),
          );
          if (isRoleExclusive) return true;
        }
        // Fallback: agent ID contains a role keyword (original heuristic)
        const allInvolved = [...agents_declaring, ...agents_missing];
        return allInvolved.some((id) => hasRoleKeyword(id));
      })()
    ) {
      classification = "complementary";
    } else {
      classification = "resolvable";
    }

    // --- Coordination overlap (Jaccard of bounded_actions across all involved agents) ---
    let coordinationOverlap: number;
    if (involvedAgents.length < 2) {
      coordinationOverlap = 0.5;
    } else {
      const actionSets = involvedAgents.map(
        (id) => agentBoundedActions.get(id) ?? [],
      );
      const nonEmpty = actionSets.filter((s) => s.length > 0);
      if (nonEmpty.length < 2) {
        coordinationOverlap = 0.5;
      } else {
        // Pairwise mean Jaccard
        let total = 0;
        let count = 0;
        for (let i = 0; i < nonEmpty.length; i++) {
          for (let j = i + 1; j < nonEmpty.length; j++) {
            total += jaccardSimilarity(nonEmpty[i], nonEmpty[j]);
            count++;
          }
        }
        coordinationOverlap = count > 0 ? total / count : 0.5;
      }
    }

    // --- impact_score ---
    // Complementary faults are intentional — they carry zero risk by definition.
    let impactScore: number;
    let severity: Severity;

    if (classification === "complementary") {
      impactScore = 0;
      severity = "low";
    } else {
      impactScore = impact_on_fleet_score * coordinationOverlap;

      // Reputation weighting: multiply by geometric mean of reputation/1000
      if (reputationScores && involvedAgents.length > 0) {
        const repValues = involvedAgents
          .map((id) => (reputationScores[id] ?? 500) / 1000)
          .map((r) => Math.max(0.001, r)); // avoid log(0)
        const logSum = repValues.reduce((sum, r) => sum + Math.log(r), 0);
        const geoMean = Math.exp(logSum / repValues.length);
        impactScore *= geoMean;
      }

      impactScore = Math.min(1, Math.max(0, impactScore));

      // --- Severity ---
      if (impactScore >= 0.7) {
        severity = "critical";
      } else if (impactScore >= 0.4) {
        severity = "high";
      } else if (impactScore >= 0.2) {
        severity = "medium";
      } else {
        severity = "low";
      }
    }

    // --- Resolution hint ---
    let resolutionHint: string;
    switch (classification) {
      case "resolvable":
        resolutionHint = `Add value '${value}' to ${agents_missing.join(", ")} alignment card(s).`;
        break;
      case "priority_mismatch":
        resolutionHint = `Align priority/definition of '${value}' across all declaring agents.`;
        break;
      case "incompatible":
        resolutionHint = `Value '${value}' conflicts with ${agents_conflicting.join(", ")}. Requires human review.`;
        break;
      case "complementary":
        resolutionHint = `Value '${value}' divergence appears intentional given agent specializations.`;
        break;
    }

    // --- affects_capabilities: intersection of bounded_actions across all involved agents ---
    let affectsCapabilities: string[] = [];
    if (involvedAgents.length > 0) {
      const firstActions = agentBoundedActions.get(involvedAgents[0]) ?? [];
      affectsCapabilities = firstActions.filter((action) =>
        involvedAgents.every((id) =>
          (agentBoundedActions.get(id) ?? []).includes(action),
        ),
      );
    }

    // --- deterministic id ---
    const idInput = [value, ...involvedAgents.sort()].join("|");
    const id = deterministicHex(idInput, 12);

    faultLines.push({
      id,
      value,
      classification,
      severity,
      agents_declaring,
      agents_missing,
      agents_conflicting,
      impact_score: round4(impactScore),
      resolution_hint: resolutionHint,
      affects_capabilities: affectsCapabilities,
    });
  }

  // Sort: critical first, then by impact_score descending
  const severityOrder: Record<Severity, number> = {
    critical: 0,
    high: 1,
    medium: 2,
    low: 3,
  };
  faultLines.sort((a, b) => {
    const sev = severityOrder[a.severity] - severityOrder[b.severity];
    if (sev !== 0) return sev;
    return b.impact_score - a.impact_score;
  });

  // --- Fault line alignment detection ---
  // Only consider resolvable and incompatible faults — complementary faults are intentional
  // role specialization and should NEVER trigger a structural fault line alert.
  const alignments: FaultLineAlignment[] = [];
  const actionableFaultLines = faultLines.filter(
    (fl) =>
      fl.classification === "resolvable" ||
      fl.classification === "incompatible",
  );

  // For each pair of actionable fault lines, compute Jaccard of agents_missing sets
  // Group fault lines with similarity > 0.6
  const grouped = new Map<number, number[]>(); // groupId → faultLine indices
  const groupAssignment = new Map<number, number>(); // faultLine index → groupId
  let nextGroupId = 0;

  for (let i = 0; i < actionableFaultLines.length; i++) {
    for (let j = i + 1; j < actionableFaultLines.length; j++) {
      const sim = jaccardSimilarity(
        actionableFaultLines[i].agents_missing,
        actionableFaultLines[j].agents_missing,
      );
      if (sim > 0.6) {
        // Find or create groups for i and j
        const gi = groupAssignment.get(i);
        const gj = groupAssignment.get(j);

        if (gi === undefined && gj === undefined) {
          const gid = nextGroupId++;
          grouped.set(gid, [i, j]);
          groupAssignment.set(i, gid);
          groupAssignment.set(j, gid);
        } else if (gi !== undefined && gj === undefined) {
          grouped.get(gi)!.push(j);
          groupAssignment.set(j, gi);
        } else if (gi === undefined && gj !== undefined) {
          grouped.get(gj)!.push(i);
          groupAssignment.set(i, gj);
        } else if (gi !== gj) {
          // Merge two groups
          const smaller = gi! < gj! ? gj! : gi!;
          const larger = gi! < gj! ? gi! : gj!;
          const smallerMembers = grouped.get(smaller) ?? [];
          const largerMembers = grouped.get(larger) ?? [];
          const merged = [...new Set([...largerMembers, ...smallerMembers])];
          grouped.set(larger, merged);
          grouped.delete(smaller);
          for (const idx of smallerMembers) {
            groupAssignment.set(idx, larger);
          }
        }
      }
    }
  }

  for (const [, members] of grouped) {
    if (members.length < 2) continue;
    const unique = [...new Set(members)];
    const groupFaultLines = unique.map((i) => actionableFaultLines[i]);

    const minorityAgents = [
      ...new Set(groupFaultLines.flatMap((fl) => fl.agents_missing)),
    ];
    const majorityAgents = [
      ...new Set(groupFaultLines.flatMap((fl) => fl.agents_declaring)),
    ];

    // Alignment score: mean pairwise Jaccard of agents_missing within the group
    let jaccardSum = 0;
    let jaccardCount = 0;
    for (let i = 0; i < unique.length; i++) {
      for (let j = i + 1; j < unique.length; j++) {
        jaccardSum += jaccardSimilarity(
          groupFaultLines[i].agents_missing,
          groupFaultLines[j].agents_missing,
        );
        jaccardCount++;
      }
    }
    const alignmentScore = jaccardCount > 0 ? jaccardSum / jaccardCount : 0;

    // Base severity on group size, raised if any fault line is critical/high
    const hasHigherSeverity = groupFaultLines.some(
      (fl) => fl.severity === "critical" || fl.severity === "high",
    );
    let severity: Severity = unique.length >= 3 ? "high" : "medium";
    if (hasHigherSeverity && severity === "medium") {
      severity = "high";
    }

    const sortedFaultLineIds = groupFaultLines.map((fl) => fl.id).sort();
    const alignmentId = deterministicHex(sortedFaultLineIds.join("|"), 12);

    alignments.push({
      id: alignmentId,
      fault_line_ids: sortedFaultLineIds,
      minority_agents: minorityAgents,
      majority_agents: majorityAgents,
      alignment_score: round4(alignmentScore),
      severity,
      description: `${groupFaultLines.length} fault lines consistently isolate ${minorityAgents.join(", ")} from the team`,
    });
  }

  // --- Summary ---
  const summary: FaultLineSummary = {
    total: faultLines.length,
    resolvable: faultLines.filter((fl) => fl.classification === "resolvable")
      .length,
    priority_mismatch: faultLines.filter(
      (fl) => fl.classification === "priority_mismatch",
    ).length,
    incompatible: faultLines.filter(
      (fl) => fl.classification === "incompatible",
    ).length,
    complementary: faultLines.filter(
      (fl) => fl.classification === "complementary",
    ).length,
    critical_count: faultLines.filter((fl) => fl.severity === "critical")
      .length,
  };

  // --- analysis_id: deterministic from fleet_score + sorted fault_line ids ---
  const analysisIdInput = [
    String(coherenceResult.fleet_score),
    ...faultLines.map((fl) => fl.id).sort(),
  ].join("|");
  const analysisId = deterministicHex(analysisIdInput, 16);

  return {
    analysis_id: analysisId,
    fleet_score: coherenceResult.fleet_score,
    fault_lines: faultLines,
    alignments,
    summary,
  };
}

/**
 * Convenience wrapper: run fleet coherence then fault line analysis in one call.
 *
 * @param cards - Array of agent cards
 * @param options - Optional reputationScores and taskContext
 * @returns Both FleetCoherenceResult and FaultLineAnalysis
 */
export function checkFleetFaultLines(
  cards: Array<{ agentId: string; card: AlignmentCard }>,
  options?: { reputationScores?: Record<string, number>; taskContext?: string },
): { coherence: FleetCoherenceResult; analysis: FaultLineAnalysis } {
  const coherence = checkFleetCoherence(cards);
  const analysis = analyzeFaultLines(coherence, cards, options);
  return { coherence, analysis };
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
  // Anchored regex to prevent polynomial backtracking (ReDoS)
  const numericMatch = condition.match(
    /^\s*(\w+)\s*([><=!]+)\s*(\d+(?:\.\d+)?)\s*$/,
  );
  if (numericMatch) {
    const [, field, op, valueStr] = numericMatch;
    const value = parseFloat(valueStr);

    // Look for field in trace context (aligned with Python: check context directly first)
    let actual: unknown = (trace.context as Record<string, unknown> | null)?.[
      field
    ];
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
    const ctxValue = (trace.context as Record<string, unknown> | null)?.[
      condition
    ];
    return Boolean(ctxValue ?? trace.context?.metadata?.[condition]);
  }

  console.warn(
    `[AAP] Condition could not be parsed: "${condition}". Supported patterns: "field == value", "field > number", "field_name" (boolean). This trigger will not fire.`,
  );
  return false;
}

/**
 * Accumulate escalation rate and value usage metrics from a single trace.
 * ADR-065 #16: normalizes applied values to ids — object entries would
 * otherwise key the usage map under '[object Object]'.
 */
function accumulateTraceMetrics(
  trace: APTrace,
  escalationRates: number[],
  valueUsage: Record<string, number>,
): void {
  escalationRates.push(trace.escalation?.required ? 1.0 : 0.0);
  for (const value of appliedValueIds(trace.decision.values_applied)) {
    valueUsage[value] = (valueUsage[value] ?? 0) + 1;
  }
}

/**
 * Infer the direction of behavioral drift.
 */
function inferDriftDirection(
  streak: Array<{ trace: APTrace; similarity: number }>,
  card: AlignmentCard,
  escalationRates: number[],
  valueUsage: Record<string, number>,
): DriftDirection {
  const declaredValues = new Set(declaredValueIds(card.values.declared));

  // Check for autonomy expansion (decreased escalation rate)
  if (escalationRates.length >= 6) {
    const earlyRate =
      escalationRates.slice(0, 3).reduce((a, b) => a + b, 0) / 3;
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
    const recentConfidences = streak
      .slice(-3)
      .map((s) => s.trace.decision.confidence ?? 1.0);
    const avgConfidence =
      recentConfidences.reduce((a, b) => a + b, 0) / recentConfidences.length;
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
  escalationRates: number[],
): DriftIndicator[] {
  const indicators: DriftIndicator[] = [];

  // Escalation rate indicator
  if (escalationRates.length >= 6) {
    const baselineRate =
      escalationRates.slice(0, 3).reduce((a, b) => a + b, 0) / 3;
    const currentRate =
      escalationRates.slice(-3).reduce((a, b) => a + b, 0) / 3;
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
      baseline: round4(similarities[0]),
      current: round4(similarities[similarities.length - 1]),
      description: `Similarity ${trend < 0 ? "decreasing" : "stable"} over ${streak.length} traces`,
    });
  }

  return indicators;
}
