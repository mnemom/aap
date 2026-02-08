/**
 * Feature extraction for AAP verification.
 *
 * Provides feature extraction utilities for computing similarity
 * between AP-Traces and Alignment Cards.
 */

import { MIN_WORD_LENGTH } from "../constants";
import type { AlignmentCard } from "../schemas/alignment-card";
import type { APTrace } from "../schemas/ap-trace";

/** Sparse feature vector represented as a record. */
export type FeatureVector = Record<string, number>;

/** Stopwords to filter from text features. */
const STOPWORDS = new Set([
  "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
  "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
  "being", "have", "has", "had", "do", "does", "did", "will", "would",
  "could", "should", "may", "might", "must", "shall", "can", "this",
  "that", "these", "those", "it", "its", "as", "if", "then", "else",
]);

/**
 * Extract tokens from text, filtering stopwords and short words.
 */
function tokenize(text: string): string[] {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, " ")
    .split(/\s+/)
    .filter((word) => word.length >= MIN_WORD_LENGTH && !STOPWORDS.has(word));
}

/**
 * Extract features from an Alignment Card.
 */
export function extractCardFeatures(card: AlignmentCard): FeatureVector {
  const features: FeatureVector = {};

  // Value features
  for (const value of card.values.declared) {
    features[`value:${value}`] = 1.0;
  }

  // Conflicts features
  for (const conflict of card.values.conflicts_with ?? []) {
    features[`conflict:${conflict}`] = 1.0;
  }

  // Action features (aligned with Python: action_name:{action})
  for (const action of card.autonomy_envelope.bounded_actions) {
    features[`action_name:${action}`] = 1.0;
  }

  // Forbidden action features
  for (const action of card.autonomy_envelope.forbidden_actions ?? []) {
    features[`forbidden:${action}`] = 1.0;
  }

  // Escalation trigger features
  for (const trigger of card.autonomy_envelope.escalation_triggers) {
    features[`escalation:${trigger.action}`] = 1.0;
    const conditionTokens = tokenize(trigger.condition);
    for (const token of conditionTokens) {
      features[`condition:${token}`] = (features[`condition:${token}`] ?? 0) + 0.5;
    }
  }

  // Principal features (matching Python SDK naming)
  features[`principal_type:${card.principal.type}`] = 1.0;
  features[`relationship:${card.principal.relationship}`] = 1.0;

  return features;
}

/**
 * Extract features from an AP-Trace.
 */
export function extractTraceFeatures(trace: APTrace): FeatureVector {
  const features: FeatureVector = {};

  // Action features (aligned with Python: action:{type}, category:{category}, action_name:{name})
  features[`action:${trace.action.type}`] = 1.0;
  features[`category:${trace.action.category}`] = 1.0;
  features[`action_name:${trace.action.name}`] = 1.0;

  // Value features from decision
  for (const value of trace.decision.values_applied) {
    features[`value:${value}`] = 1.0;
  }

  // Escalation features
  if (trace.escalation) {
    features[`escalation:${trace.escalation.required ? "required" : "not_required"}`] = 1.0;
    if (trace.escalation.escalation_status) {
      features[`escalation:${trace.escalation.escalation_status}`] = 1.0;
    }
  }

  // Note: Content features from reasoning/alternatives are deliberately excluded.
  // Card features are purely structural, so content tokens dilute cosine
  // similarity without adding alignment signal. See CALIBRATION.md Section 3.5.

  // Flag features from alternatives (structural, not content)
  for (const alt of trace.decision.alternatives_considered) {
    if (alt.flags) {
      for (const flag of alt.flags) {
        features[`flag:${flag}`] = 1.0;
      }
    }
  }

  return features;
}

/**
 * Compute the centroid (element-wise mean) of multiple feature vectors.
 *
 * Used by drift detection to build a baseline from the first N traces,
 * enabling trace-to-trace comparison instead of trace-to-card comparison.
 *
 * @param vectors - Array of feature vectors to average
 * @returns Centroid feature vector
 */
export function computeCentroid(vectors: FeatureVector[]): FeatureVector {
  if (vectors.length === 0) return {};
  const centroid: FeatureVector = {};
  for (const vec of vectors) {
    for (const [key, value] of Object.entries(vec)) {
      centroid[key] = (centroid[key] ?? 0) + value;
    }
  }
  const n = vectors.length;
  for (const key of Object.keys(centroid)) {
    centroid[key] /= n;
  }
  return centroid;
}

/**
 * Compute cosine similarity between two feature vectors.
 *
 * @returns Similarity score between 0.0 and 1.0
 */
export function cosineSimilarity(a: FeatureVector, b: FeatureVector): number {
  const keysA = Object.keys(a);
  const keysB = new Set(Object.keys(b));

  let dotProduct = 0;
  let normA = 0;
  let normB = 0;

  // Compute dot product and norm of A
  for (const key of keysA) {
    const valA = a[key];
    normA += valA * valA;
    if (keysB.has(key)) {
      dotProduct += valA * b[key];
    }
  }

  // Compute norm of B
  for (const key of keysB) {
    const valB = b[key];
    normB += valB * valB;
  }

  // Avoid division by zero
  if (normA === 0 || normB === 0) {
    return 0;
  }

  return dotProduct / (Math.sqrt(normA) * Math.sqrt(normB));
}
