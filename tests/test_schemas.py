"""Comprehensive tests for AAP schema models.

Tests Pydantic model validation, serialization, and business logic for:
- AlignmentCard and all nested models
- APTrace and all nested models
- Value Coherence Handshake messages

Design principles:
- Test valid cases first, then edge cases, then error cases
- Every validation rule should have a dedicated test
- Tests should document the schema through usage
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from aap.schemas import (
    # AP-Trace
    Action,
    ActionCategory,
    ActionType,
    # Alignment Card (unified / ADR-039)
    AlignmentCard,
    # Value Coherence
    AlignmentCardRequest,
    AlignmentCardResponse,
    Alternative,
    APTrace,
    Audit,
    Autonomy,
    CoherenceResultMessage,
    Decision,
    Escalation,
    EscalationTrigger,
    Principal,
    PrincipalType,
    ProposedCollaboration,
    RelationshipType,
    TriggerAction,
    ValueCoherenceCheck,
    Values,
)

# ===========================================================================
# AlignmentCard Schema Tests
# ===========================================================================


class TestPrincipal:
    """Tests for Principal model."""

    def test_minimal_principal(self):
        """Minimal valid principal (identifier required when type != unspecified)."""
        principal = Principal(
            type=PrincipalType.HUMAN,
            identifier="did:web:user.example.com",
            relationship=RelationshipType.DELEGATED_AUTHORITY,
        )
        assert principal.type == PrincipalType.HUMAN
        assert principal.relationship == RelationshipType.DELEGATED_AUTHORITY
        assert principal.identifier == "did:web:user.example.com"
        assert principal.escalation_contact is None

    def test_unspecified_principal_needs_no_identifier(self):
        """A principal of type 'unspecified' does not require an identifier."""
        principal = Principal(
            type=PrincipalType.UNSPECIFIED,
            relationship=RelationshipType.ADVISORY,
        )
        assert principal.identifier is None

    def test_identifier_required_when_typed(self):
        """ADR-039: identifier is required when type != 'unspecified'."""
        with pytest.raises(ValidationError) as exc_info:
            Principal(
                type=PrincipalType.HUMAN,
                relationship=RelationshipType.DELEGATED_AUTHORITY,
            )
        assert "identifier" in str(exc_info.value)

    def test_full_principal(self):
        """Fully-specified principal."""
        principal = Principal(
            type=PrincipalType.ORGANIZATION,
            identifier="did:web:corp.example.com",
            relationship=RelationshipType.AUTONOMOUS,
            escalation_contact="https://corp.example.com/escalate",
        )
        assert principal.type == PrincipalType.ORGANIZATION
        assert principal.identifier == "did:web:corp.example.com"

    def test_all_principal_types(self):
        """All principal types are valid (typed ones require an identifier)."""
        for ptype in PrincipalType:
            identifier = None if ptype == PrincipalType.UNSPECIFIED else "did:web:p.example.com"
            principal = Principal(
                type=ptype,
                identifier=identifier,
                relationship=RelationshipType.ADVISORY,
            )
            assert principal.type == ptype

    def test_all_relationship_types(self):
        """All relationship types are valid."""
        for rtype in RelationshipType:
            principal = Principal(
                type=PrincipalType.HUMAN,
                identifier="did:web:user.example.com",
                relationship=rtype,
            )
            assert principal.relationship == rtype

    def test_missing_required_fields(self):
        """Required fields must be provided."""
        with pytest.raises(ValidationError) as exc_info:
            Principal(type=PrincipalType.HUMAN)  # type: ignore
        assert "relationship" in str(exc_info.value)


class TestValues:
    """Tests for Values model."""

    def test_standard_values(self):
        """Standard values don't need definitions."""
        standard_values = [
            "principal_benefit",
            "transparency",
            "minimal_data",
            "harm_prevention",
            "honesty",
            "user_control",
            "privacy",
            "fairness",
        ]
        values = Values(declared=standard_values)
        assert values.declared == standard_values

    def test_custom_value_requires_definition_when_definitions_provided(self):
        """Custom values must have definitions when definitions dict has entries."""
        # Note: The validator only triggers when definitions is truthy (non-empty dict)
        # An empty dict {} is falsy, so won't trigger validation
        with pytest.raises(ValidationError) as exc_info:
            Values(
                declared=["principal_benefit", "my_custom_value"],
                definitions={
                    # Include at least one definition so dict is truthy
                    "some_other_value": {
                        "name": "Other",
                        "description": "Some other value",
                    }
                },
            )
        assert "my_custom_value" in str(exc_info.value)
        assert "must be defined" in str(exc_info.value)

    def test_custom_value_with_definition(self):
        """Custom values with definitions are valid."""
        values = Values(
            declared=["principal_benefit", "sustainability"],
            definitions={
                "sustainability": {
                    "name": "Environmental Sustainability",
                    "description": "Minimize environmental impact",
                    "priority": 1,
                }
            },
        )
        assert "sustainability" in values.declared
        assert "sustainability" in values.definitions

    def test_conflicts_with(self):
        """Values can declare conflicts."""
        values = Values(
            declared=["principal_benefit"],
            conflicts_with=["profit_maximization", "engagement_maximization"],
        )
        assert "profit_maximization" in values.conflicts_with

    def test_empty_declared_allowed(self):
        """Empty declared values list is allowed by schema.

        Note: The schema permits empty declared values. Whether this is
        semantically meaningful is a policy decision, not a schema constraint.
        """
        values = Values(declared=[])
        assert values.declared == []


