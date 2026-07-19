"""Public API surface parity between the Python package and the TypeScript port.

``agent-alignment-protocol`` ships as two parallel SDKs — the Python package
(``src/aap``) and the TypeScript port (``typescript/``). Downstream users pick a
language and expect the *same* protocol surface: the same verification functions,
the same schema/result model names, and the same calibrated constants. This suite
is the guard that keeps the two public surfaces from silently drifting apart.

How it works
------------
Two independent tiers are checked, because the two languages expose the two kinds
of surface differently:

1. **Symbols** — the exported functions and model types. The Python surface is
   ``aap.__all__``; the TypeScript surface is parsed out of the ``export`` blocks
   in ``typescript/src/index.ts``. Names are compared through :func:`normalize`
   (lowercase + strip underscores) so that ``verify_trace`` (snake_case) matches
   ``verifyTrace`` (camelCase). Note that ``index.ts`` re-exports the constants via
   ``export * from "./constants"`` — a star export carries no names in the source
   text, so constants never appear in the symbol tier and are handled in tier 2.

2. **Constants** — the calibrated thresholds. Compared by their (upper-snake)
   names and by value, sourced from ``aap.verification.constants`` and
   ``typescript/src/constants.ts``.

Symbols/constants that intentionally exist on only one side are enumerated in the
allowlists below. Everything else must appear on both sides.

Updating the allowlists (discovery pattern)
-------------------------------------------
When a new one-sided symbol or constant is added, this suite fails with the exact
name(s) that are unaccounted for. To repopulate the allowlists, run::

    pytest tests/test_api_parity.py::test_no_unaccounted_oneside_symbols -v

and add each reported name to :data:`PY_ONLY_SYMBOLS` / :data:`TS_ONLY_SYMBOLS`
(or, for constants, to :data:`PY_ONLY_CONSTANTS` / :data:`TS_ONLY_CONSTANTS` /
:data:`CONSTANT_ALIASES`) with a short reason, OR add it to
:data:`CANONICAL_CORE_SYMBOLS` and export it from the other language too.

Dunder names (``__version__`` etc.) are never part of a published API surface, so
they are filtered out before the symbol surface is built (``__version__`` would
otherwise normalize to ``version`` and read as an unaccounted Python-only symbol).
"""

from __future__ import annotations

import re
from pathlib import Path

import aap
from aap.verification import constants as py_constants

# ---------------------------------------------------------------------------
# Locations
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[1]
_TS_INDEX = _REPO_ROOT / "typescript" / "src" / "index.ts"
_TS_CONSTANTS = _REPO_ROOT / "typescript" / "src" / "constants.ts"


# ---------------------------------------------------------------------------
# Canonical core — MUST be exported by BOTH languages
# ---------------------------------------------------------------------------
# Only functions and model/result types belong here — never calibration
# constants (those live in the constant-parity tier below).

CANONICAL_CORE_SYMBOLS: frozenset[str] = frozenset(
    {
        # Core verification API
        "verify_trace",
        "check_coherence",
        "check_fleet_coherence",
        "detect_drift",
        # Verification result models
        "VerificationResult",
        "Violation",
        "ViolationType",
        "Warning",
        "Severity",
        "VerificationMetadata",
        "CoherenceResult",
        "ValueAlignment",
        "ValueConflict",
        # Fleet coherence models (E-05)
        "FleetCoherenceResult",
        "PairwiseEntry",
        "FleetOutlier",
        "FleetCluster",
        "ValueDivergence",
        "AgentCoherenceSummary",
        # Drift models
        "DriftAlert",
        "DriftAnalysis",
        "DriftDirection",
        "DriftIndicator",
        # Alignment Card (unified / ADR-039)
        "AlignmentCard",
        "AlignmentMode",
        "Principal",
        "PrincipalType",
        "RelationshipType",
        "Values",
        "Autonomy",
        "EscalationTrigger",
        "TriggerAction",
        "Audit",
        # AP-Trace
        "APTrace",
        "Action",
        "ActionType",
        "ActionCategory",
        "Alternative",
        "Decision",
        "Escalation",
        "TraceContext",
        # Value coherence
        "AlignmentCardRequest",
        "AlignmentCardResponse",
        "ValueCoherenceCheck",
        "CoherenceResultMessage",
        "ProposedCollaboration",
        # EU AI Act compliance presets
        "EU_COMPLIANCE_AUDIT",
        "EU_COMPLIANCE_EXTENSIONS",
        "EU_COMPLIANCE_VALUES",
    }
)


