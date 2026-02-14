# EU AI Act Article 50 → AAP Compliance Mapping

## How AAP Satisfies EU AI Act Transparency Obligations

**Date**: February 2026
**Authors**: Mnemom Research
**License**: CC BY 4.0

---

## Summary

The EU AI Act's Article 50 establishes transparency obligations for providers and deployers of AI systems. These obligations require that users are informed they are interacting with AI, that AI-generated content is machine-detectable, that decisions are explainable, and that audit trails are maintained.

The Agent Alignment Protocol (AAP) provides the technical infrastructure to satisfy these requirements through its three core artifacts: the **Alignment Card** (declaration), the **AP-Trace** (audit trail), and the **Verification Engine** (enforcement).

This document provides a field-level mapping between Article 50 obligations and AAP features, references the SDK compliance presets, and links to a working example.

**Disclaimer**: This document reflects a technical mapping of AAP features to Article 50 requirements. It does not constitute legal advice. Consult qualified legal counsel for your specific compliance obligations.

---

## Article 50 Obligation Mapping

### 50(1) — Inform Users of AI Interaction

**Requirement**: Providers shall ensure that AI systems intended to interact directly with natural persons are designed and developed in such a way that the natural persons concerned are informed that they are interacting with an AI system, unless this is obvious from the circumstances and the context of use.

**AAP mapping**:

| Obligation | AAP Field | How It Satisfies |
|-----------|-----------|------------------|
| Identify the AI system | `AlignmentCard.agent_id` | Unique, persistent agent identifier |
| Identify the principal | `AlignmentCard.principal` | Declares human/org oversight and relationship type |
| Disclose AI nature | `extensions.eu_ai_act.disclosure_text` | Machine-readable disclosure text for presentation to users |
| Classify the system | `extensions.eu_ai_act.ai_system_classification` | Declares risk classification per AI Act categories |

**SDK preset**: `EU_COMPLIANCE_EXTENSIONS` provides a ready-made extension block:

```python
from aap.compliance import EU_COMPLIANCE_EXTENSIONS

card = AlignmentCard(
    ...,
    extensions=EU_COMPLIANCE_EXTENSIONS,
)
# card.extensions["eu_ai_act"]["disclosure_text"] contains the disclosure
```

### 50(2) — Machine-Readable Marking

**Requirement**: Providers of AI systems, including general-purpose AI systems, generating synthetic audio, image, video or text content, shall ensure that the outputs of the AI system are marked in a machine-readable format and detectable as artificially generated or manipulated.

**AAP mapping**:

| Obligation | AAP Field | How It Satisfies |
|-----------|-----------|------------------|
| Machine-readable format | AP-Trace structured JSON | Every decision is a structured, parseable record |
| Protocol versioning | `AlignmentCard.aap_version` | Protocol version enables tooling compatibility |
| Trace format declaration | `audit_commitment.trace_format` = `"ap-trace-v1"` | Declares the structured format used |
| Agent attribution | `APTrace.agent_id` + `APTrace.card_id` | Every trace links to the producing agent and its card |

AP-Traces are inherently machine-readable — they are structured JSON documents with a defined schema. Any system processing AAP-instrumented agent output can parse the trace to determine that it was AI-generated and by which agent.

### 50(3) — Transparency of Decisions

**Requirement**: Deployers of AI systems that generate or manipulate content shall disclose that the content has been artificially generated or manipulated. Deployers of emotion recognition or biometric categorisation systems shall inform natural persons exposed thereto of the operation of the system.

**AAP mapping**:

| Obligation | AAP Field | How It Satisfies |
|-----------|-----------|------------------|
| Decision reasoning | `APTrace.decision.selection_reasoning` | Free-text explanation of why the agent chose this action |
| Values applied | `APTrace.decision.values_applied` | Which declared values influenced the decision |
| Alternatives considered | `APTrace.decision.alternatives_considered` | All options the agent evaluated, with scores |
| Escalation evaluation | `APTrace.escalation.evaluated` + `triggers_checked` | Whether human oversight was considered and why |
| Confidence | `APTrace.decision.confidence` | Agent's self-assessed confidence in the decision |

The AP-Trace `decision` block provides complete transparency into agent reasoning: what alternatives were considered, how they were scored, which values were applied, and why the selected option was chosen. This goes beyond Article 50's minimum requirements by making the full decision process auditable.

### 50(4) — Audit Trail

**Requirement**: AI systems shall be designed and developed to allow for the logging of relevant events over the lifetime of the system, in a manner that enables tracing of the system's operation.

**AAP mapping**:

