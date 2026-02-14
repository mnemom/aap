# EU AI Act Article 50 Compliance Example

Demonstrates how to configure an AAP-instrumented agent for EU AI Act Article 50 compliance using the SDK compliance presets.

## Quick Start

```bash
# From the repository root
cd examples/eu-compliance
python main.py
```

## What It Does

This example creates an EU-compliant agent that:

1. **Declares transparency values** using `EU_COMPLIANCE_VALUES`
2. **Configures 90-day audit retention** with tamper evidence using `EU_COMPLIANCE_AUDIT_COMMITMENT`
3. **Includes EU AI Act metadata** (disclosure text, classification) using `EU_COMPLIANCE_EXTENSIONS`
4. **Makes a traced decision** and verifies it against the card
5. **Prints an Article 50 compliance summary**

## Article 50 Obligations Satisfied

| Obligation | How This Example Addresses It |
|-----------|------------------------------|
| **50(1)** Inform users of AI interaction | `agent_id`, `principal`, and `extensions.eu_ai_act.disclosure_text` |
| **50(2)** Machine-readable marking | AP-Trace structured JSON with `trace_format: "ap-trace-v1"` |
| **50(3)** Transparency of decisions | `decision.selection_reasoning`, `values_applied`, `alternatives_considered` |
| **50(4)** Audit trail | `retention_days: 90`, `queryable: true`, `tamper_evidence: "append_only"` |

## SDK Compliance Presets Used

```python
from aap.compliance import (
    EU_COMPLIANCE_AUDIT_COMMITMENT,  # retention, queryable, tamper_evidence
    EU_COMPLIANCE_EXTENSIONS,        # eu_ai_act disclosure block
    EU_COMPLIANCE_VALUES,            # transparency, honesty, user_control, principal_benefit
)
```

## Files

- `alignment-card.json` — Pre-built EU-compliant Alignment Card
- `main.py` — Creates card from presets, traces a decision, verifies, prints summary

## Further Reading

- [EU AI Act Compliance Mapping](../../docs/EU_AI_ACT_MAPPING.md)
- [AAP Specification](../../docs/SPEC.md)
- [Article 50 Full Text](https://artificialintelligenceact.eu/article/50/)