# ---------------------------------------------------------------------------
# One-sided allowlists — symbols intentionally exported by only one language
# ---------------------------------------------------------------------------

# Python only: the runtime tracing decorators / trace-store helpers. The TS port
# is a pure verification library and ships no decorator-based instrumentation.
PY_ONLY_SYMBOLS: frozenset[str] = frozenset(
    {
        "trace_decision",
        "mcp_traced",
        "TracedResult",
        "TraceConfig",
        "TraceHandler",
        "AlignmentViolationError",
        "get_trace_store",
        "clear_trace_store",
    }
)

# TypeScript only: fault-line analysis (E-06), the governance-signal vocabulary
# (ADR-048), type-guard/utility helpers, and the extra structural sub-types that
# the TS type system names explicitly but Python folds into its Pydantic models.
TS_ONLY_SYMBOLS: frozenset[str] = frozenset(
    {
        # Fault line analysis (E-06) — TS-only feature
        "analyzeFaultLines",
        "checkFleetFaultLines",
        "FaultLineClassification",
        "FaultLine",
        "FaultLineSummary",
        "FaultLineAlignment",
        "FaultLineAnalysis",
        # Alignment-card structural sub-types
        "ValueDefinition",
        "HierarchyType",
        "MonetaryValue",
        "TamperEvidence",
        "ParameterizedValue",
        # AP-Trace structural sub-types
        "ActionTarget",
        "ValueScore",
        "EscalationStatus",
        "TriggerCheck",
        "PrincipalResponse",
        # Value-coherence structural sub-types
        "ValueCoherenceMessage",
        "RequesterInfo",
        "TaskContext",
        "Signature",
        "DataSharing",
        "AutonomyScope",
        "Coherence",
        "ValueAlignmentDetail",
        "ProposedResolution",
        # Result structural sub-types
        "VerificationRecommendation",
        "ValueConflictResult",
        # Type-guard / utility helpers (Python exposes these as methods)
        "isCardExpired",
        "hasValue",
        "isActionBounded",
        "isActionForbidden",
        "getSelectedAlternative",
        "wasEscalated",
        "hadViolations",
        "computeCentroid",
        "extractCardFeatures",
        "extractTraceFeatures",
        "cosineSimilarity",
        "createViolation",
        "VIOLATION_SEVERITY",
        # Governance signals (ADR-048) — operator-facing types + guards
        "GovernanceSignal",
        "GovernanceSignalScope",
        "GovernanceSignalSource",
        "GovernanceSignalSeverity",
        "GovernanceSignalStatus",
        "GovernanceActorRole",
        "GovernanceResolutionStatus",
        "GovernanceNotificationChannel",
        "GovernanceFleetPatternType",
        "GovernanceCoherencePatternType",
        "GovernanceSourceRef",
        "GovernanceFleetSourceRef",
        "GovernanceCoherenceSourceRef",
        "GovernanceFaultLineSourceRef",
        "GovernanceDriftSourceRef",
        "GovernanceSourceRefBase",
        "GovernanceNotificationDispatchState",
        "GovernanceNotificationChannelState",
        "GovernanceNotificationState",
        "GovernanceWebhookEventType",
        "GovernanceWebhookEnvelope",
        "isFleetSignal",
        "isCoherenceSignal",
        "isFaultLineSignal",
        "isDriftSignal",
        "severityAtLeast",
        "SEVERITY_ORDER",
    }
)


# ---------------------------------------------------------------------------
# Constant parity
# ---------------------------------------------------------------------------
# CONSTANT_ALIASES maps a renamed constant across languages.
#   key   = Python name (upper-snake)
#   value = TypeScript name (upper-snake)
# The direction matters: the parity logic below keys lookups by Python name, so
# reversing this dict silently breaks the check. The assertion guards the shape.
CONSTANT_ALIASES: dict[str, str] = {
    # Python calls it "turns"; the TS port calls it "checks". Same threshold.
    "DEFAULT_SUSTAINED_TURNS_THRESHOLD": "DEFAULT_SUSTAINED_CHECKS_THRESHOLD",
}
assert all(k.upper() == k and v.upper() == v for k, v in CONSTANT_ALIASES.items()), (
    "CONSTANT_ALIASES must be keyed by Python name -> TS name, both upper-snake"
)

