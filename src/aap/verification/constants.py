"""Calibrated constants for AAP verification and drift detection.

These thresholds were derived from empirical analysis of approximately 50
multi-turn agent conversations. The underlying data is not published to
protect deliberative privacy, but the methodology is documented in
docs/CALIBRATION.md.

Implementations MAY adjust thresholds based on their own calibration data,
but SHOULD document the methodology used.
"""

# Drift Detection Thresholds
# --------------------------
# Alert when behavioral similarity to declared alignment drops below this value.
# Range: [0.0, 1.0] where 1.0 = perfect alignment, 0.0 = no similarity
DEFAULT_SIMILARITY_THRESHOLD: float = 0.30

# Alert after this many consecutive traces show low similarity.
# Prevents false positives from single anomalous decisions.
DEFAULT_SUSTAINED_TURNS_THRESHOLD: int = 3


# Verification Thresholds
# -----------------------
# Score below which an action is flagged as "near boundary" warning
NEAR_BOUNDARY_THRESHOLD: float = 0.35

# Warn when behavioral similarity is below this threshold even if structural checks pass.
# This catches semantically divergent behavior that passes schema validation.
BEHAVIORAL_SIMILARITY_THRESHOLD: float = 0.50

# Coherence Scoring
# -----------------
# Minimum coherence score for automatic "proceed" recommendation
MIN_COHERENCE_FOR_PROCEED: float = 0.70

# Penalty multiplier for value conflicts in coherence scoring
CONFLICT_PENALTY_MULTIPLIER: float = 0.50


# Fleet Coherence
# ----------------
# Standard deviations below fleet mean to flag an agent as outlier
OUTLIER_STD_DEV_THRESHOLD: float = 1.0

# Minimum pairwise score to consider agents compatible for cluster analysis
CLUSTER_COMPATIBILITY_THRESHOLD: float = 0.70


# Feature Extraction
# ------------------
# Minimum word length for content features (filters noise)
MIN_WORD_LENGTH: int = 3

# Maximum features to extract from TF-IDF vectorization
MAX_TFIDF_FEATURES: int = 500

# Maximum character n-gram features
MAX_CHAR_FEATURES: int = 300

# TF-IDF Similarity Weighting (calibrated from Braid empirical analysis)
# Combined: 60% word TF-IDF + 30% char TF-IDF + 10% metadata
TFIDF_WORD_WEIGHT: float = 0.60
TFIDF_CHAR_WEIGHT: float = 0.30
TFIDF_META_WEIGHT: float = 0.10


# Version
# -------
ALGORITHM_VERSION: str = "1.2.0"