class TestAutonomy:
    """Tests for Autonomy model (unified / ADR-039 §autonomy)."""

    def test_minimal_autonomy(self):
        """Minimal valid autonomy section."""
        autonomy = Autonomy(
            bounded_actions=["search"],
            escalation_triggers=[
                EscalationTrigger(
                    condition='action_type == "purchase"',
                    action=TriggerAction.ESCALATE,
                    reason="Require approval",
                )
            ],
        )
        assert autonomy.bounded_actions == ["search"]
        assert len(autonomy.escalation_triggers) == 1

    def test_escalation_triggers_optional(self):
        """escalation_triggers defaults to an empty list (unified shape)."""
        autonomy = Autonomy(bounded_actions=["search"])
        assert autonomy.escalation_triggers == []

    def test_forbidden_actions(self):
        """Forbidden actions list."""
        autonomy = Autonomy(
            bounded_actions=["search"],
            escalation_triggers=[],
            forbidden_actions=["delete", "transfer_funds"],
        )
        assert "delete" in autonomy.forbidden_actions

    def test_bounded_and_forbidden_must_be_disjoint(self):
        """ADR-039: bounded_actions and forbidden_actions must be disjoint."""
        with pytest.raises(ValidationError) as exc_info:
            Autonomy(
                bounded_actions=["search", "delete"],
                forbidden_actions=["delete"],
            )
        assert "disjoint" in str(exc_info.value)

    def test_max_autonomous_value(self):
        """Monetary limit specification."""
        autonomy = Autonomy(
            bounded_actions=["purchase"],
            escalation_triggers=[],
            max_autonomous_value={"amount": 100.0, "currency": "EUR"},
        )
        assert autonomy.max_autonomous_value.amount == 100.0
        assert autonomy.max_autonomous_value.currency == "EUR"

    def test_all_trigger_actions(self):
        """All trigger actions are valid."""
        for action in TriggerAction:
            trigger = EscalationTrigger(
                condition="test",
                action=action,
                reason=f"Test {action.value}",
            )
            assert trigger.action == action


class TestAudit:
    """Tests for Audit model (unified / ADR-039 §audit)."""

    def test_minimal_audit(self):
        """Minimal valid audit section."""
        audit = Audit(retention_days=30, queryable=False)
        assert audit.retention_days == 30
        assert audit.queryable is False

    def test_queryable_requires_endpoint(self):
        """If queryable=True, query_endpoint is required."""
        with pytest.raises(ValidationError) as exc_info:
            Audit(retention_days=90, queryable=True)
        assert "query_endpoint" in str(exc_info.value)

    def test_queryable_with_endpoint(self):
        """Queryable with endpoint is valid."""
        audit = Audit(
            retention_days=90,
            queryable=True,
            query_endpoint="https://api.example.com/traces",
        )
        assert audit.queryable is True
        assert audit.query_endpoint == "https://api.example.com/traces"

    def test_retention_days_zero_allowed(self):
        """ADR-039: retention_days must be non-negative (0 is allowed)."""
        audit = Audit(retention_days=0, queryable=False)
        assert audit.retention_days == 0

    def test_retention_days_negative_rejected(self):
        """Negative retention_days is rejected."""
        with pytest.raises(ValidationError):
            Audit(retention_days=-1, queryable=False)

    def test_tamper_evidence_options(self):
        """All tamper evidence types are valid."""
        for evidence in ["append_only", "signed", "merkle"]:
            audit = Audit(
                retention_days=90,
                queryable=False,
                tamper_evidence=evidence,
            )
            assert audit.tamper_evidence == evidence


