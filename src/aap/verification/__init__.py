"""AAP Verification Module — Verify traces, check coherence, detect drift.

This module provides the three core verification functions specified in
the Agent Alignment Protocol:

- verify_trace: Verify a single AP-Trace against an Alignment Card
- check_coherence: Check value coherence between two Alignment Cards
- detect_drift: Detect behavioral drift from declared alignment over time

Example usage:

    from aap.verification import verify_trace, check_coherence, detect_drift

    # Verify a single trace
    result = verify_trace(trace, card)
    if not result.verified:
        for violation in result.violations:
            print(f"VIOLATION: {violation.type} - {violation.description}")

    # Check coherence between two agents
    coherence = check_coherence(my_card, their_card)
    if coherence.proceed:
        # Safe to coordinate
        pass
    else:
        # Handle conflicts
        print(f"Conflicts: {coherence.value_alignment.conflicts}")

    # Detect drift over time
    alerts = detect_drift(card, traces)
    for alert in alerts:
        print(f"DRIFT: {alert.analysis.drift_direction}")

See SPEC.md Sections 7, 6.4, and 8 for protocol specification.
"""

from aap.verification.api import (
    check_coherence,
    check_fleet_coherence,
    detect_drift,
    verify_trace,
)
from aap.verification.constants import (
    ALGORITHM_VERSION,
    DEFAULT_SIMILARITY_THRESHOLD,
    DEFAULT_SUSTAINED_TURNS_THRESHOLD,
    MIN_COHERENCE_FOR_PROCEED,
    NEAR_BOUNDARY_THRESHOLD,
)
from aap.verification.divergence import (
    DivergenceDetector,
    detect_divergence,
)
from aap.verification.features import (
    FeatureExtractor,
    compute_centroid,
    compute_similarity_with_tfidf,
    cosine_similarity,
)
from aap.verification.models import (
    AgentCoherenceSummary,
    CoherenceResult,
    DriftAlert,
    DriftAnalysis,
    DriftDirection,
    DriftIndicator,
    FleetCluster,
    FleetCoherenceResult,
    FleetOutlier,
    PairwiseEntry,
    Severity,
    ValueAlignment,
    ValueConflict,
    ValueDivergence,
    VerificationMetadata,
    VerificationResult,
    Violation,
    ViolationType,
    Warning,
)
from aap.verification.ssm import (
    SSMAnalyzer,
    compute_trace_card_similarity,
)

__all__ = [
    # Core functions
    "verify_trace",
    "check_coherence",
    "check_fleet_coherence",
    "detect_drift",
    # SSM and Divergence (Phase 1 Braid extraction)
    "SSMAnalyzer",
    "compute_trace_card_similarity",
    "DivergenceDetector",
    "detect_divergence",
    # Feature extraction
    "FeatureExtractor",
    "compute_centroid",
    "cosine_similarity",
    "compute_similarity_with_tfidf",
    # Fleet Coherence (E-05)
    "FleetCoherenceResult",
    "PairwiseEntry",
    "FleetOutlier",
    "FleetCluster",
    "ValueDivergence",
    "AgentCoherenceSummary",
    # Result models
    "VerificationResult",
    "Violation",
    "ViolationType",
    "Warning",
    "Severity",
    "VerificationMetadata",
    "CoherenceResult",
    "ValueAlignment",
    "ValueConflict",
    "DriftAlert",
    "DriftAnalysis",
    "DriftDirection",
    "DriftIndicator",
    # Constants
    "ALGORITHM_VERSION",
    "DEFAULT_SIMILARITY_THRESHOLD",
    "DEFAULT_SUSTAINED_TURNS_THRESHOLD",
    "MIN_COHERENCE_FOR_PROCEED",
    "NEAR_BOUNDARY_THRESHOLD",
]
