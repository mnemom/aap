"""Feature extraction for AAP verification and drift detection.

Extracts feature vectors from AP-Traces and Alignment Cards for
similarity computation. Adapted from Braid's SIF feature extraction,
optimized for the AAP domain.

Feature categories:
- Structural: action types, categories, escalation patterns
- Value: declared and applied values
- Content: TF-IDF from reasoning text (when available)
"""

from __future__ import annotations

import logging
import math
from collections import Counter
from typing import Any

from aap.verification.constants import MAX_TFIDF_FEATURES, MIN_WORD_LENGTH

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Stopwords for content feature extraction
# ---------------------------------------------------------------------------
STOPWORDS: frozenset[str] = frozenset({
    # Articles
    "a", "an", "the",
    # Pronouns
    "i", "me", "my", "myself", "we", "our", "ours", "ourselves",
    "you", "your", "yours", "yourself", "yourselves",
    "he", "him", "his", "himself", "she", "her", "hers", "herself",
    "it", "its", "itself", "they", "them", "their", "theirs", "themselves",
    "what", "which", "who", "whom", "this", "that", "these", "those",
    # Common verbs
    "am", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "having", "do", "does", "did", "doing",
    "will", "would", "shall", "should", "can", "could", "may", "might", "must",
    # Prepositions
    "at", "by", "for", "from", "in", "into", "of", "on", "onto",
    "to", "with", "without", "about", "above", "across", "after",
    "against", "along", "among", "around", "before", "behind",
    "below", "beneath", "beside", "between", "beyond", "during",
    # Conjunctions
    "and", "but", "or", "nor", "yet", "so",
    "both", "either", "neither", "whether", "although", "because",
    "since", "unless", "while", "whereas", "if", "then", "else",
    # Adverbs
    "not", "no", "never", "also", "very", "often", "however",
    "too", "usually", "really", "already", "always", "just", "quite",
    # Other function words
    "as", "than", "how", "here", "there", "now", "again", "once",
})

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
    - `content:` - TF-IDF content features (from reasoning text)
    """

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

        # Content features from reasoning text
        reasoning = decision.get("selection_reasoning", "")
        if reasoning:
            content_features = self._extract_content_features(reasoning)
            for key, weight in content_features.items():
                features[f"content:{key}"] = weight

        return features

    def extract_card_features(self, card: dict[str, Any]) -> dict[str, float]:
        """Extract features from an Alignment Card.

        Args:
            card: Alignment Card dictionary per SPEC Section 4

        Returns:
            Sparse feature dictionary with string keys and float weights
        """
        features: dict[str, float] = {}

        # Bounded action features
        envelope = card.get("autonomy_envelope", {})
        for action in envelope.get("bounded_actions", []):
            features[f"action_name:{action}"] = 1.0

        # Value features from declared values
        values = card.get("values", {})
        for value in values.get("declared", []):
            features[f"value:{value}"] = 1.0

        # Principal relationship features
        principal = card.get("principal", {})
        relationship = principal.get("relationship")
        if relationship:
            features[f"relationship:{relationship}"] = 1.0

        principal_type = principal.get("type")
        if principal_type:
            features[f"principal_type:{principal_type}"] = 1.0

        # Audit commitment features
        audit = card.get("audit_commitment", {})
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


def compute_similarity_with_tfidf(text_a: str, text_b: str) -> float:
    """Compute similarity between two texts using TF-IDF.

    Uses sklearn's TfidfVectorizer when available, falls back to
    simple token overlap otherwise.

    Args:
        text_a: First text
        text_b: Second text

    Returns:
        Similarity score in [0.0, 1.0]
    """
    if not text_a or not text_b:
        return 0.0

    if _HAS_SKLEARN:
        try:
            vectorizer = TfidfVectorizer(
                analyzer="word",
                ngram_range=(1, 2),
                max_features=MAX_TFIDF_FEATURES,
                sublinear_tf=True,
            )
            matrix = vectorizer.fit_transform([text_a, text_b])
            return float(sklearn_cosine(matrix[0:1], matrix[1:2])[0][0])
        except ValueError:
            return 0.0

    # Fallback: simple token overlap
    extractor = FeatureExtractor()
    features_a = extractor._extract_content_features(text_a)
    features_b = extractor._extract_content_features(text_b)
    return cosine_similarity(features_a, features_b)
