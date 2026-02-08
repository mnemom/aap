/**
 * Calibrated constants for AAP verification and drift detection.
 *
 * These thresholds were derived from empirical analysis of approximately 50
 * multi-turn agent conversations. The underlying data is not published to
 * protect deliberative privacy, but the methodology is documented in
 * docs/CALIBRATION.md.
 *
 * Implementations MAY adjust thresholds based on their own calibration data,
 * but SHOULD document the methodology used.
 */

// Drift Detection Thresholds
// --------------------------
/** Alert when behavioral similarity to declared alignment drops below this value. */
export const DEFAULT_SIMILARITY_THRESHOLD = 0.3;

/** Alert after this many consecutive traces show low similarity. */
export const DEFAULT_SUSTAINED_TURNS_THRESHOLD = 3;

// Verification Thresholds
// -----------------------
/** Score below which an action is flagged as "near boundary" warning */
export const NEAR_BOUNDARY_THRESHOLD = 0.35;

// Coherence Scoring
// -----------------
/** Minimum coherence score for automatic "proceed" recommendation */
export const MIN_COHERENCE_FOR_PROCEED = 0.7;

/** Penalty multiplier for value conflicts in coherence scoring */
export const CONFLICT_PENALTY_MULTIPLIER = 0.5;

// Feature Extraction
// ------------------
/** Minimum word length for content features (filters noise) */
export const MIN_WORD_LENGTH = 3;

/** Maximum features to extract from TF-IDF vectorization */
export const MAX_TFIDF_FEATURES = 500;

// Version
// -------
export const ALGORITHM_VERSION = "1.2.0";
