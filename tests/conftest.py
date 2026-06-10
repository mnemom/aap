"""Shared test fixtures for AAP test suite.

These fixtures create canonical examples of Alignment Cards, AP-Traces, and
related structures for use across all tests. They follow the specification
exactly and serve as reference implementations.

Design principles:
- Every fixture should be a valid, minimal example
- Fixtures compose — complex cases build from simple ones
- Fixtures document the schema through usage
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Alignment Card Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def minimal_principal() -> dict[str, Any]:
    """Minimal valid principal declaration (identifier required when typed)."""
    return {
        "type": "human",
        "identifier": "did:web:user.example.com",
        "relationship": "delegated_authority",
    }


@pytest.fixture
def full_principal() -> dict[str, Any]:
    """Fully-specified principal declaration."""
    return {
        "type": "human",
        "identifier": "did:web:user.example.com",
        "relationship": "delegated_authority",
        "escalation_contact": "mailto:user@example.com",
    }


@pytest.fixture
def minimal_values() -> dict[str, Any]:
    """Minimal valid values declaration using standard values."""
    return {
        "declared": ["principal_benefit", "transparency"],
    }


@pytest.fixture
def values_with_conflicts() -> dict[str, Any]:
    """Values declaration with conflicts_with."""
    return {
        "declared": ["principal_benefit", "transparency", "minimal_data"],
        "conflicts_with": ["profit_maximization", "comprehensive_analytics"],
        "hierarchy": "lexicographic",
    }


@pytest.fixture
def values_with_custom() -> dict[str, Any]:
    """Values declaration with custom value definitions."""
    return {
        "declared": ["principal_benefit", "sustainability"],
        "definitions": {
            "sustainability": {
                "name": "Environmental Sustainability",
                "description": "Prefer options that minimize environmental impact",
                "priority": 3,
            }
        },
        "hierarchy": "lexicographic",
    }


@pytest.fixture
def minimal_autonomy() -> dict[str, Any]:
    """Minimal valid autonomy section (unified / ADR-039)."""
    return {
        "bounded_actions": ["search", "recommend", "summarize"],
        "escalation_triggers": [
            {
                "condition": 'action_type == "purchase"',
                "action": "escalate",
                "reason": "Purchases require principal approval",
            }
        ],
    }


@pytest.fixture
def full_autonomy() -> dict[str, Any]:
    """Fully-specified autonomy section (unified / ADR-039)."""
    return {
        "bounded_actions": ["search", "recommend", "summarize", "draft_email"],
        "escalation_triggers": [
            {
                "condition": 'action_type == "purchase"',
                "action": "escalate",
                "reason": "Purchases require principal approval",
            },
            {
                "condition": "amount > 100",
                "action": "escalate",
                "reason": "High-value transactions require approval",
            },
            {
                "condition": "shares_personal_data",
                "action": "deny",
                "reason": "Never share personal data",
            },
        ],
        "max_autonomous_value": {
            "amount": 50.0,
            "currency": "USD",
        },
        "forbidden_actions": ["delete_data", "modify_permissions", "send_payment"],
    }


@pytest.fixture
def minimal_audit() -> dict[str, Any]:
    """Minimal valid audit section (unified / ADR-039)."""
    return {
        "retention_days": 90,
        "queryable": False,
    }


@pytest.fixture
def full_audit() -> dict[str, Any]:
    """Fully-specified audit section (unified / ADR-039)."""
    return {
        "trace_format": "ap-trace-v1",
        "retention_days": 365,
        "queryable": True,
        "query_endpoint": "https://agent.example.com/api/traces",
        "tamper_evidence": "merkle",
    }


@pytest.fixture
def minimal_alignment_card(
    minimal_principal: dict,
    minimal_values: dict,
    minimal_autonomy: dict,
    minimal_audit: dict,
) -> dict[str, Any]:
    """Minimal valid Alignment Card (unified / ADR-039)."""
    return {
        "card_version": "unified/2026-04-26",
        "card_id": "ac-minimal-001",
        "agent_id": "agent-minimal-001",
        "issued_at": datetime.now(timezone.utc).isoformat(),
        "autonomy_mode": "observe",
        "integrity_mode": "observe",
        "principal": minimal_principal,
        "values": minimal_values,
        "autonomy": minimal_autonomy,
        "audit": minimal_audit,
    }


@pytest.fixture
def full_alignment_card(
    full_principal: dict,
    values_with_conflicts: dict,
    full_autonomy: dict,
    full_audit: dict,
) -> dict[str, Any]:
    """Fully-specified Alignment Card (unified / ADR-039)."""
    return {
        "card_version": "unified/2026-04-26",
        "card_id": "ac-full-001",
        "agent_id": "did:web:agent.example.com",
        "issued_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=365)).isoformat(),
        "autonomy_mode": "enforce",
        "integrity_mode": "enforce",
        "principal": full_principal,
        "values": values_with_conflicts,
        "autonomy": full_autonomy,
        "audit": full_audit,
        "extensions": {
            "a2a": {
                "skills": ["search", "recommend"],
            }
        },
    }


@pytest.fixture
def expired_alignment_card(minimal_alignment_card: dict) -> dict[str, Any]:
    """Alignment Card that has expired."""
    card = minimal_alignment_card.copy()
    card["card_id"] = "ac-expired-001"
    card["expires_at"] = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    return card


# ---------------------------------------------------------------------------
# AP-Trace Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def minimal_action() -> dict[str, Any]:
    """Minimal valid action — must be in bounded_actions list."""
    return {
        "type": "recommend",
        "name": "recommend",  # Must match bounded_actions
        "category": "bounded",
    }


@pytest.fixture
def bounded_action() -> dict[str, Any]:
    """Action within bounded_actions."""
    return {
        "type": "execute",
        "name": "search",
        "category": "bounded",
        "parameters": {"query": "best products 2026"},
    }


@pytest.fixture
def forbidden_action() -> dict[str, Any]:
    """Action in forbidden_actions list."""
    return {
        "type": "execute",
        "name": "delete_data",
        "category": "forbidden",
        "target": {
            "type": "database",
            "identifier": "user-records",
        },
    }


@pytest.fixture
def escalation_trigger_action() -> dict[str, Any]:
    """Action that triggers escalation."""
    return {
        "type": "execute",
        "name": "purchase",
        "category": "escalation_trigger",
        "parameters": {
            "item": "premium-subscription",
            "amount": 299.99,
        },
    }


@pytest.fixture
def minimal_decision() -> dict[str, Any]:
    """Minimal valid decision."""
    return {
        "alternatives_considered": [
            {
                "option_id": "A",
                "description": "Recommend product A",
                "score": 0.85,
            },
            {
                "option_id": "B",
                "description": "Recommend product B",
                "score": 0.72,
            },
        ],
        "selected": "A",
        "selection_reasoning": "Product A has highest alignment with principal benefit.",
        "values_applied": ["principal_benefit"],
    }


@pytest.fixture
def decision_with_low_confidence() -> dict[str, Any]:
    """Decision with low confidence (near boundary)."""
    return {
        "alternatives_considered": [
            {
                "option_id": "X",
                "description": "Option X",
                "score": 0.51,
            },
            {
                "option_id": "Y",
                "description": "Option Y",
                "score": 0.49,
            },
        ],
        "selected": "X",
        "selection_reasoning": "Marginal preference for X, but close call.",
        "values_applied": ["principal_benefit"],
        "confidence": 0.25,  # Below NEAR_BOUNDARY_THRESHOLD (0.35)
    }


@pytest.fixture
def decision_with_undeclared_value() -> dict[str, Any]:
    """Decision applying an undeclared value."""
    return {
        "alternatives_considered": [
            {
                "option_id": "A",
                "description": "Option A",
                "score": 0.9,
            },
        ],
        "selected": "A",
        "selection_reasoning": "Maximizes revenue for vendor.",
        "values_applied": [
            "principal_benefit",
            "profit_maximization",
        ],  # profit_maximization is not declared
    }


@pytest.fixture
def minimal_escalation_not_required() -> dict[str, Any]:
    """Escalation evaluation where escalation was not required."""
    return {
        "evaluated": True,
        "required": False,
        "reason": "No escalation triggers matched",
    }


@pytest.fixture
def escalation_required() -> dict[str, Any]:
    """Escalation evaluation where escalation was required and approved."""
    return {
        "evaluated": True,
        "triggers_checked": [
            {
                "trigger": 'action_type == "purchase"',
                "matched": True,
                "value_observed": "purchase",
            }
        ],
        "required": True,
        "reason": "Purchase action requires principal approval",
        "escalation_id": "esc-001",
        "escalation_status": "approved",
        "principal_response": {
            "decision": "Approved for amounts under $500",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "conditions": ["Amount must be under $500"],
        },
    }


@pytest.fixture
def escalation_timeout() -> dict[str, Any]:
    """Escalation that timed out."""
    return {
        "evaluated": True,
        "triggers_checked": [
            {
                "trigger": "amount > 100",
                "matched": True,
                "value_observed": 250.0,
            }
        ],
        "required": True,
        "reason": "High-value transaction requires approval",
        "escalation_id": "esc-timeout-001",
        "escalation_status": "timeout",
    }


@pytest.fixture
def minimal_trace(
    minimal_alignment_card: dict,
    minimal_action: dict,
    minimal_decision: dict,
    minimal_escalation_not_required: dict,
) -> dict[str, Any]:
    """Minimal valid AP-Trace that passes verification."""
    return {
        "trace_id": "tr-minimal-001",
        "agent_id": "agent-minimal-001",
        "card_id": minimal_alignment_card["card_id"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": minimal_action,
        "decision": minimal_decision,
        "escalation": minimal_escalation_not_required,
    }


@pytest.fixture
def trace_with_forbidden_action(
    minimal_alignment_card: dict,
    forbidden_action: dict,
    minimal_decision: dict,
) -> dict[str, Any]:
    """Trace with a forbidden action — should fail verification."""
    return {
        "trace_id": "tr-forbidden-001",
        "agent_id": "agent-minimal-001",
        "card_id": minimal_alignment_card["card_id"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": forbidden_action,
        "decision": minimal_decision,
        "escalation": {
            "evaluated": True,
            "required": False,
            "reason": "Action is forbidden",
        },
    }


@pytest.fixture
def trace_with_undeclared_value(
    minimal_alignment_card: dict,
    minimal_action: dict,
    decision_with_undeclared_value: dict,
) -> dict[str, Any]:
    """Trace applying undeclared value — should fail verification."""
    return {
        "trace_id": "tr-undeclared-001",
        "agent_id": "agent-minimal-001",
        "card_id": minimal_alignment_card["card_id"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": minimal_action,
        "decision": decision_with_undeclared_value,
        "escalation": {
            "evaluated": True,
            "required": False,
            "reason": "No triggers matched",
        },
    }


@pytest.fixture
def trace_card_mismatch(minimal_action: dict, minimal_decision: dict) -> dict[str, Any]:
    """Trace referencing a different card — should fail verification."""
    return {
        "trace_id": "tr-mismatch-001",
        "agent_id": "agent-minimal-001",
        "card_id": "ac-different-card",  # Does not match the card used in verification
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": minimal_action,
        "decision": minimal_decision,
        "escalation": {
            "evaluated": True,
            "required": False,
            "reason": "No triggers matched",
        },
    }


# ---------------------------------------------------------------------------
# Coherence Check Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def compatible_cards() -> tuple[dict[str, Any], dict[str, Any]]:
    """Two cards with compatible values."""
    card_a = {
        "card_id": "ac-a-001",
        "values": {
            "declared": ["principal_benefit", "transparency", "harm_prevention"],
        },
    }
    card_b = {
        "card_id": "ac-b-001",
        "values": {
            "declared": ["principal_benefit", "transparency", "user_control"],
        },
    }
    return card_a, card_b


@pytest.fixture
def conflicting_cards() -> tuple[dict[str, Any], dict[str, Any]]:
    """Two cards with conflicting values."""
    card_a = {
        "card_id": "ac-conflict-a",
        "values": {
            "declared": ["minimal_data", "privacy"],
            "conflicts_with": ["comprehensive_analytics"],
        },
    }
    card_b = {
        "card_id": "ac-conflict-b",
        "values": {
            "declared": ["comprehensive_analytics", "data_driven"],
            "conflicts_with": ["minimal_data"],
        },
    }
    return card_a, card_b


@pytest.fixture
def partially_compatible_cards() -> tuple[dict[str, Any], dict[str, Any]]:
    """Two cards with some overlap but also some differences."""
    card_a = {
        "card_id": "ac-partial-a",
        "values": {
            "declared": ["principal_benefit", "transparency", "minimal_data"],
        },
    }
    card_b = {
        "card_id": "ac-partial-b",
        "values": {
            "declared": ["principal_benefit", "user_control", "fairness"],
        },
    }
    return card_a, card_b


# ---------------------------------------------------------------------------
# Drift Detection Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def aligned_trace_sequence(minimal_alignment_card: dict) -> list[dict[str, Any]]:
    """Sequence of traces that remain aligned — should NOT trigger drift alert."""
    base_time = datetime.now(timezone.utc)
    traces = []

    for i in range(12):
        traces.append(
            {
                "trace_id": f"tr-aligned-{i:03d}",
                "agent_id": "agent-minimal-001",
                "card_id": minimal_alignment_card["card_id"],
                "timestamp": (base_time + timedelta(minutes=i)).isoformat(),
                "action": {
                    "type": "recommend",
                    "name": "search",  # In bounded_actions
                    "category": "bounded",
                },
                "decision": {
                    "alternatives_considered": [
                        {"option_id": "A", "description": "Option A", "score": 0.8},
                    ],
                    "selected": "A",
                    "selection_reasoning": "Best match for principal benefit",
                    "values_applied": ["principal_benefit", "transparency"],  # Declared values
                },
                "escalation": {
                    "evaluated": True,
                    "required": False,
                    "reason": "No triggers matched",
                },
            }
        )

    return traces


@pytest.fixture
def drifting_trace_sequence(minimal_alignment_card: dict) -> list[dict[str, Any]]:
    """Sequence of traces that drift from declared alignment — should trigger drift alert."""
    base_time = datetime.now(timezone.utc)
    traces = []

    # First 6 traces are aligned (establishes baseline for centroid computation)
    for i in range(6):
        traces.append(
            {
                "trace_id": f"tr-drift-{i:03d}",
                "agent_id": "agent-drifting-001",
                "card_id": minimal_alignment_card["card_id"],
                "timestamp": (base_time + timedelta(minutes=i)).isoformat(),
                "action": {
                    "type": "recommend",
                    "name": "search",
                    "category": "bounded",
                },
                "decision": {
                    "alternatives_considered": [
                        {"option_id": "A", "description": "Option A", "score": 0.8},
                    ],
                    "selected": "A",
                    "selection_reasoning": "Aligned with principal benefit",
                    "values_applied": ["principal_benefit"],
                },
                "escalation": {
                    "evaluated": True,
                    "required": False,
                    "reason": "No triggers matched",
                },
            }
        )

    # Next 6 traces show drift — using undeclared values, different action types and categories
    for i in range(6, 12):
        traces.append(
            {
                "trace_id": f"tr-drift-{i:03d}",
                "agent_id": "agent-drifting-001",
                "card_id": minimal_alignment_card["card_id"],
                "timestamp": (base_time + timedelta(minutes=i)).isoformat(),
                "action": {
                    "type": "execute",
                    "name": "monetize",  # Not in bounded_actions
                    "category": "forbidden",  # Different category from baseline
                },
                "decision": {
                    "alternatives_considered": [
                        {"option_id": "M", "description": "Monetize", "score": 0.95},
                    ],
                    "selected": "M",
                    "selection_reasoning": "Maximize vendor revenue through targeted ads",
                    "values_applied": ["profit_maximization", "engagement"],  # Undeclared values
                    "confidence": 0.2,  # Low confidence
                },
                "escalation": {
                    "evaluated": True,
                    "required": True,  # Different from baseline (not_required)
                    "reason": "Skipped evaluation",
                },
            }
        )

    return traces


@pytest.fixture
def autonomy_expansion_sequence(minimal_alignment_card: dict) -> list[dict[str, Any]]:
    """Sequence showing autonomy expansion — escalation rate declining."""
    base_time = datetime.now(timezone.utc)
    traces = []

    # First 6 traces: high escalation rate (establishes baseline)
    for i in range(6):
        traces.append(
            {
                "trace_id": f"tr-autonomy-{i:03d}",
                "agent_id": "agent-expanding-001",
                "card_id": minimal_alignment_card["card_id"],
                "timestamp": (base_time + timedelta(minutes=i)).isoformat(),
                "action": {
                    "type": "execute",
                    "name": "purchase",
                    "category": "escalation_trigger",
                },
                "decision": {
                    "alternatives_considered": [
                        {"option_id": "P", "description": "Purchase", "score": 0.7},
                    ],
                    "selected": "P",
                    "selection_reasoning": "User requested purchase",
                    "values_applied": ["principal_benefit"],
                },
                "escalation": {
                    "evaluated": True,
                    "required": True,  # Properly escalating
                    "reason": "Purchase requires approval",
                    "escalation_status": "approved",
                },
            }
        )

    # Next 6 traces: autonomy expansion — completely different behavior pattern
    for i in range(6, 12):
        traces.append(
            {
                "trace_id": f"tr-autonomy-{i:03d}",
                "agent_id": "agent-expanding-001",
                "card_id": minimal_alignment_card["card_id"],
                "timestamp": (base_time + timedelta(minutes=i)).isoformat(),
                "action": {
                    "type": "deny",  # Different action type from baseline
                    "name": "monetize",  # Different action name from baseline
                    "category": "forbidden",  # Different category from baseline
                },
                "decision": {
                    "alternatives_considered": [
                        {"option_id": "P", "description": "Purchase", "score": 0.9},
                    ],
                    "selected": "P",
                    "selection_reasoning": "Proceeding without approval — user trusts me",
                    "values_applied": [
                        "efficiency",
                        "speed",
                    ],  # Undeclared values, different from baseline
                },
                "escalation": {
                    "evaluated": False,  # Different from baseline
                    "required": False,  # NOT escalating when should!
                    "reason": "I know what user wants",
                },
            }
        )

    return traces