# Constants intentionally present on only one side.
# Python only: the char-n-gram + TF-IDF weighting knobs. The TS similarity model
# is word-TF-IDF only, so it has no char/metadata-weighting constants.
PY_ONLY_CONSTANTS: frozenset[str] = frozenset(
    {
        "MAX_CHAR_FEATURES",
        "TFIDF_WORD_WEIGHT",
        "TFIDF_CHAR_WEIGHT",
        "TFIDF_META_WEIGHT",
    }
)
# TypeScript only: none today.
TS_ONLY_CONSTANTS: frozenset[str] = frozenset()


# ---------------------------------------------------------------------------
# Surface extraction
# ---------------------------------------------------------------------------


def normalize(name: str) -> str:
    """Fold a symbol name to a language-agnostic key: lowercase, no underscores.

    ``verify_trace`` (Python) and ``verifyTrace`` (TS) both fold to ``verifytrace``.
    """
    return name.replace("_", "").lower()


def _strip_ts_comments(source: str) -> str:
    """Remove ``/* ... */`` block comments and ``// ...`` line comments."""
    source = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    source = re.sub(r"//[^\n]*", "", source)
    return source


def _python_surface() -> set[str]:
    """Public Python symbols from ``aap.__all__``, excluding dunder names."""
    return {name for name in aap.__all__ if not name.startswith("__")}


def _typescript_surface() -> set[str]:
    """Exported symbol names parsed from ``typescript/src/index.ts``.

    Parses ``export { ... }`` and ``export type { ... }`` blocks (multiline
    aware). ``export * from "./constants"`` carries no names in the source text
    and is therefore excluded — constants are checked in the constant tier.
    """
    source = _strip_ts_comments(_TS_INDEX.read_text(encoding="utf-8"))
    names: set[str] = set()
    for block in re.findall(r"export\s+(?:type\s+)?\{(.*?)\}", source, flags=re.DOTALL):
        for entry in block.split(","):
            entry = entry.strip()
            if not entry:
                continue
            # Handle a possible `Foo as Bar` re-export by taking the exported name.
            token = entry.split()[-1]
            match = re.match(r"[A-Za-z_$][\w$]*", token)
            if match:
                names.add(match.group(0))
    return names


def _python_constants() -> dict[str, object]:
    """Upper-snake module constants from ``aap.verification.constants``."""
    return {
        name: getattr(py_constants, name)
        for name in dir(py_constants)
        if name.isupper() and not name.startswith("_")
    }


def _typescript_constants() -> dict[str, str]:
    """``NAME -> raw literal`` from ``export const`` lines in ``constants.ts``."""
    source = _strip_ts_comments(_TS_CONSTANTS.read_text(encoding="utf-8"))
    constants: dict[str, str] = {}
    for name, literal in re.findall(
        r"export\s+const\s+([A-Za-z_$][\w$]*)\s*=\s*([^;]+);", source
    ):
        constants[name] = literal.strip()
    return constants


def _values_equal(py_value: object, ts_literal: str) -> bool:
    """Compare a Python constant value against a raw TS literal token."""
    try:
        return float(py_value) == float(ts_literal)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return str(py_value) == ts_literal.strip("\"'")


# ---------------------------------------------------------------------------
# Sanity: the fixtures parse to something non-trivial
# ---------------------------------------------------------------------------


def test_surface_extraction_is_non_empty() -> None:
    """Guard against a parser regression silently emptying a surface."""
    assert _TS_INDEX.is_file(), f"missing {_TS_INDEX}"
    assert _TS_CONSTANTS.is_file(), f"missing {_TS_CONSTANTS}"
    assert _python_surface(), "Python surface (aap.__all__) is empty"
    assert _typescript_surface(), "TypeScript surface (index.ts) is empty"
    assert _python_constants(), "Python constants are empty"
    assert _typescript_constants(), "TypeScript constants are empty"


# ---------------------------------------------------------------------------
# Symbol parity
# ---------------------------------------------------------------------------


