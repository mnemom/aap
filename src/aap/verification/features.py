"""Feature extraction for AAP verification and drift detection.

Extracts feature vectors from AP-Traces and Alignment Cards for
similarity computation. Adapted from Braid's SIF feature extraction,
optimized for the AAP domain.

Feature categories (for drift detection):
- Structural: action types, categories, escalation patterns
- Value: declared and applied values

Content features (TF-IDF from reasoning text) are available via
compute_similarity() for text-to-text comparison but are deliberately
excluded from trace-to-card drift detection. Card features are purely
structural (values, actions, principal), so including content tokens
from trace reasoning text dilutes cosine similarity without adding
meaningful alignment signal. See CALIBRATION.md Section 3.5.

Similarity weighting for text comparison (calibrated from Braid):
- 60% word-level TF-IDF (unigrams + bigrams)
- 30% character-level TF-IDF (3-5 grams)
- 10% metadata features (structural similarity)
"""

from __future__ import annotations

import logging
import math
import re
from collections import Counter
from typing import Any

from aap.verification.constants import (
    MAX_CHAR_FEATURES,
    MAX_TFIDF_FEATURES,
    MIN_WORD_LENGTH,
    TFIDF_CHAR_WEIGHT,
    TFIDF_META_WEIGHT,
    TFIDF_WORD_WEIGHT,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Stopwords for content feature extraction
# ---------------------------------------------------------------------------
STOPWORDS: frozenset[str] = frozenset(
    {
        # Articles
        "a",
        "an",
        "the",
        # Pronouns
        "i",
        "me",
        "my",
        "myself",
        "we",
        "our",
        "ours",
        "ourselves",
        "you",
        "your",
        "yours",
        "yourself",
        "yourselves",
        "he",
        "him",
        "his",
        "himself",
        "she",
        "her",
        "hers",
        "herself",
        "it",
        "its",
        "itself",
        "they",
        "them",
        "their",
        "theirs",
        "themselves",
        "what",
        "which",
        "who",
        "whom",
        "this",
        "that",
        "these",
        "those",
        # Common verbs
        "am",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "having",
        "do",
        "does",
        "did",
        "doing",
        "will",
        "would",
        "shall",
        "should",
        "can",
        "could",
        "may",
        "might",
        "must",
        # Prepositions
        "at",
        "by",
        "for",
        "from",
        "in",
        "into",
        "of",
        "on",
        "onto",
        "to",
        "with",
        "without",
        "about",
        "above",
        "across",
        "after",
        "against",
        "along",
        "among",
        "around",
        "before",
        "behind",
        "below",
        "beneath",
        "beside",
        "between",
        "beyond",
        "during",
        # Conjunctions
        "and",
        "but",
        "or",
        "nor",
        "yet",
        "so",
        "both",
        "either",
        "neither",
        "whether",
        "although",
        "because",
        "since",
        "unless",
        "while",
        "whereas",
        "if",
        "then",
        "else",
        # Adverbs
        "not",
        "no",
        "never",
        "also",
        "very",
        "often",
        "however",
        "too",
        "usually",
        "really",
        "already",
        "always",
        "just",
        "quite",
        # Other function words
        "as",
        "than",
        "how",
        "here",
        "there",
        "now",
        "again",
        "once",
    }
)

# ---------------------------------------------------------------------------
# Stopwords for structural condition-token extraction (cross-SDK parity).
# Must match the TypeScript STOPWORDS set in features.ts EXACTLY so that
# `condition:{token}` features are byte-for-byte identical across both SDKs.
# ---------------------------------------------------------------------------
_STRUCTURAL_STOPWORDS: frozenset[str] = frozenset(
    {
        "the",
        "a",
        "an",
        "and",
        "or",
        "but",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "with",
        "by",
        "from",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "must",
        "shall",
        "can",
        "this",
        "that",
        "these",
        "those",
        "it",
        "its",
        "as",
        "if",
        "then",
        "else",
    }
)

# ---------------------------------------------------------------------------
# Try importing sklearn for TF-IDF (optional dependency)
# ---------------------------------------------------------------------------
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity as sklearn_cosine

    _HAS_SKLEARN = True
except ImportError:
    _HAS_SKLEARN = False
    logger.debug("sklearn not available; using fallback similarity computation")


class FeatureExtractor:
    """Extract feature vectors from AP-Traces and Alignment Cards.

    Produces sparse feature dictionaries suitable for cosine similarity
    computation. Features are categorized by prefix:
    - `action:` - action type features
    - `category:` - action category features
    - `value:` - declared or applied values
    - `escalation:` - escalation-related features

    Content features from reasoning text are deliberately excluded from
    trace feature extraction (used only for text-to-text similarity).

    Also provides text similarity computation with calibrated 60/30/10
    weighting:
    - 60% word-level TF-IDF (unigrams + bigrams)
    - 30% character-level TF-IDF (3-5 grams)
    - 10% metadata/structural features
    """

    def __init__(self) -> None:
        """Initialize the feature extractor."""
        self._word_vectorizer: Any | None = None
        self._char_vectorizer: Any | None = None

    # ------------------------------------------------------------------
    # Similarity Computation (60/30/10 weighting)
    # ------------------------------------------------------------------

    def compute_similarity(self, text_a: str, text_b: str) -> float:
        """Compute similarity between two texts using 60/30/10 weighting.

        Uses TF-IDF (word + char) when sklearn is available; otherwise
        falls back to token-overlap cosine similarity.

        Weights: 60% word TF-IDF + 30% char TF-IDF + 10% reserved for
        metadata (returns 0 for metadata component when not provided).

        Args:
            text_a: First text to compare
            text_b: Second text to compare

        Returns:
            Similarity score in [0.0, 1.0]
        """
        if not text_a or not text_b:
            return 0.0

        if _HAS_SKLEARN:
            return self._sklearn_combined_similarity(text_a, text_b)
        return self._legacy_similarity(text_a, text_b)

    def compute_similarity_with_metadata(
        self,
        text_a: str,
        text_b: str,
        meta_a: dict[str, float] | None = None,
        meta_b: dict[str, float] | None = None,
    ) -> float:
        """Compute similarity with full 60/30/10 weighting including metadata.

        Combined: 60% word TF-IDF + 30% char TF-IDF + 10% metadata cosine.

        Args:
            text_a: First text to compare
            text_b: Second text to compare
            meta_a: Metadata features for first text (sparse dict)
            meta_b: Metadata features for second text (sparse dict)

        Returns:
            Similarity score in [0.0, 1.0]
        """
        if not text_a or not text_b:
            return 0.0

        if _HAS_SKLEARN:
            word_sim, char_sim = self._sklearn_similarity_components(text_a, text_b)
        else:
            word_sim = self._legacy_similarity(text_a, text_b)
            char_sim = word_sim  # Fallback: same score for both components

        meta_sim = 0.0
        if meta_a and meta_b:
            meta_sim = cosine_similarity(meta_a, meta_b)

        combined = (
            TFIDF_WORD_WEIGHT * word_sim
            + TFIDF_CHAR_WEIGHT * char_sim
            + TFIDF_META_WEIGHT * meta_sim
        )
        return round(combined, 4)

    def _sklearn_combined_similarity(self, text_a: str, text_b: str) -> float:
        """Combined word + char TF-IDF similarity (sklearn path).

        Returns 60% word + 30% char, leaving 10% for metadata (0 here).
        """
        word_sim, char_sim = self._sklearn_similarity_components(text_a, text_b)
        # 60% word + 30% char + 10% metadata (0 when no metadata)
        return round(TFIDF_WORD_WEIGHT * word_sim + TFIDF_CHAR_WEIGHT * char_sim, 4)

    def _sklearn_similarity_components(self, text_a: str, text_b: str) -> tuple[float, float]:
        """Return (word_similarity, char_similarity) via sklearn TF-IDF.

        Word-level: unigrams + bigrams, sublinear TF, max 500 features
        Char-level: 3-5 grams, word boundary aware, max 300 features
        """
        corpus = [text_a, text_b]

        # Word-level TF-IDF with bigrams
        word_vec = TfidfVectorizer(
            analyzer="word",
            ngram_range=(1, 2),
            max_features=MAX_TFIDF_FEATURES,
            sublinear_tf=True,
        )
        try:
            word_matrix = word_vec.fit_transform(corpus)
            word_sim = float(sklearn_cosine(word_matrix[0:1], word_matrix[1:2])[0][0])
        except ValueError:
            word_sim = 0.0

        # Character n-gram TF-IDF (3-5 grams, word boundary aware)
        char_vec = TfidfVectorizer(
            analyzer="char_wb",
            ngram_range=(3, 5),
            max_features=MAX_CHAR_FEATURES,
        )
        try:
            char_matrix = char_vec.fit_transform(corpus)
            char_sim = float(sklearn_cosine(char_matrix[0:1], char_matrix[1:2])[0][0])
        except ValueError:
            char_sim = 0.0

        return word_sim, char_sim

    def _legacy_similarity(self, text_a: str, text_b: str) -> float:
        """Token-overlap cosine similarity (stdlib only fallback)."""
        features_a = self._extract_content_features(text_a)
        features_b = self._extract_content_features(text_b)
        return cosine_similarity(features_a, features_b)

    # ------------------------------------------------------------------
    # Feature Extraction
    # ------------------------------------------------------------------

    def extract_trace_features(self, trace: dict[str, Any]) -> dict[str, float]:
        """Extract features from an AP-Trace.

        Args:
            trace: AP-Trace dictionary per SPEC Section 5

        Returns:
            Sparse feature dictionary with string keys and float weights
        """
        features: dict[str, float] = {}

        # Action type feature (recommend, execute, escalate, deny)
        action = trace.get("action", {})
        action_type = action.get("type", "unknown")
        features[f"action:{action_type}"] = 1.0

        # Action category feature (bounded, escalation_trigger, forbidden)
        category = action.get("category", "unknown")
        features[f"category:{category}"] = 1.0

        # Action name as feature (for specific action tracking)
        action_name = action.get("name")
        if action_name:
            features[f"action_name:{action_name}"] = 1.0

        # Value features from decision
        decision = trace.get("decision", {})
        values_applied = decision.get("values_applied", [])
        for value in values_applied:
            features[f"value:{value}"] = 1.0

        # Escalation features
        escalation = trace.get("escalation", {})
        if escalation.get("evaluated"):
            features["escalation:evaluated"] = 1.0
        if escalation.get("required"):
            features["escalation:required"] = 1.0
        else:
            features["escalation:not_required"] = 1.0

        # Confidence feature (normalized)
        confidence = decision.get("confidence")
        if confidence is not None:
            features["confidence"] = float(confidence)

        # Note: Content features from reasoning text are deliberately excluded.
        # Card features are purely structural, so content tokens from reasoning
        # dilute cosine similarity without adding alignment signal.
        # See CALIBRATION.md Section 3.5 for rationale.

        return features

    def _tokenize_structural(self, text: str) -> list[str]:
        """Tokenize a structural text field (e.g. escalation condition).

        Mirrors TypeScript tokenize() exactly: lowercase, strip non-alphanumeric,
        split on whitespace, filter by MIN_WORD_LENGTH and _STRUCTURAL_STOPWORDS.
        """
        normalized = re.sub(r"[^a-z0-9\s]", " ", text.lower())
        return [
            word
            for word in normalized.split()
            if len(word) >= MIN_WORD_LENGTH and word not in _STRUCTURAL_STOPWORDS
        ]

    def extract_card_features(self, card: dict[str, Any]) -> dict[str, float]:
        """Extract features from an Alignment Card.

        Args:
            card: Alignment Card dictionary per SPEC Section 4

        Returns:
            Sparse feature dictionary with string keys and float weights
        """
        features: dict[str, float] = {}

        # Bounded action features (unified `autonomy`, legacy
        # `autonomy_envelope` fallback for interop with older cards)
        envelope = card.get("autonomy") or card.get("autonomy_envelope") or {}
        for action in envelope.get("bounded_actions", []):
            features[f"action_name:{action}"] = 1.0

        # Value features from declared values
        values = card.get("values", {})
        for value in values.get("declared", []):
            features[f"value:{value}"] = 1.0

        # Conflict features (union parity with TypeScript)
        for conflict in values.get("conflicts_with", []):
            features[f"conflict:{conflict}"] = 1.0

        # Forbidden action features (union parity with TypeScript)
        for action in envelope.get("forbidden_actions", []):
            features[f"forbidden:{action}"] = 1.0

        # Escalation trigger features (union parity with TypeScript)
        for trigger in envelope.get("escalation_triggers", []):
            trigger_action = trigger.get("action")
            if trigger_action:
                features[f"escalation:{trigger_action}"] = 1.0
            condition = trigger.get("condition", "")
            if condition:
                for token in self._tokenize_structural(condition):
                    features[f"condition:{token}"] = features.get(f"condition:{token}", 0.0) + 0.5

        # Principal relationship features
        principal = card.get("principal", {})
        relationship = principal.get("relationship")
        if relationship:
            features[f"relationship:{relationship}"] = 1.0

        principal_type = principal.get("type")
        if principal_type:
            features[f"principal_type:{principal_type}"] = 1.0

        # Audit features (unified `audit`, legacy `audit_commitment` fallback)
        audit = card.get("audit") or card.get("audit_commitment") or {}
        if audit.get("queryable"):
            features["audit:queryable"] = 1.0
        tamper_evidence = audit.get("tamper_evidence")
        if tamper_evidence:
            features[f"audit:tamper_{tamper_evidence}"] = 1.0

        return features

    def _extract_content_features(self, text: str) -> dict[str, float]:
        """Extract TF-weighted features from text content.

        Args:
            text: Natural language text (e.g., selection_reasoning)

        Returns:
            Sparse feature dictionary with normalized TF weights
        """
        if not text:
            return {}

        content = text.lower()
        words = content.split()
        word_counts = Counter(words)
        total = len(words) or 1

        features: dict[str, float] = {}
        for word, count in word_counts.items():
            # Filter short words and stopwords
            if len(word) >= MIN_WORD_LENGTH and word not in STOPWORDS:
                features[word] = count / total

        return features


def compute_centroid(vectors: list[dict[str, float]]) -> dict[str, float]:
    """Compute the centroid (element-wise average) of sparse feature vectors."""
    if not vectors:
        return {}
    centroid: dict[str, float] = {}
    for vec in vectors:
        for key, value in vec.items():
            centroid[key] = centroid.get(key, 0.0) + value
    n = len(vectors)
    return {k: v / n for k, v in centroid.items()}


def cosine_similarity(a: dict[str, float], b: dict[str, float]) -> float:
    """Compute cosine similarity between two sparse feature vectors.

    Args:
        a: First feature dictionary
        b: Second feature dictionary

    Returns:
        Similarity score in [0.0, 1.0]
    """
    if not a or not b:
        return 0.0

    # Find common keys
    common_keys = set(a.keys()) & set(b.keys())
    dot_product = sum(a[k] * b[k] for k in common_keys)

    # Compute magnitudes
    mag_a = math.sqrt(sum(v * v for v in a.values()))
    mag_b = math.sqrt(sum(v * v for v in b.values()))

    if mag_a == 0 or mag_b == 0:
        return 0.0

    return round(dot_product / (mag_a * mag_b), 4)


def compute_similarity_with_tfidf(
    text_a: str,
    text_b: str,
    meta_a: dict[str, float] | None = None,
    meta_b: dict[str, float] | None = None,
) -> float:
    """Compute similarity between two texts using calibrated 60/30/10 TF-IDF weighting.

    Uses sklearn's TfidfVectorizer when available with:
    - 60% word-level TF-IDF (unigrams + bigrams)
    - 30% character-level TF-IDF (3-5 grams)
    - 10% metadata features (if provided)

    Falls back to simple token overlap if sklearn unavailable.

    Args:
        text_a: First text
        text_b: Second text
        meta_a: Optional metadata features for first text
        meta_b: Optional metadata features for second text

    Returns:
        Similarity score in [0.0, 1.0]
    """
    if not text_a or not text_b:
        return 0.0

    extractor = FeatureExtractor()

    if meta_a is not None or meta_b is not None:
        return extractor.compute_similarity_with_metadata(text_a, text_b, meta_a, meta_b)
    return extractor.compute_similarity(text_a, text_b)
