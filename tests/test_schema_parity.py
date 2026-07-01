"""Parity tests — canonical JSON schema enum values match Python implementation.

For each enum in the canonical JSON schema files, we assert that the
corresponding Python ``Enum`` subclass declares exactly the same members.
This detects drift in either direction: a value added to the schema without
updating the Python class, and a value added to Python without updating the
schema.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aap.schemas import (
    ActionCategory,
    ActionType,
    AlignmentMode,
    EscalationStatus,
    HierarchyType,
    PrincipalType,
    RelationshipType,
    TamperEvidence,
    TriggerAction,
)

_SCHEMAS_DIR = Path(__file__).parent.parent / "schemas"


def _load_schema(name: str) -> dict[str, Any]:
    return json.loads((_SCHEMAS_DIR / name).read_text())


def _def_enum(schema: dict[str, Any], def_name: str) -> set[str]:
    """Return the ``enum`` values for a named ``$defs`` entry as a set."""
    return set(schema["$defs"][def_name]["enum"])


class TestAlignmentCardSchemaParity:
    """Each AlignmentCard enum in Python matches the canonical JSON schema."""

    SCHEMA = _load_schema("alignment-card.schema.json")

    def test_alignment_mode(self) -> None:
        assert {m.value for m in AlignmentMode} == _def_enum(self.SCHEMA, "AlignmentMode")

    def test_principal_type(self) -> None:
        assert {m.value for m in PrincipalType} == _def_enum(self.SCHEMA, "PrincipalType")

    def test_relationship_type(self) -> None:
        assert {m.value for m in RelationshipType} == _def_enum(self.SCHEMA, "RelationshipType")

    def test_hierarchy_type(self) -> None:
        assert {m.value for m in HierarchyType} == _def_enum(self.SCHEMA, "HierarchyType")

    def test_trigger_action(self) -> None:
        assert {m.value for m in TriggerAction} == _def_enum(self.SCHEMA, "TriggerAction")

    def test_tamper_evidence(self) -> None:
        assert {m.value for m in TamperEvidence} == _def_enum(self.SCHEMA, "TamperEvidence")

    def test_alignment_mode_drift_guard(self) -> None:
        """Injecting a spurious value is detected (guard is bidirectional)."""
        schema_values = _def_enum(self.SCHEMA, "AlignmentMode")
        assert {m.value for m in AlignmentMode} != schema_values | {"spurious"}


class TestAPTraceSchemaParity:
    """Each APTrace enum in Python matches the canonical JSON schema."""

    SCHEMA = _load_schema("ap-trace.schema.json")

    def test_action_type(self) -> None:
        assert {m.value for m in ActionType} == _def_enum(self.SCHEMA, "ActionType")

    def test_action_category(self) -> None:
        assert {m.value for m in ActionCategory} == _def_enum(self.SCHEMA, "ActionCategory")

    def test_escalation_status(self) -> None:
        assert {m.value for m in EscalationStatus} == _def_enum(self.SCHEMA, "EscalationStatus")

    def test_escalation_status_drift_guard(self) -> None:
        """Injecting a spurious value is detected (guard is bidirectional)."""
        schema_values = _def_enum(self.SCHEMA, "EscalationStatus")
        assert {m.value for m in EscalationStatus} != schema_values | {"spurious"}