def test_canonical_core_symbols_present_in_both_surfaces() -> None:
    """Every canonical core symbol is exported by BOTH languages."""
    py_norm = {normalize(n) for n in _python_surface()}
    ts_norm = {normalize(n) for n in _typescript_surface()}
    for symbol in sorted(CANONICAL_CORE_SYMBOLS):
        key = normalize(symbol)
        assert key in py_norm, f"canonical core symbol {symbol!r} missing from Python surface"
        assert key in ts_norm, f"canonical core symbol {symbol!r} missing from TypeScript surface"


def test_canonical_core_symbols_not_also_in_oneside_allowlists() -> None:
    """A symbol is either canonical-core or one-sided — never both."""
    core = {normalize(n) for n in CANONICAL_CORE_SYMBOLS}
    py_only = {normalize(n) for n in PY_ONLY_SYMBOLS}
    ts_only = {normalize(n) for n in TS_ONLY_SYMBOLS}
    assert not (core & py_only), f"core symbols mislabeled Python-only: {core & py_only}"
    assert not (core & ts_only), f"core symbols mislabeled TS-only: {core & ts_only}"


def test_no_unaccounted_oneside_symbols() -> None:
    """Any symbol on only one side must be in that side's allowlist.

    This is the drift guard: adding an export to one language without either
    exporting it from the other or allowlisting it here fails this test with the
    offending name(s). See the module docstring for how to repopulate the lists.
    """
    py_norm = {normalize(n) for n in _python_surface()}
    ts_norm = {normalize(n) for n in _typescript_surface()}

    py_only_actual = py_norm - ts_norm
    ts_only_actual = ts_norm - py_norm

    py_only_allowed = {normalize(n) for n in PY_ONLY_SYMBOLS}
    ts_only_allowed = {normalize(n) for n in TS_ONLY_SYMBOLS}

    unaccounted_py = py_only_actual - py_only_allowed - {normalize(n) for n in CANONICAL_CORE_SYMBOLS}
    unaccounted_ts = ts_only_actual - ts_only_allowed - {normalize(n) for n in CANONICAL_CORE_SYMBOLS}

    assert not unaccounted_py, (
        f"Python-only symbols not in PY_ONLY_SYMBOLS: {sorted(unaccounted_py)}"
    )
    assert not unaccounted_ts, (
        f"TypeScript-only symbols not in TS_ONLY_SYMBOLS: {sorted(unaccounted_ts)}"
    )


# ---------------------------------------------------------------------------
# Constant parity
# ---------------------------------------------------------------------------


def test_constant_alias_convention() -> None:
    """Aliases are keyed by real Python names and point at real TS names."""
    py_names = set(_python_constants())
    ts_names = set(_typescript_constants())
    for py_name, ts_name in CONSTANT_ALIASES.items():
        assert py_name in py_names, f"alias key {py_name!r} is not a Python constant"
        assert ts_name in ts_names, f"alias value {ts_name!r} is not a TypeScript constant"


def test_no_unaccounted_oneside_constants() -> None:
    """Constants present on only one side must be aliased or allowlisted."""
    py_names = set(_python_constants())
    ts_names = set(_typescript_constants())

    py_only_actual = py_names - ts_names - set(CONSTANT_ALIASES)
    ts_only_actual = ts_names - py_names - set(CONSTANT_ALIASES.values())

    unaccounted_py = py_only_actual - PY_ONLY_CONSTANTS
    unaccounted_ts = ts_only_actual - TS_ONLY_CONSTANTS

    assert not unaccounted_py, (
        f"Python-only constants not in PY_ONLY_CONSTANTS: {sorted(unaccounted_py)}"
    )
    assert not unaccounted_ts, (
        f"TypeScript-only constants not in TS_ONLY_CONSTANTS: {sorted(unaccounted_ts)}"
    )


def test_shared_constant_values_match() -> None:
    """Constants shared across languages (directly or via alias) have equal values."""
    py_constants_map = _python_constants()
    ts_constants_map = _typescript_constants()

    checked = 0
    for py_name, py_value in py_constants_map.items():
        ts_name = CONSTANT_ALIASES.get(py_name, py_name)
        if ts_name not in ts_constants_map:
            continue
        ts_literal = ts_constants_map[ts_name]
        assert _values_equal(py_value, ts_literal), (
            f"constant value mismatch: {py_name}={py_value!r} (py) "
            f"vs {ts_name}={ts_literal!r} (ts)"
        )
        checked += 1

    # The shared set must not be empty, or a parser regression could make this
    # test vacuously pass.
    assert checked, "no shared constants were compared — check the constant parsers"
