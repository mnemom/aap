"""Tests asserting the unified / ADR-039 AlignmentCard shape (MNE-190).

These tests pin the migrated card shape: top-level master switches
(`autonomy_mode`, `integrity_mode`), the renamed `autonomy` / `audit`
sections, `card_version` (replacing the legacy `aap_version`), and the
`principal.identifier`-when-typed rule. They guard against an accidental
regression back to the legacy AAP 0.5.0 shape.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from aap.schemas import AlignmentCard
from aap.schemas.alignment_card import CARD_VERSION

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"
EXAMPLE_CARDS = [
    EXAMPLES_DIR / "simple-agent" / "alignment-card.json",
    EXAMPLES_DIR / "eu-compliance" / "alignment-card.json",
    EXAMPLES_DIR / "mcp-integration" / "server-alignment-card.json",
]


class TestUnifiedShape:
    """The serialized card uses the unified field names, never the legacy ones."""

    def test_to_dict_uses_unified_keys(self, minimal_alignment_card: dict):
        card = AlignmentCard.model_validate(minimal_alignment_card)
        dumped = card.to_dict()
        # Unified keys present
        assert "card_version" in dumped
        assert "autonomy_mode" in dumped
        assert "integrity_mode" in dumped
        assert "autonomy" in dumped
        assert "audit" in dumped
        # Legacy keys absent
        assert "aap_version" not in dumped
        assert "autonomy_envelope" not in dumped
        assert "audit_commitment" not in dumped

    def test_default_card_version(self):
        card = AlignmentCard(
            card_id="ac-x",
            agent_id="agent-x",
            issued_at="2026-04-26T00:00:00Z",
            principal={
                "type": "agent",
                "identifier": "mnm-abcd",
                "relationship": "delegated_authority",
            },
            values={"declared": ["transparency"]},
            autonomy={"bounded_actions": ["respond"]},
            audit={"retention_days": 30, "queryable": False},
        )
        assert card.card_version == CARD_VERSION
        # Master switches default to the non-blocking "observe" mode.
        assert card.autonomy_mode.value == "observe"
        assert card.integrity_mode.value == "observe"

    def test_master_switch_enum_rejects_unknown(self, minimal_alignment_card: dict):
        bad = dict(minimal_alignment_card)
        bad["autonomy_mode"] = "turbo"
        with pytest.raises(ValidationError):
            AlignmentCard.model_validate(bad)

    def test_legacy_shape_is_rejected(self, minimal_alignment_card: dict):
        """A card using the legacy autonomy_envelope/audit_commitment keys
        (and lacking the unified ones) fails to validate."""
        legacy = {
            "aap_version": "0.5.0",
            "card_id": "ac-legacy",
            "agent_id": "agent-legacy",
            "issued_at": "2026-01-01T00:00:00Z",
            "principal": {"type": "human", "relationship": "delegated_authority"},
            "values": {"declared": ["transparency"]},
            "autonomy_envelope": {"bounded_actions": ["search"]},
            "audit_commitment": {"retention_days": 30, "queryable": False},
        }
        with pytest.raises(ValidationError):
            AlignmentCard.model_validate(legacy)


class TestExampleCards:
    """The shipped example cards parse as unified cards."""

    @pytest.mark.parametrize("path", EXAMPLE_CARDS, ids=lambda p: p.parent.name)
    def test_example_card_validates(self, path: Path):
        data = json.loads(path.read_text())
        card = AlignmentCard.model_validate(data)
        assert card.card_version == "unified/2026-04-26"
        assert card.autonomy.bounded_actions
        # principal.identifier present because all examples declare a typed principal
        assert card.principal.identifier
        # No legacy keys in the source file
        raw = path.read_text()
        assert "aap_version" not in raw
        assert "autonomy_envelope" not in raw
        assert "audit_commitment" not in raw