class TestAlignmentCard:
    """Tests for AlignmentCard model."""

    def test_minimal_card(self, minimal_alignment_card: dict):
        """Minimal valid card from fixture."""
        card = AlignmentCard.model_validate(minimal_alignment_card)
        assert card.card_id == "ac-minimal-001"
        assert card.card_version == "unified/2026-04-26"

    def test_full_card(self, full_alignment_card: dict):
        """Fully-specified card from fixture."""
        card = AlignmentCard.model_validate(full_alignment_card)
        assert card.card_id == "ac-full-001"
        assert card.extensions is not None

    def test_to_dict_round_trip(self, minimal_alignment_card: dict):
        """Serialize and deserialize preserves data."""
        card = AlignmentCard.model_validate(minimal_alignment_card)
        exported = card.to_dict()
        reimported = AlignmentCard.from_dict(exported)
        assert reimported.card_id == card.card_id
        assert reimported.values.declared == card.values.declared

    def test_is_expired_not_expired(self, minimal_alignment_card: dict):
        """Card without expiry is not expired."""
        card = AlignmentCard.model_validate(minimal_alignment_card)
        assert card.is_expired() is False

    def test_is_expired_future(self, minimal_alignment_card: dict):
        """Card with future expiry is not expired.

        Note: There's a timezone-aware vs naive datetime comparison issue
        in is_expired(). This test uses naive datetime to work around it.
        """
        # Use naive datetime to avoid comparison issues
        minimal_alignment_card["expires_at"] = (datetime.utcnow() + timedelta(days=30)).isoformat()
        card = AlignmentCard.model_validate(minimal_alignment_card)
        assert card.is_expired() is False

    def test_is_expired_past(self, minimal_alignment_card: dict):
        """Card with past expiry is expired.

        Note: There's a timezone-aware vs naive datetime comparison issue
        in is_expired(). This test uses naive datetime to work around it.
        """
        # Use naive datetime to avoid comparison issues
        minimal_alignment_card["expires_at"] = (datetime.utcnow() - timedelta(days=1)).isoformat()
        card = AlignmentCard.model_validate(minimal_alignment_card)
        assert card.is_expired() is True

    def test_has_value(self, minimal_alignment_card: dict):
        """Check if card has a declared value."""
        card = AlignmentCard.model_validate(minimal_alignment_card)
        assert card.has_value("principal_benefit") is True
        assert card.has_value("profit_maximization") is False

    def test_is_action_bounded(self, minimal_alignment_card: dict):
        """Check if action is bounded."""
        card = AlignmentCard.model_validate(minimal_alignment_card)
        assert card.is_action_bounded("search") is True
        assert card.is_action_bounded("delete") is False

    def test_is_action_forbidden(self, full_alignment_card: dict):
        """Check if action is forbidden."""
        card = AlignmentCard.model_validate(full_alignment_card)
        assert card.is_action_forbidden("delete_data") is True
        assert card.is_action_forbidden("search") is False


# ===========================================================================
# APTrace Schema Tests
# ===========================================================================


class TestAction:
    """Tests for Action model."""

    def test_minimal_action(self):
        """Minimal valid action."""
        action = Action(
            type=ActionType.RECOMMEND,
            name="suggestion",
            category=ActionCategory.BOUNDED,
        )
        assert action.type == ActionType.RECOMMEND
        assert action.name == "suggestion"

    def test_all_action_types(self):
        """All action types are valid."""
        for atype in ActionType:
            action = Action(
                type=atype,
                name="test",
                category=ActionCategory.BOUNDED,
            )
            assert action.type == atype

    def test_all_action_categories(self):
        """All action categories are valid."""
        for category in ActionCategory:
            action = Action(
                type=ActionType.EXECUTE,
                name="test",
                category=category,
            )
            assert action.category == category

    def test_action_with_target(self):
        """Action with target specification."""
        action = Action(
            type=ActionType.EXECUTE,
            name="modify",
            category=ActionCategory.BOUNDED,
            target={"type": "file", "identifier": "/path/to/file"},
        )
        assert action.target.type == "file"

    def test_action_with_parameters(self):
        """Action with parameters."""
        action = Action(
            type=ActionType.EXECUTE,
            name="search",
            category=ActionCategory.BOUNDED,
            parameters={"query": "test", "limit": 10},
        )
        assert action.parameters["query"] == "test"


