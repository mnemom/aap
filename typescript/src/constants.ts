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
export const DEFAULT_SUSTAINED_CHECKS_THRESHOLD = 3;

/**
 * @deprecated Use `DEFAULT_SUSTAINED_CHECKS_THRESHOLD`.
 * Renamed in 0.7.0 to align with AIP terminology. Will be removed at 1.0.0.
 */
export const DEFAULT_SUSTAINED_TURNS_THRESHOLD = DEFAULT_SUSTAINED_CHECKS_THRESHOLD;

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

// Fleet Coherence
// ----------------
/** Standard deviations below fleet mean to flag an agent as outlier */
export const OUTLIER_STD_DEV_THRESHOLD = 1.0;

/** Minimum pairwise score to consider agents compatible for cluster analysis */
export const CLUSTER_COMPATIBILITY_THRESHOLD = 0.7;

// Version
// -------
export const ALGORITHM_VERSION = "1.2.0";
