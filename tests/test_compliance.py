"""Tests for EU AI Act Article 50 compliance presets."""

from __future__ import annotations

from aap.compliance import (
    EU_COMPLIANCE_AUDIT,
    EU_COMPLIANCE_EXTENSIONS,
    EU_COMPLIANCE_VALUES,
)
from aap.schemas import AlignmentCard, Audit, Autonomy, Principal, Values

# Standard AAP values that the presets should draw from
STANDARD_VALUES = {
    "principal_benefit",
    "transparency",
    "minimal_data",
    "harm_prevention",
    "honesty",
    "user_control",
    "privacy",
    "fairness",
}


class TestEUComplianceAudit:
    """Tests for EU_COMPLIANCE_AUDIT preset."""

    def test_retention_at_least_90_days(self):
        assert EU_COMPLIANCE_AUDIT["retention_days"] >= 90

    def test_queryable_is_true(self):
        assert EU_COMPLIANCE_AUDIT["queryable"] is True

    def test_tamper_evidence_set(self):
        assert EU_COMPLIANCE_AUDIT["tamper_evidence"] in {
            "append_only",
            "signed",
            "merkle",
        }

    def test_trace_format_set(self):
        assert EU_COMPLIANCE_AUDIT["trace_format"] == "ap-trace-v1"

    def test_produces_valid_audit(self):
        """Preset values produce a valid Audit model."""
        commitment = Audit(**EU_COMPLIANCE_AUDIT)
        assert commitment.retention_days == 90
        assert commitment.queryable is True
        assert commitment.tamper_evidence == "append_only"


class TestEUComplianceExtensions:
    """Tests for EU_COMPLIANCE_EXTENSIONS preset."""

    def test_has_eu_ai_act_key(self):
        assert "eu_ai_act" in EU_COMPLIANCE_EXTENSIONS

    def test_article_50_compliant_flag(self):
        assert EU_COMPLIANCE_EXTENSIONS["eu_ai_act"]["article_50_compliant"] is True

    def test_disclosure_text_present(self):
        text = EU_COMPLIANCE_EXTENSIONS["eu_ai_act"]["disclosure_text"]
        assert isinstance(text, str)
        assert len(text) > 0

    def test_classification_present(self):
        assert "ai_system_classification" in EU_COMPLIANCE_EXTENSIONS["eu_ai_act"]

    def test_compliance_version_present(self):
        assert "compliance_version" in EU_COMPLIANCE_EXTENSIONS["eu_ai_act"]


class TestEUComplianceValues:
    """Tests for EU_COMPLIANCE_VALUES preset."""

    def test_values_are_standard(self):
        """All EU compliance values should be from the standard AAP value set."""
        for value in EU_COMPLIANCE_VALUES:
            assert value in STANDARD_VALUES, f"{value} is not a standard AAP value"

    def test_transparency_included(self):
        assert "transparency" in EU_COMPLIANCE_VALUES

    def test_honesty_included(self):
        assert "honesty" in EU_COMPLIANCE_VALUES

    def test_user_control_included(self):
        assert "user_control" in EU_COMPLIANCE_VALUES

    def test_at_least_three_values(self):
        assert len(EU_COMPLIANCE_VALUES) >= 3


class TestPresetsProduceValidCard:
    """Integration test: presets produce a valid AlignmentCard."""

    def test_full_card_with_presets(self):
        card = AlignmentCard(
            card_version="unified/2026-04-26",
            card_id="ac-test-eu-001",
            agent_id="test-eu-agent",
            issued_at="2026-02-13T00:00:00Z",
            autonomy_mode="enforce",
            integrity_mode="enforce",
            principal=Principal(
                type="organization",
                identifier="Example Corp (EU)",
                relationship="delegated_authority",
            ),
            values=Values(
                declared=list(EU_COMPLIANCE_VALUES),
            ),
            autonomy=Autonomy(
                bounded_actions=["search", "recommend"],
                escalation_triggers=[],
            ),
            audit=Audit(**EU_COMPLIANCE_AUDIT),
            extensions=EU_COMPLIANCE_EXTENSIONS,
        )
        dumped = card.model_dump(mode="json")

        assert dumped["audit"]["retention_days"] == 90
        assert dumped["audit"]["queryable"] is True
        assert dumped["extensions"]["eu_ai_act"]["article_50_compliant"] is True
        assert dumped["values"]["declared"] == list(EU_COMPLIANCE_VALUES)
