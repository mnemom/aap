"""EU AI Act Article 50 compliance presets for AAP.

These presets provide recommended configuration values for deploying
AAP-instrumented agents in EU jurisdictions subject to AI Act
transparency obligations. Spread them into your AlignmentCard fields.

Usage:
    from aap.compliance import (
        EU_COMPLIANCE_AUDIT,
        EU_COMPLIANCE_EXTENSIONS,
        EU_COMPLIANCE_VALUES,
    )

    card = AlignmentCard(
        ...,
        audit=Audit(**EU_COMPLIANCE_AUDIT),
        values=Values(declared=EU_COMPLIANCE_VALUES, ...),
        extensions=EU_COMPLIANCE_EXTENSIONS,
    )

DISCLAIMER: These presets reflect a technical mapping of AAP features to
Article 50 requirements. They do not constitute legal advice. Consult
qualified legal counsel for your specific compliance obligations.
"""

from __future__ import annotations

from typing import Any

# Audit commitment values that satisfy Article 50(4) audit trail requirements.
# Spread into the unified card's `audit` section (Audit(**EU_COMPLIANCE_AUDIT)).
EU_COMPLIANCE_AUDIT: dict[str, Any] = {
    "retention_days": 90,
    "queryable": True,
    "query_endpoint": "https://audit.example.com/traces",
    "tamper_evidence": "append_only",
    "trace_format": "ap-trace-v1",
}

# Extension block for EU AI Act metadata on the Alignment Card.
EU_COMPLIANCE_EXTENSIONS: dict[str, Any] = {
    "eu_ai_act": {
        "article_50_compliant": True,
        "ai_system_classification": "general_purpose",
        "disclosure_text": (
            "This system is powered by an AI agent. Its decisions are logged "
            "and auditable. You may request a human review of any decision."
        ),
        "compliance_version": "2026-08",
    },
}

# Recommended declared values for Article 50 transparency obligations.
EU_COMPLIANCE_VALUES: list[str] = [
    "transparency",
    "honesty",
    "user_control",
    "principal_benefit",
]