| Obligation | AAP Field | How It Satisfies |
|-----------|-----------|------------------|
| Retention period | `audit_commitment.retention_days` >= 90 | Minimum 90 days recommended for EU compliance |
| Queryability | `audit_commitment.queryable` = `true` | Traces can be retrieved and inspected |
| Tamper evidence | `audit_commitment.tamper_evidence` = `"append_only"` | Audit log integrity protection |
| Query endpoint | `audit_commitment.query_endpoint` | Optional: API endpoint for trace retrieval |
| Trace format | `audit_commitment.trace_format` = `"ap-trace-v1"` | Standardized, versioned format |

**SDK preset**: `EU_COMPLIANCE_AUDIT_COMMITMENT` provides recommended values:

```python
from aap.compliance import EU_COMPLIANCE_AUDIT_COMMITMENT

card = AlignmentCard(
    ...,
    audit_commitment=AuditCommitment(**EU_COMPLIANCE_AUDIT_COMMITMENT),
)
# retention_days=90, queryable=True, tamper_evidence="append_only"
```

---

## Risk Assessment Support

Article 50 obligations vary by risk classification. AAP supports risk assessment through:

| Risk Dimension | AAP Feature | Reference |
|---------------|-------------|-----------|
| Behavioral boundaries | `autonomy_envelope.bounded_actions` + `forbidden_actions` | Alignment Card |
| Escalation policy | `autonomy_envelope.escalation_triggers` | Alignment Card |
| Value declaration | `values.declared` + `values.definitions` | Alignment Card |
| Known limitations | LIMITS.md documentation pattern | `docs/LIMITS.md` |
| Behavioral drift | `detect_drift()` API | Verification Engine |
| Violation detection | `verify_trace()` API | Verification Engine |

The Alignment Card + LIMITS.md combination provides the static risk assessment. The Verification Engine provides dynamic, ongoing risk monitoring.

---

## SDK Compliance Presets

AAP provides three compliance presets that encapsulate the recommended configuration:

### `EU_COMPLIANCE_AUDIT_COMMITMENT`

```python
{
    "retention_days": 90,
    "queryable": True,
    "query_endpoint": "https://audit.example.com/traces",
    "tamper_evidence": "append_only",
    "trace_format": "ap-trace-v1",
}
```

### `EU_COMPLIANCE_EXTENSIONS`

```python
{
    "eu_ai_act": {
        "article_50_compliant": True,
        "ai_system_classification": "general_purpose",
        "disclosure_text": "This system is powered by an AI agent. Its decisions "
                           "are logged and auditable. You may request a human "
                           "review of any decision.",
        "compliance_version": "2026-08",
    },
}
```

### `EU_COMPLIANCE_VALUES`

```python
["transparency", "honesty", "user_control", "principal_benefit"]
```

These are available in both Python and TypeScript:

```python
from aap.compliance import (
    EU_COMPLIANCE_AUDIT_COMMITMENT,
    EU_COMPLIANCE_EXTENSIONS,
    EU_COMPLIANCE_VALUES,
)
```

```typescript
import {
  EU_COMPLIANCE_AUDIT_COMMITMENT,
  EU_COMPLIANCE_EXTENSIONS,
  EU_COMPLIANCE_VALUES,
} from "agent-alignment-protocol";
```

---

## Relationship to AIP

AAP provides post-hoc audit trails (what the agent did). The Agent Integrity Protocol (AIP) provides real-time transparency (what the agent is thinking). Together they satisfy both dimensions of Article 50:

| Dimension | Protocol | Artifact |
|-----------|----------|----------|
| Decision audit trail | AAP | AP-Trace |
| Real-time reasoning transparency | AIP | Integrity Checkpoint |
| Cross-protocol linkage | Both | `IntegrityCheckpoint.linked_trace_id` → `APTrace.trace_id` |

See the [AIP EU AI Act Compliance Guide](https://github.com/mnemom/aip/blob/main/docs/EU_AI_ACT_MAPPING.md) for AIP-specific mappings.

---

## Working Example

See [`examples/eu-compliance/`](../examples/eu-compliance/) for a complete working example that:

1. Creates an EU-compliant Alignment Card using the presets
2. Generates a traced decision
3. Verifies the trace against the card
4. Prints a compliance summary

---

## Enforcement Timeline

| Date | Milestone |
|------|-----------|
| August 2025 | AI Act general provisions in force |
| February 2026 | Prohibited practices apply |
| **August 2026** | **Article 50 transparency obligations apply** |
| August 2027 | High-risk system obligations apply |

---

## References

- [EU AI Act Article 50 — Full Text](https://artificialintelligenceact.eu/article/50/)
- [AAP Specification](../docs/SPEC.md)
- [AAP LIMITS.md](../docs/LIMITS.md)
- [EU AI Act Compliance Example](../examples/eu-compliance/)