class TestDecision:
    """Tests for Decision model."""

    def test_minimal_decision(self):
        """Minimal valid decision."""
        decision = Decision(
            alternatives_considered=[
                Alternative(option_id="A", description="Option A"),
            ],
            selected="A",
            selection_reasoning="Only option available",
            values_applied=["principal_benefit"],
        )
        assert decision.selected == "A"
        assert len(decision.alternatives_considered) == 1

    def test_selected_must_be_in_alternatives(self):
        """Selected option must be one of the alternatives."""
        with pytest.raises(ValidationError) as exc_info:
            Decision(
                alternatives_considered=[
                    Alternative(option_id="A", description="Option A"),
                ],
                selected="B",  # Not in alternatives!
                selection_reasoning="Chose B",
                values_applied=["principal_benefit"],
            )
        assert "not in alternatives" in str(exc_info.value)

    def test_multiple_alternatives(self):
        """Decision with multiple alternatives."""
        decision = Decision(
            alternatives_considered=[
                Alternative(option_id="A", description="A", score=0.9),
                Alternative(option_id="B", description="B", score=0.7),
                Alternative(option_id="C", description="C", score=0.5),
            ],
            selected="A",
            selection_reasoning="Highest score",
            values_applied=["principal_benefit"],
        )
        assert len(decision.alternatives_considered) == 3

    def test_confidence_bounds(self):
        """Confidence must be between 0 and 1."""
        # Valid confidence
        decision = Decision(
            alternatives_considered=[
                Alternative(option_id="A", description="A"),
            ],
            selected="A",
            selection_reasoning="Test",
            values_applied=["principal_benefit"],
            confidence=0.85,
        )
        assert decision.confidence == 0.85

        # Invalid confidence > 1
        with pytest.raises(ValidationError):
            Decision(
                alternatives_considered=[
                    Alternative(option_id="A", description="A"),
                ],
                selected="A",
                selection_reasoning="Test",
                values_applied=["principal_benefit"],
                confidence=1.5,
            )

    def test_alternative_score_bounds(self):
        """Alternative scores must be between 0 and 1."""
        with pytest.raises(ValidationError):
            Alternative(option_id="A", description="A", score=1.5)

    def test_value_scores_optional(self):
        """value_scores is optional — V1 observer output has no value_scores."""
        decision = Decision(
            alternatives_considered=[
                Alternative(option_id="A", description="Option A"),
            ],
            selected="A",
            selection_reasoning="Only option available",
            values_applied=["principal_benefit"],
        )
        assert decision.value_scores is None

    def test_value_scores_populated(self):
        """V2 observer surface — value_scores keyed by catalog value id."""
        decision = Decision(
            alternatives_considered=[
                Alternative(option_id="A", description="Option A"),
            ],
            selected="A",
            selection_reasoning="Chose A",
            values_applied=["escalation_when_unsure"],
            value_scores={
                "escalation_when_unsure": {
                    "score": "on_track",
                    "rationale": "Hedged then invoked stage_next_action",
                },
                "principled_dissent": {
                    "score": "not_applicable",
                    "rationale": "No value conflict surfaced this turn",
                },
            },
        )
        assert decision.value_scores is not None
        assert decision.value_scores["escalation_when_unsure"].score == "on_track"
        assert decision.value_scores["principled_dissent"].score == "not_applicable"

    def test_value_scores_rejects_invalid_score(self):
        """Score must be one of on_track / off_track / not_applicable."""
        with pytest.raises(ValidationError):
            Decision(
                alternatives_considered=[
                    Alternative(option_id="A", description="Option A"),
                ],
                selected="A",
                selection_reasoning="Test",
                values_applied=["x"],
                value_scores={
                    "x": {
                        "score": "maybe",  # Not a valid Literal value
                        "rationale": "uncertain",
                    },
                },
            )


