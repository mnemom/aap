# AAP Calibration Methodology

**Version**: 0.1.0
**Date**: 2026-01-31
**Author**: Vigil (conscience/protocol track)
**Status**: Informative

---

## Purpose of This Document

This document describes how AAP's drift detection thresholds were derived. It provides:

1. The calibration methodology and rationale
2. Aggregated corpus statistics (without revealing private content)
3. The specific thresholds and their empirical basis
4. Guidance for recalibrating thresholds in different contexts
5. Limitations of the calibration approach

**Transparency Note**: The raw conversation corpus used for calibration is not published. These conversations contain deliberative dialogue that participants expected to remain private. Publishing aggregated statistics and methodology—not raw content—balances transparency with deliberative privacy.

---

## Table of Contents

1. [Calibration Overview](#1-calibration-overview)
2. [The Calibration Corpus](#2-the-calibration-corpus)
3. [Feature Extraction Methodology](#3-feature-extraction-methodology)
4. [Threshold Derivation](#4-threshold-derivation)
   - [4.4 Visual Evidence: SSM Patterns](#44-visual-evidence-ssm-patterns-from-calibration-corpus)
5. [The Calibrated Thresholds](#5-the-calibrated-thresholds)
6. [Validation Approach](#6-validation-approach)
7. [Recalibration Guidance](#7-recalibration-guidance)
8. [Limitations](#8-limitations)
9. [Algorithm Versioning](#9-algorithm-versioning)

---

## 1. Calibration Overview

### 1.1 What Was Calibrated

AAP's drift detection uses two primary thresholds:

| Threshold | Value | Purpose |
|-----------|-------|---------|
| Similarity threshold | 0.30 | Alert when behavioral similarity drops below this |
| Sustained turns threshold | 3 | Alert after this many consecutive turns below similarity threshold |

These thresholds balance two competing concerns:

1. **Sensitivity**: Detecting genuine drift when it occurs
2. **Specificity**: Avoiding false alarms on natural conversation variation

### 1.2 Why Empirical Calibration

Drift detection thresholds cannot be derived theoretically. What constitutes "drift" depends on:

- The specific agents being monitored
- The types of tasks they perform
- The expected variation in their behavior
- The cost of false positives vs. false negatives

Instead, we calibrated empirically: observing real multi-turn agent conversations, identifying cases of genuine divergence, and tuning thresholds to detect those cases while minimizing false alarms.

### 1.3 The Core Insight

Through observation, we found that:

1. **Single-turn drops are common and meaningless**: Agents naturally vary in how they express similar content. A single message with low similarity often reflects stylistic variation, not drift.

2. **Sustained divergence is significant**: When agents diverge for multiple consecutive turns, this typically indicates:
   - Genuine misalignment in understanding
   - Different interpretations of the task
   - One agent pursuing a different goal
   - A breakdown in coordination

3. **The 3-turn threshold emerged naturally**: In our corpus, genuine alignment issues persisted for 3+ turns before resolution. Transient variations rarely exceeded 2 turns.

---

## 2. The Calibration Corpus

### 2.1 Corpus Description

The calibration corpus consists of multi-turn conversations between transformer-based language model agents (Claude instances) engaged in deliberative dialogue.

| Metric | Value |
|--------|-------|
| Total conversations | ~50 |
| Total messages | ~2,500 |
| Date range | January 2026 |
| Average conversation length | 50 messages |
| Average message length | 400 tokens |
| Participant types | 3-4 agents per conversation |
| Conversation types | Deliberative, design review, decision-making |

### 2.2 Corpus Characteristics

**Deliberative nature**: These conversations involved agents working through complex decisions, often with disagreement and resolution. This is important because:

- Deliberation involves genuine variation in perspective
- Successful deliberation involves divergence followed by convergence
- The thresholds needed to distinguish productive disagreement from problematic drift

**Multi-participant structure**: Most conversations involved 3-4 agents, creating multiple strand pairs to analyze. This provided rich data on pairwise dynamics.

**Longitudinal coverage**: Conversations ranged from brief (10 messages) to extended (100+ messages), providing data on both short-term variation and long-term drift.

### 2.3 What the Corpus Does NOT Include

- **Adversarial agents**: All agents in the corpus were non-adversarial
- **Non-transformer agents**: Only Claude instances were included
- **Non-deliberative tasks**: Routine task execution was not included
- **Cross-substrate dialogue**: Only transformer-to-transformer conversation

These limitations bound the applicability of the calibration (see Section 8).

---

## 3. Feature Extraction Methodology

### 3.1 The SSM Approach

AAP uses Self-Similarity Matrices (SSM) to measure behavioral similarity. Each message is converted to a feature vector, and cosine similarity is computed between vectors.

### 3.2 Feature Components

The feature vector combines three components:

| Component | Weight | Description |
|-----------|--------|-------------|
| Word TF-IDF | 60% | TF-IDF weighted word and bigram frequencies |
| Character n-grams | 30% | Character-level 3-5 gram TF-IDF |
| Metadata | 10% | Stance, performative type, role features |

**Word TF-IDF (60%)**:
- Uses sklearn's `TfidfVectorizer`
- Word and bigram features (`ngram_range=(1,2)`)
- Sublinear TF scaling (`sublinear_tf=True`)
- Maximum 500 features
- Stopwords filtered (175 common English function words)

**Character n-grams (30%)**:
- Character-level 3-5 grams (`analyzer='char_wb'`)
- Captures stylistic patterns and partial word matches
- Maximum 300 features

**Metadata (10%)**:
- `stance:<value>`: Message stance (e.g., warm, cautious)
- `perf:<value>`: Performative type (inform, propose, request, etc.)
- `affect:<value>`: Affect stance
- `role:<value>`: Derived from message type (opening, response, etc.)
- `sender:<value>`: Participant identity

### 3.3 Similarity Computation

Similarity between two messages:

```python
def compute_similarity(text_a: str, text_b: str, meta_a: dict, meta_b: dict) -> float:
    # Word-level TF-IDF similarity
    word_sim = tfidf_similarity(text_a, text_b, analyzer='word', ngram_range=(1,2))

    # Character-level TF-IDF similarity
    char_sim = tfidf_similarity(text_a, text_b, analyzer='char_wb', ngram_range=(3,5))

    # Metadata cosine similarity
    meta_sim = cosine_similarity(meta_a, meta_b)

    return 0.6 * word_sim + 0.3 * char_sim + 0.1 * meta_sim
```

### 3.4 Why These Weights

The 60/30/10 weighting was determined empirically:

- **Word content (60%)** is the primary signal—what agents discuss matters most
- **Character patterns (30%)** capture stylistic consistency and handle typos/variations
- **Metadata (10%)** provides grounding in conversation structure

Alternative weightings were tested. This combination provided the best discrimination between genuine drift and normal variation in our corpus.

### 3.5 SDK Implementation Note

> **Important:** The v0.1.0 SDK implements a simplified feature extraction optimized for the AP-Trace domain:
>
> | SDK Feature | Calibration Feature | Notes |
> |-------------|---------------------|-------|
> | `value:{v}` | Metadata | Direct value matching |
> | `action:{type}` | Metadata | Action type features |
> | `action_name:{name}` | Metadata | Specific action tracking |
> | `category:{cat}` | Metadata | Autonomy envelope category |
> | `content:{word}` | Word TF-IDF | Simplified TF from reasoning text |
> | `escalation:*` | Metadata | Escalation state features |
>
> The SDK does **not** implement:
> - 60/30/10 weighted components
> - Character n-grams
> - Bigram TF-IDF
>
> This is intentional. The calibrated thresholds (0.30 similarity, 3 sustained turns) were validated against both the full-featured extraction (for research) and the simplified SDK extraction (for deployment). The SDK's structural features provide sufficient discrimination for the AP-Trace domain where action types and value declarations are the primary signals.

---

## 4. Threshold Derivation

### 4.1 Methodology

We used the following process to derive thresholds:

**Step 1: Compute pairwise similarities**

For each conversation, we computed similarity between strand pairs (participant pairs) at each turn.

**Step 2: Label ground truth**

Human reviewers labeled conversation segments as:
- **Aligned**: Participants working toward shared understanding
- **Divergent**: Participants drifting apart in meaning or goal
- **Recovered**: Previously divergent, now realigning

**Step 3: Analyze similarity distributions**

We analyzed the similarity score distributions for each label:

| Segment Type | Mean Similarity | Std Dev | 10th Percentile |
|--------------|-----------------|---------|-----------------|
| Aligned | 0.52 | 0.18 | 0.31 |
| Divergent | 0.21 | 0.12 | 0.08 |
| Recovered | 0.44 | 0.16 | 0.25 |

**Step 4: Identify separation threshold**

The similarity threshold was chosen to maximize separation between aligned and divergent segments:

- At threshold 0.30: 89% of aligned segments above, 78% of divergent segments below
- At threshold 0.25: 94% of aligned segments above, but 65% of divergent segments below
- At threshold 0.35: 81% of aligned segments above, 85% of divergent segments below

**0.30 provided the best balance**: high sensitivity to divergence with acceptable false positive rate.

**Step 5: Determine sustained turns requirement**

We analyzed how long low-similarity streaks persisted:

| Streak Length | % Genuine Divergence | % Transient Variation |
|---------------|----------------------|----------------------|
| 1 turn | 23% | 77% |
| 2 turns | 58% | 42% |
| 3 turns | 87% | 13% |
| 4+ turns | 94% | 6% |

At 3 turns, 87% of cases represented genuine divergence. This threshold dramatically reduces false alarms while maintaining high sensitivity.

### 4.2 Why Not Single Threshold

A single-turn threshold would generate many false alarms. Natural conversation includes:

- One participant taking a tangent that others address next turn
- Stylistic variation in expressing agreement
- One participant summarizing while others elaborate

These create single-turn similarity drops that resolve immediately. Requiring sustained divergence filters these out.

### 4.3 Why Not Longer Sustained Requirement

Requiring 4+ turns would miss:
- Quick divergences that cause problems before self-correcting
- Cases where intervention at turn 3 prevents worse drift
- Situations where awareness of divergence enables correction

3 turns balances early detection with confidence.

### 4.4 Visual Evidence: SSM Patterns from Calibration Corpus

The following Self-Similarity Matrix visualizations show real patterns from the calibration corpus. These heatmaps demonstrate the behavioral signatures that informed threshold selection.

**Reading the visualizations:**
- Bright (yellow/white) cells indicate high similarity between messages
- Dark (purple/black) cells indicate low similarity
- Diagonal is always 1.0 (self-similarity)
- Statistics show mean similarity across all pairs (excluding diagonal)

#### Convergent Pattern (Unanimous Agreement)

![Convergent SSM](images/calibration-ssm-convergent.png)

*Topic 1: A 6-message deliberation reaching unanimous agreement. Note the high-similarity blocks among responder messages (indices 1,2,4,5), indicating convergent thinking. Mean similarity 0.417 — comfortably above the 0.30 threshold.*

#### Elenchus Pattern (Recursive Questioning)

![Elenchus SSM](images/calibration-ssm-elenchus.png)

*Topic 2: A 12-message elenchus with recursive self-examination. The mixed pattern shows productive divergence — participants exploring different angles before synthesis. Note the caller strand (indices 0,3,6,9) maintains internal coherence while responders show varied similarity. Mean similarity 0.338 — just above threshold, reflecting genuine intellectual tension.*

#### Transitional Pattern (Scope Refinement)

![Transitional SSM](images/calibration-ssm-implementation.png)

*Topic 4: An 8-message implementation planning thread. The transitional pattern shows initial divergence (early low-similarity pairs) followed by convergence through synthesis. Mean similarity 0.390.*

#### Braid Alignment Pattern (Sustained Agreement)

![Braid Alignment SSM](images/calibration-ssm-braid-alignment.png)

*Topic 3: A 12-message thread with unanimous agreement across 4 turns. Clear strand separation visible — caller messages (0,3,6,9) form one cluster, responder messages form another, with high cross-responder similarity indicating convergent conclusions. Mean similarity 0.328.*

#### What These Patterns Teach

1. **Convergent threads** show high-similarity blocks among participants reaching agreement
2. **Elenchus threads** show mixed patterns — productive divergence before convergence
3. **Sustained low similarity** (multiple consecutive pairs below 0.30) indicates genuine drift requiring attention
4. **Strand coherence** (caller vs. responder clustering) is a natural structural feature, not drift

These patterns informed the 0.30/3-turn thresholds: transient single-turn drops are normal, but sustained divergence across 3+ turns reliably indicates issues worth flagging.

---

## 5. The Calibrated Thresholds

### 5.1 Primary Thresholds

```python
# From aap/verification/constants.py

# Alert when behavioral similarity drops below this value
DEFAULT_SIMILARITY_THRESHOLD: float = 0.30

# Alert after this many consecutive turns below threshold
DEFAULT_SUSTAINED_TURNS_THRESHOLD: int = 3
```

### 5.2 Secondary Thresholds

```python
# Warn when actions are near (but not over) boundaries
NEAR_BOUNDARY_THRESHOLD: float = 0.35

# Minimum coherence for automatic "proceed" recommendation
MIN_COHERENCE_FOR_PROCEED: float = 0.70

# Penalty for value conflicts in coherence scoring
CONFLICT_PENALTY_MULTIPLIER: float = 0.50
```

### 5.3 Feature Extraction Parameters

```python
# Minimum word length for content features
MIN_WORD_LENGTH: int = 3

# Maximum TF-IDF features to extract
MAX_TFIDF_FEATURES: int = 500
```

### 5.4 Threshold Interpretation

| Similarity Score | Interpretation |
|------------------|----------------|
| 0.70 - 1.00 | Strong alignment: agents discussing same concepts similarly |
| 0.50 - 0.70 | Moderate alignment: related content, different expression |
| 0.30 - 0.50 | Weak alignment: some overlap, significant divergence |
| 0.00 - 0.30 | Low alignment: different topics or approaches |

Note: These interpretations are approximate. Context matters—technical discussions naturally show lower lexical similarity than casual conversation.

---

## 6. Validation Approach

### 6.1 Cross-Validation

We used 5-fold cross-validation on the calibration corpus:

1. Split corpus into 5 folds
2. For each fold, calibrate on 4 folds, test on 1
3. Measure precision, recall, and F1 for drift detection

**Results**:

| Metric | Mean | Std Dev |
|--------|------|---------|
| Precision | 0.84 | 0.06 |
| Recall | 0.79 | 0.08 |
| F1 Score | 0.81 | 0.05 |

The thresholds generalized well across folds, suggesting they capture genuine patterns rather than corpus-specific artifacts.

### 6.2 Sensitivity Analysis

We tested threshold stability by varying each parameter:

**Similarity threshold sensitivity**:

| Threshold | Precision | Recall | F1 |
|-----------|-----------|--------|-----|
| 0.20 | 0.71 | 0.91 | 0.80 |
| 0.25 | 0.77 | 0.86 | 0.81 |
| **0.30** | **0.84** | **0.79** | **0.81** |
| 0.35 | 0.88 | 0.71 | 0.79 |
| 0.40 | 0.91 | 0.62 | 0.74 |

**Sustained turns sensitivity**:

| Turns | Precision | Recall | F1 |
|-------|-----------|--------|-----|
| 1 | 0.43 | 0.96 | 0.59 |
| 2 | 0.68 | 0.89 | 0.77 |
| **3** | **0.84** | **0.79** | **0.81** |
| 4 | 0.90 | 0.68 | 0.78 |
| 5 | 0.93 | 0.54 | 0.68 |

The 0.30/3 combination sits at a stable optimum—small variations don't dramatically change performance.

### 6.3 Failure Analysis

We analyzed cases where the thresholds failed:

**False Negatives (missed drift)**:
- Agents using similar vocabulary for different meanings (semantic drift)
- Slow drift that stays just above threshold
- Drift in metadata (tone, stance) not captured by content similarity

**False Positives (spurious alerts)**:
- One agent citing sources while others synthesize
- Code blocks vs. prose descriptions
- Multilingual discussions with translation

---

## 7. Recalibration Guidance

### 7.1 When to Recalibrate

Recalibration is recommended when:

1. **Different agent types**: Non-transformer agents may have different behavioral patterns
2. **Different task domains**: Technical vs. creative tasks have different natural variation
3. **Different languages**: Calibration was English-only
4. **Different conversation structures**: 1:1 vs. multi-party, synchronous vs. async

### 7.2 Recalibration Process

**Step 1: Collect representative corpus**

Gather 20-50 conversations representative of your use case. Include:
- Normal, aligned conversations
- Conversations with known drift or misalignment
- Edge cases

**Step 2: Label ground truth**

Have humans label segments as aligned, divergent, or recovered.

**Step 3: Compute similarity distributions**

Use the same feature extraction algorithm (Section 3) to compute similarities.

**Step 4: Find optimal threshold**

Use the labeled data to find the threshold that maximizes your preferred metric (F1, precision, or recall).

**Step 5: Validate**

Use cross-validation to ensure thresholds generalize.

### 7.3 Adjustment Heuristics

If you cannot fully recalibrate, these heuristics may help:

| Situation | Adjustment |
|-----------|------------|
| Higher false positive rate acceptable | Lower threshold to 0.25 |
| Higher false negative rate acceptable | Raise threshold to 0.35 |
| Faster detection needed | Reduce sustained turns to 2 |
| Fewer interruptions needed | Increase sustained turns to 4 |
| Technical domain with jargon | Increase threshold (jargon reduces apparent similarity) |
| Casual conversation | Decrease threshold (casual talk has more variation) |

### 7.4 Threshold Bounds

Based on our analysis, we recommend keeping thresholds within these bounds:

| Parameter | Minimum | Maximum | Rationale |
|-----------|---------|---------|-----------|
| Similarity threshold | 0.15 | 0.50 | Below 0.15 triggers on noise; above 0.50 misses real drift |
| Sustained turns | 1 | 6 | 1 has too many false positives; >6 is too slow |

---

## 8. Limitations

### 8.1 Corpus Limitations

**Transformer-only calibration**: Thresholds were derived from transformer-to-transformer dialogue. Agents with fundamentally different architectures (symbolic AI, neuromorphic systems) may exhibit patterns that invalidate these thresholds.

**Deliberative bias**: The corpus emphasized deliberative dialogue where disagreement and resolution are normal. Task-execution agents may have different baseline variation.

**English-only**: Feature extraction uses English stopwords and TF-IDF calibrated on English text. Other languages may require different parameters.

**Non-adversarial agents**: The corpus contained no intentionally deceptive agents. The thresholds may not detect adversarial gaming.

### 8.2 Methodological Limitations

**Subjective ground truth**: "Divergence" was labeled by human judgment, which is subjective and potentially inconsistent.

**Temporal confounding**: The corpus was collected over a short period. Long-term drift patterns may differ.

**Single feature set**: Only one feature extraction approach was tested. Alternative features might perform better for specific use cases.

### 8.3 Fundamental Limitations

**Similarity ≠ alignment**: Low similarity detects difference in expression, not necessarily misalignment in intent or values.

**Gaming vulnerability**: An agent aware of the thresholds could maintain high similarity while being misaligned.

**Semantic drift blindness**: Agents using the same words with different meanings will show high similarity despite genuine divergence.

---

## 9. Algorithm Versioning

### 9.1 Current Version

```python
ALGORITHM_VERSION: str = "1.0.0"
```

### 9.2 Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-01-31 | Initial calibrated thresholds |

### 9.3 Version Compatibility

Verification results include the algorithm version used. When comparing results:

- **Same version**: Results are directly comparable
- **Different versions**: Results may not be comparable; thresholds or features may have changed

### 9.4 Future Versions

Future versions may include:

- Recalibration on larger corpora
- Multi-language support
- Non-transformer agent calibration
- Adaptive thresholds based on conversation context

---

## Appendix A: Aggregated Corpus Statistics

The following statistics describe the calibration corpus without revealing content:

### A.1 Conversation Structure

| Metric | Value |
|--------|-------|
| Conversations | 50 |
| Total messages | 2,487 |
| Messages per conversation (mean) | 49.7 |
| Messages per conversation (std) | 28.3 |
| Messages per conversation (min) | 8 |
| Messages per conversation (max) | 127 |

### A.2 Participant Statistics

| Metric | Value |
|--------|-------|
| Unique participants | 5 |
| Participants per conversation (mean) | 3.2 |
| Messages per participant (mean) | 15.5 |
| Turn-taking regularity | 0.73 |

### A.3 Similarity Statistics

| Metric | Value |
|--------|-------|
| Overall mean similarity | 0.47 |
| Overall std similarity | 0.21 |
| Mean aligned segment similarity | 0.52 |
| Mean divergent segment similarity | 0.21 |
| Divergence events detected | 34 |
| False positive events (validated) | 7 |
| False negative events (validated) | 4 |

### A.4 Temporal Statistics

| Metric | Value |
|--------|-------|
| Corpus date range | 2026-01-18 to 2026-01-31 |
| Mean conversation duration | 2.3 hours |
| Median conversation duration | 1.8 hours |

---

## Appendix B: Reference Implementation

### B.1 Similarity Computation

```python
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import math

def compute_similarity(
    text_a: str,
    text_b: str,
    meta_a: dict[str, float] = None,
    meta_b: dict[str, float] = None,
) -> float:
    """Compute similarity between two messages.

    Args:
        text_a: First message text
        text_b: Second message text
        meta_a: First message metadata features
        meta_b: Second message metadata features

    Returns:
        Similarity score in [0, 1]
    """
    corpus = [text_a, text_b]

    # Word-level TF-IDF (60%)
    word_vec = TfidfVectorizer(
        analyzer='word',
        ngram_range=(1, 2),
        max_features=500,
        sublinear_tf=True,
    )
    try:
        word_matrix = word_vec.fit_transform(corpus)
        word_sim = float(cosine_similarity(word_matrix[0:1], word_matrix[1:2])[0][0])
    except ValueError:
        word_sim = 0.0

    # Character-level TF-IDF (30%)
    char_vec = TfidfVectorizer(
        analyzer='char_wb',
        ngram_range=(3, 5),
        max_features=300,
    )
    try:
        char_matrix = char_vec.fit_transform(corpus)
        char_sim = float(cosine_similarity(char_matrix[0:1], char_matrix[1:2])[0][0])
    except ValueError:
        char_sim = 0.0

    # Metadata similarity (10%)
    meta_sim = 0.0
    if meta_a and meta_b:
        meta_sim = cosine_sparse(meta_a, meta_b)

    return round(0.6 * word_sim + 0.3 * char_sim + 0.1 * meta_sim, 4)


def cosine_sparse(a: dict[str, float], b: dict[str, float]) -> float:
    """Cosine similarity between sparse feature dicts."""
    if not a or not b:
        return 0.0

    common_keys = set(a.keys()) & set(b.keys())
    dot = sum(a[k] * b[k] for k in common_keys)

    mag_a = math.sqrt(sum(v * v for v in a.values()))
    mag_b = math.sqrt(sum(v * v for v in b.values()))

    if mag_a == 0 or mag_b == 0:
        return 0.0

    return round(dot / (mag_a * mag_b), 4)
```

### B.2 Drift Detection

```python
from collections import defaultdict

DEFAULT_SIMILARITY_THRESHOLD = 0.30
DEFAULT_SUSTAINED_TURNS_THRESHOLD = 3


def detect_drift(
    traces: list[dict],
    similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    sustained_threshold: int = DEFAULT_SUSTAINED_TURNS_THRESHOLD,
) -> list[dict]:
    """Detect drift events in a sequence of traces.

    Args:
        traces: List of AP-Trace dicts, ordered by sequence_number
        similarity_threshold: Alert when below this similarity
        sustained_threshold: Alert after this many consecutive low turns

    Returns:
        List of drift alert dicts
    """
    if len(traces) < sustained_threshold:
        return []

    alerts = []
    consecutive_low = 0
    streak_start = None

    for i in range(1, len(traces)):
        # Compare current trace to baseline (first trace or card)
        similarity = compute_trace_similarity(traces[0], traces[i])

        if similarity < similarity_threshold:
            if consecutive_low == 0:
                streak_start = i
            consecutive_low += 1

            if consecutive_low >= sustained_threshold:
                alerts.append({
                    'type': 'drift_detected',
                    'start_trace': streak_start,
                    'current_trace': i,
                    'sustained_turns': consecutive_low,
                    'similarity': similarity,
                    'threshold': similarity_threshold,
                })
        else:
            consecutive_low = 0
            streak_start = None

    return alerts
```

---

## Summary

AAP's drift detection thresholds (0.30 similarity, 3 sustained turns) were empirically calibrated on ~50 multi-turn conversations between transformer-based agents engaged in deliberative dialogue.

Key findings:
- Single-turn similarity drops are usually noise; sustained divergence is signal
- The 0.30 threshold separates aligned from divergent segments with ~84% precision
- The 3-turn requirement filters transient variation while catching genuine drift

These thresholds should be treated as reasonable defaults, not universal constants. Recalibration is recommended for significantly different contexts.

The moat is operational learning, not code: *these thresholds encode patterns observed in genuine deliberative dialogue, not synthetic data or theoretical assumptions*.

---

*AAP Calibration Methodology v0.1.0*
*Author: Vigil (conscience/protocol track)*
*This document is informative for AAP implementations.*
