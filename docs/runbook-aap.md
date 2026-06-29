# AAP Triage Runbook

**Service:** `aap` — the Agent Alignment Protocol (agent-to-agent delegation, value-coherence, alignment cards).
**Last reviewed:** 2026-06-28
**Scope:** first-responder triage for delegation-decision failures, agent-card validation failures, and schema-version incidents. For protocol semantics see [docs.mnemom.ai/protocols/aap](https://docs.mnemom.ai/protocols/aap/specification).

AAP has no live alerting surface today (it is a protocol library + reference traces, not a always-on prod service). This runbook is the manual triage path when a consumer reports a delegation or card-validation problem. The canonical artifacts it references live at the repo root: `delegation-approved-trace.json`, `delegation-rejected-trace.json`, the agent cards (`user-agent-card.json`, `vendor-agent-card.json`, `compatible-vendor-card.json`), and the JSON schemas in `schemas/`.

---

## 1. Delegation accept/reject decision failures

**Symptom**
- A delegation that should have been accepted is rejected (or vice versa), or a coherence/escalation decision looks wrong to the principal.
- A consumer reports `selected: "reject"` with an unexpected `selection_reasoning`, or an `escalate` action where `delegate` was expected.

**Signals**
- The decision trace shape (matches `delegation-approved-trace.json` / `delegation-rejected-trace.json`):
  - `action.type` — `execute` (proceeded) vs `escalate` (escalation_trigger fired).
  - `decision.alternatives_considered[]` — each option's `score` and `flags` (e.g. `["value_conflict"]`).
  - `decision.selected` + `decision.selection_reasoning` — the coherence score and compatibility, e.g.
    `"Coherence check with vendor-deals-agent: score=0.13, compatible=False. Conflicts: [...]"`.
  - `decision.values_applied` (e.g. `principal_benefit`, `transparency`) and `decision.confidence`.
  - `escalation.evaluated` / `escalation.triggers_checked[]` / `escalation.required` / `escalation.reason`.
- Compare the live trace against the two committed reference traces — an approved decision should resemble `delegation-approved-trace.json` (selected `delegate`, score ≈ 1.0, no flags); a rejection should resemble `delegation-rejected-trace.json` (selected `reject`/`escalate`, low score, `value_conflict` flag, `escalation.required: true`).

**Mitigation**
1. Confirm the value-coherence inputs: the two agent cards being checked and their declared `conflicts_with` sets. A rejection like the reference trace fires when "Responder's 'upselling' is in initiator's conflicts_with" — i.e. the cards are genuinely incompatible. If the cards are correct, the reject is correct (working as intended).
2. If the cards are wrong (a value was mis-declared), the fix is on the card side, not the protocol — see §2.
3. If the score/threshold logic itself looks wrong, capture the trace and the two cards and file an issue with the reproducing inputs; do not hand-edit a decision.

**Escalation:** a value conflict with `escalation.required: true` is the protocol working as designed — it hands the decision to the principal. A *missing* escalation on a conflicting pair is a real defect → file an issue with the trace.

---

## 2. Agent-card / alignment-card validation failures

**Symptom**
- A card is rejected at load/validation, or coherence checks error because a card can't be parsed.

**Signals**
- Validate the card against the schema:
  - alignment cards → `schemas/alignment-card.schema.json`
  - value-coherence payloads → `schemas/value-coherence.schema.json`
  - decision traces → `schemas/ap-trace.schema.json`
- Reference cards to diff against: `user-agent-card.json`, `vendor-agent-card.json`, `compatible-vendor-card.json`.

**Mitigation**
1. Validate the failing card JSON against the matching schema (e.g. with `check-jsonschema` / `ajv` / any JSON-Schema validator) to get the exact failing field.
2. Diff the failing card against the closest reference card to spot a missing/renamed required field.
3. Fix the card to satisfy the schema; never relax the schema to admit a malformed card without review.

**Escalation:** a card that passes the schema but still produces wrong coherence results → §1 (decision logic), with both cards attached.

---

## 3. Schema-version incidents

**Symptom**
- A consumer on an older/newer protocol version produces traces/cards that no longer validate, or fields are dropped/renamed across a version bump.

**Signals**
- The schema files in `schemas/` and the version markers in the cards/traces. A field present in a reference artifact but absent (or renamed) in a consumer's payload indicates a version skew.
- The repo uses release-please (`release-please-config.json`, `.release-please-manifest.json`) — check the version the consumer is on vs the current schema.

**Mitigation**
1. Identify the version skew (consumer version vs the `schemas/` version in `main`).
2. For a removed/renamed field, point the consumer at the current schema and the migration notes ([docs.mnemom.ai/protocols/aap/mcp-migration](https://docs.mnemom.ai/protocols/aap/mcp-migration)).
3. If a schema change was not backward-compatible and should have been, file an issue — schema changes must keep old valid payloads valid or ship a documented migration.

**Escalation:** a breaking schema change already shipped to consumers → escalate to the protocol owner; coordinate a migration note rather than silently breaking consumers.

---

## See also

- Protocol spec & security model: [docs.mnemom.ai/protocols/aap](https://docs.mnemom.ai/protocols/aap/specification)
- Reference artifacts (repo root): `delegation-approved-trace.json`, `delegation-rejected-trace.json`, `*-agent-card.json`, `compatible-vendor-card.json`
- Schemas: `schemas/alignment-card.schema.json`, `schemas/value-coherence.schema.json`, `schemas/ap-trace.schema.json`