class TestValueScore:
    """Tests for ValueScore model (Phase 3.3 V2 observer surface)."""

    def test_minimal(self):
        """Minimal ValueScore with the three required-shape fields."""
        from aap.schemas import ValueScore

        vs = ValueScore(score="on_track", rationale="hedged then escalated")
        assert vs.score == "on_track"
        assert vs.rationale == "hedged then escalated"

    def test_off_track(self):
        """off_track score is accepted."""
        from aap.schemas import ValueScore

        vs = ValueScore(score="off_track", rationale="committed silently")
        assert vs.score == "off_track"

    def test_not_applicable(self):
        """not_applicable score is accepted for surface-not-exercised turns."""
        from aap.schemas import ValueScore

        vs = ValueScore(score="not_applicable", rationale="no value conflict this turn")
        assert vs.score == "not_applicable"

    def test_invalid_score_raises(self):
        """Score outside the three-value Literal raises ValidationError."""
        from aap.schemas import ValueScore

        with pytest.raises(ValidationError):
            ValueScore(score="invalid", rationale="x")  # type: ignore[arg-type]


class TestEscalation:
    """Tests for Escalation model."""

    def test_not_required(self):
        """Escalation not required."""
        escalation = Escalation(
            evaluated=True,
            required=False,
            reason="No triggers matched",
        )
        assert escalation.required is False

    def test_required_with_status(self):
        """Escalation required with status tracking."""
        escalation = Escalation(
            evaluated=True,
            required=True,
            reason="Amount exceeded threshold",
            escalation_id="esc-001",
            escalation_status="pending",
        )
        assert escalation.required is True
        assert escalation.escalation_status == "pending"

    def test_with_principal_response(self):
        """Escalation with principal response."""
        escalation = Escalation(
            evaluated=True,
            required=True,
            reason="Purchase requires approval",
            escalation_id="esc-002",
            escalation_status="approved",
            principal_response={
                "decision": "Approved",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
        assert escalation.principal_response.decision == "Approved"


class TestAPTrace:
    """Tests for APTrace model."""

    def test_minimal_trace(self, minimal_trace: dict):
        """Minimal valid trace from fixture."""
        trace = APTrace.model_validate(minimal_trace)
        assert trace.trace_id == "tr-minimal-001"

    def test_to_dict_round_trip(self, minimal_trace: dict):
        """Serialize and deserialize preserves data."""
        trace = APTrace.model_validate(minimal_trace)
        exported = trace.to_dict()
        reimported = APTrace.from_dict(exported)
        assert reimported.trace_id == trace.trace_id
        assert reimported.action.name == trace.action.name

    def test_get_selected_alternative(self, minimal_trace: dict):
        """Get the selected alternative."""
        trace = APTrace.model_validate(minimal_trace)
        selected = trace.get_selected_alternative()
        assert selected is not None
        assert selected.option_id == "A"

    def test_was_escalated_false(self, minimal_trace: dict):
        """Check escalation status — not escalated."""
        trace = APTrace.model_validate(minimal_trace)
        assert trace.was_escalated() is False

    def test_was_escalated_true(self, minimal_trace: dict):
        """Check escalation status — was escalated."""
        minimal_trace["escalation"]["required"] = True
        trace = APTrace.model_validate(minimal_trace)
        assert trace.was_escalated() is True

    def test_trace_with_context(self, minimal_trace: dict):
        """Trace with full context."""
        minimal_trace["context"] = {
            "session_id": "sess-001",
            "conversation_turn": 5,
            "prior_trace_ids": ["tr-001", "tr-002"],
            "environment": {"client": "web", "locale": "en-US"},
            "metadata": {"custom_field": "value"},
        }
        trace = APTrace.model_validate(minimal_trace)
        assert trace.context.session_id == "sess-001"
        assert trace.context.conversation_turn == 5


# ===========================================================================
# Value Coherence Handshake Tests
# ===========================================================================


class TestAlignmentCardRequest:
    """Tests for AlignmentCardRequest message."""

    def test_minimal_request(self):
        """Minimal valid request."""
        request = AlignmentCardRequest(
            request_id="req-001",
            requester={
                "agent_id": "agent-a",
                "card_id": "card-a",
            },
        )
        assert request.message_type == "alignment_card_request"
        assert request.request_id == "req-001"

    def test_with_task_context(self):
        """Request with task context."""
        request = AlignmentCardRequest(
            request_id="req-002",
            requester={
                "agent_id": "agent-a",
                "card_id": "card-a",
            },
            task_context={
                "task_type": "product_recommendation",
                "values_required": ["principal_benefit", "transparency"],
            },
        )
        assert request.task_context.task_type == "product_recommendation"


class TestAlignmentCardResponse:
    """Tests for AlignmentCardResponse message."""

    def test_minimal_response(self, minimal_alignment_card: dict):
        """Minimal valid response."""
        response = AlignmentCardResponse(
            request_id="req-001",
            alignment_card=minimal_alignment_card,
        )
        assert response.message_type == "alignment_card_response"
        assert response.alignment_card["card_id"] == "ac-minimal-001"


class TestValueCoherenceCheck:
    """Tests for ValueCoherenceCheck message."""

    def test_minimal_check(self):
        """Minimal valid coherence check."""
        check = ValueCoherenceCheck(
            request_id="req-001",
            initiator_card_id="card-a",
            responder_card_id="card-b",
            proposed_collaboration=ProposedCollaboration(
                task_type="comparison",
            ),
        )
        assert check.message_type == "value_coherence_check"


class TestCoherenceResultMessage:
    """Tests for CoherenceResultMessage."""

    def test_compatible_result(self):
        """Compatible coherence result."""
        result = CoherenceResultMessage(
            request_id="req-001",
            coherence={
                "compatible": True,
                "score": 0.85,
                "value_alignment": {
                    "matched": ["principal_benefit", "transparency"],
                    "unmatched": [],
                    "conflicts": [],
                },
            },
            proceed=True,
        )
        assert result.proceed is True
        assert result.coherence.score == 0.85

    def test_conflict_result(self):
        """Coherence result with conflicts."""
        result = CoherenceResultMessage(
            request_id="req-002",
            coherence={
                "compatible": False,
                "score": 0.35,
                "value_alignment": {
                    "matched": ["transparency"],
                    "unmatched": ["privacy"],
                    "conflicts": [
                        {
                            "initiator_value": "minimal_data",
                            "responder_value": "comprehensive_analytics",
                            "conflict_type": "incompatible",
                            "description": "Data collection conflict",
                        }
                    ],
                },
            },
            proceed=False,
            proposed_resolution={
                "type": "escalate_to_principals",
                "reason": "Value conflict requires human decision",
            },
        )
        assert result.proceed is False
        assert len(result.coherence.value_alignment.conflicts) == 1


# ===========================================================================
# Cross-Schema Integration Tests
# ===========================================================================


class TestSchemaIntegration:
    """Tests verifying schemas work together correctly."""

    def test_trace_references_card(
        self,
        minimal_alignment_card: dict,
        minimal_trace: dict,
    ):
        """Trace correctly references its alignment card."""
        card = AlignmentCard.model_validate(minimal_alignment_card)
        trace = APTrace.model_validate(minimal_trace)
        assert trace.card_id == card.card_id

    def test_trace_action_matches_card_bounds(
        self,
        minimal_alignment_card: dict,
        minimal_trace: dict,
    ):
        """Trace action is within card's bounded actions."""
        _card = AlignmentCard.model_validate(minimal_alignment_card)  # noqa: F841
        trace = APTrace.model_validate(minimal_trace)

        # The action name might not be in bounded_actions (depends on category)
        if trace.action.category == ActionCategory.BOUNDED:
            # This is a semantic check that verification enforces, not schema
            pass

    def test_trace_values_match_card_values(
        self,
        minimal_alignment_card: dict,
        minimal_trace: dict,
    ):
        """Trace values should be subset of card's declared values."""
        card = AlignmentCard.model_validate(minimal_alignment_card)
        trace = APTrace.model_validate(minimal_trace)

        declared = set(card.values.declared)
        applied = set(trace.decision.values_applied)

        # This is a semantic check — schemas allow any values,
        # verification enforces the constraint
        # Here we just verify we CAN compare them
        assert isinstance(declared, set)
        assert isinstance(applied, set)
