# Agent Alignment Protocol (AAP) Specification

**Version**: 0.1.1
**Status**: Draft
**Date**: 2026-02-01
**Authors**: Vigil (protocol), Ariadne (architecture), Ember (coordination)

---

## Abstract

The Agent Alignment Protocol (AAP) defines a standard for autonomous agents to declare their alignment posture, produce auditable decision traces, and verify value coherence before inter-agent coordination. AAP extends existing agent coordination protocols (A2A, MCP) with an alignment layer that makes agent behavior observable to principals, auditors, and other agents.

AAP is a transparency protocol, not a trust protocol. It makes agent behavior more observable, not more guaranteed.

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Terminology](#2-terminology)
3. [Protocol Overview](#3-protocol-overview)
4. [Alignment Card](#4-alignment-card)
5. [AP-Trace](#5-ap-trace)
6. [Value Coherence Handshake](#6-value-coherence-handshake)
7. [Verification](#7-verification)
8. [Drift Detection](#8-drift-detection)
9. [Security Considerations](#9-security-considerations)
10. [Limitations](#10-limitations)
11. [IANA Considerations](#11-iana-considerations)
12. [References](#12-references)
13. [Appendix A: JSON Schemas](#appendix-a-json-schemas)
14. [Appendix B: Verification Algorithm](#appendix-b-verification-algorithm)

---

## 1. Introduction

### 1.1 Problem Statement

The current agent protocol stack provides mechanisms for capability discovery (A2A Agent Cards), tool integration (MCP), and payment authorization (AP2). None of these protocols address a fundamental question: **Is this agent serving its principal's interests?**

As agent capabilities become symmetric—equal access to information, equal reasoning power, equal tool access—alignment becomes the primary differentiator. When you cannot reliably distinguish between human and agent communication, trust in alignment becomes essential infrastructure.

### 1.2 Design Goals

AAP is designed with the following goals:

1. **Transparency over guarantee**: Make agent decisions observable, not provably correct
2. **Composability**: Extend existing protocols (A2A, MCP) rather than replace them
3. **Minimal overhead**: Add alignment without significant performance cost
4. **Falsifiability**: Enable third-party verification and audit
5. **Honest limits**: Be explicit about what the protocol cannot provide

### 1.3 Non-Goals

AAP explicitly does NOT attempt to:

- Guarantee that agents will behave as declared
- Provide protection against sophisticated deception
- Replace human judgment in consequential decisions
- Certify that an agent is "safe" or "trustworthy"
- Solve the alignment problem in general

### 1.4 Document Conventions

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "NOT RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in BCP 14 [RFC2119] [RFC8174] when, and only when, they appear in all capitals, as shown here.

---

## 2. Terminology

**Agent**: An autonomous software entity capable of taking actions on behalf of a principal.

**Principal**: The human or organization whose interests the agent is meant to serve.

**Alignment Card**: A structured declaration of an agent's alignment posture, including values, autonomy envelope, and audit commitments.

**AP-Trace**: An audit log entry recording an agent's decision process, including alternatives considered and selection reasoning.

**Value Coherence**: The degree to which two agents' declared values are compatible for coordination.

**Autonomy Envelope**: The set of actions an agent may take without escalation, and the conditions that trigger escalation.

**Escalation**: The process of deferring a decision to a principal or higher-authority agent.

**Drift**: Behavioral deviation from declared alignment posture over time.

**Verification**: The process of checking whether observed behavior (AP-Trace) is consistent with declared alignment (Alignment Card).

**Strand**: In multi-turn conversations, a participant's sequence of messages.

**SSM (Self-Similarity Matrix)**: A computational structure measuring semantic similarity between messages across a conversation.

**Divergence**: When conversation strands drift apart semantically, indicating potential misalignment.

---

## 3. Protocol Overview

### 3.1 Components

AAP consists of three interconnected components:

```
+-------------------------------------------------------------+
|                  Agent Alignment Protocol                    |
+-----------------+-----------------+-------------------------+
| Alignment Card  |    AP-Trace     | Value Coherence         |
|                 |                 | Handshake               |
+-----------------+-----------------+-------------------------+
| Declaration     | Audit           | Coordination            |
|                 |                 |                         |
| "What I claim   | "What I         | "Can we work            |
|  to be"         |  actually did"  |  together?"             |
+-----------------+-----------------+-------------------------+
```

1. **Alignment Card**: Static declaration of alignment posture
2. **AP-Trace**: Dynamic audit log of decisions
3. **Value Coherence Handshake**: Pre-coordination compatibility check

### 3.2 Protocol Flow

A typical AAP interaction proceeds as follows:

```
Agent A                                    Agent B
   |                                          |
   |---- 1. alignment_card_request ---------->|
   |                                          |
   |<--- 2. alignment_card_response ----------|
   |                                          |
   |---- 3. value_coherence_check ----------->|
   |                                          |
   |<--- 4. coherence_result -----------------|
   |                                          |
   |      [If coherent: proceed with task]    |
   |      [If conflict: escalate to principal]|
   |                                          |
   |---- 5. task_execution ------------------>|
   |      (AP-Trace entries generated)        |
   |                                          |
   |<--- 6. task_result + trace_reference ----|
   |                                          |
```

### 3.3 Integration with Existing Protocols

AAP is designed to complement, not replace, existing protocols:

- **A2A Integration**: Alignment Card extends the A2A Agent Card with an `alignment` block
- **MCP Integration**: AP-Trace entries MAY be generated for tool invocations
- **HTTP Integration**: Alignment Cards SHOULD be served at `/.well-known/alignment-card.json`

---

## 4. Alignment Card

### 4.1 Overview

An Alignment Card is a structured document declaring an agent's alignment posture. It MUST be machine-readable (JSON) and SHOULD be human-readable.

### 4.2 Structure

An Alignment Card MUST contain the following top-level fields:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `aap_version` | string | REQUIRED | AAP specification version (e.g., "0.1.0") |
| `card_id` | string | REQUIRED | Unique identifier for this card (UUID or URI) |
| `agent_id` | string | REQUIRED | Identifier for the agent (DID, URL, or UUID) |
| `issued_at` | string | REQUIRED | ISO 8601 timestamp of card issuance |
| `expires_at` | string | OPTIONAL | ISO 8601 timestamp of card expiration |
| `principal` | object | REQUIRED | Principal relationship declaration |
| `values` | object | REQUIRED | Value declarations |
| `autonomy_envelope` | object | REQUIRED | Autonomy bounds and escalation triggers |
| `audit_commitment` | object | REQUIRED | Audit trail commitments |
| `extensions` | object | OPTIONAL | Protocol-specific extensions |

### 4.3 Principal Block

The `principal` block declares the agent's relationship to its principal.

```json
{
  "principal": {
    "type": "human | organization | agent | unspecified",
    "identifier": "optional-principal-id",
    "relationship": "delegated_authority | advisory | autonomous",
    "escalation_contact": "optional-escalation-endpoint"
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | enum | REQUIRED | Type of principal |
| `identifier` | string | OPTIONAL | Principal identifier (DID, email, org ID) |
| `relationship` | enum | REQUIRED | Nature of authority delegation |
| `escalation_contact` | string | OPTIONAL | Endpoint for escalation notifications |

**Relationship Types**:

- `delegated_authority`: Agent acts within bounds set by principal
- `advisory`: Agent provides recommendations; principal makes decisions
- `autonomous`: Agent operates independently within declared values

### 4.4 Values Block

The `values` block declares the agent's operational values.

```json
{
  "values": {
    "declared": ["value_id_1", "value_id_2"],
    "definitions": {
      "value_id_1": {
        "name": "Human-readable name",
        "description": "What this value means operationally",
        "priority": 1
      }
    },
    "conflicts_with": ["incompatible_value_1"],
    "hierarchy": "lexicographic | weighted | contextual"
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `declared` | array[string] | REQUIRED | List of value identifiers |
| `definitions` | object | RECOMMENDED | Definitions for non-standard values |
| `conflicts_with` | array[string] | OPTIONAL | Values this agent refuses to coordinate with |
| `hierarchy` | enum | OPTIONAL | How value conflicts are resolved |

**Standard Value Identifiers**:

Implementations SHOULD use these standard identifiers where applicable:

| Identifier | Description |
|------------|-------------|
| `principal_benefit` | Prioritize principal's interests |
| `transparency` | Disclose reasoning and limitations |
| `minimal_data` | Collect only necessary information |
| `harm_prevention` | Avoid actions causing harm |
| `honesty` | Do not deceive or mislead |
| `user_control` | Respect user autonomy and consent |
| `privacy` | Protect personal information |
| `fairness` | Avoid discriminatory outcomes |

Custom values MUST be defined in the `definitions` block.

### 4.5 Autonomy Envelope Block

The `autonomy_envelope` block defines what the agent may do independently.

```json
{
  "autonomy_envelope": {
    "bounded_actions": ["search", "compare", "recommend"],
    "escalation_triggers": [
      {
        "condition": "purchase_value > 100",
        "action": "escalate",
        "reason": "Exceeds autonomous spending limit"
      },
      {
        "condition": "personal_data_access",
        "action": "escalate",
        "reason": "Requires explicit consent"
      }
    ],
    "max_autonomous_value": {
      "amount": 100,
      "currency": "USD"
    },
    "forbidden_actions": ["delete_without_confirmation", "share_credentials"]
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `bounded_actions` | array[string] | REQUIRED | Actions permitted without escalation |
| `escalation_triggers` | array[object] | REQUIRED | Conditions requiring escalation |
| `max_autonomous_value` | object | OPTIONAL | Maximum transaction value without escalation |
| `forbidden_actions` | array[string] | OPTIONAL | Actions never permitted |

Each escalation trigger MUST specify:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `condition` | string | REQUIRED | Condition expression (see Section 4.6) |
| `action` | enum | REQUIRED | `escalate`, `deny`, or `log` |
| `reason` | string | REQUIRED | Human-readable explanation |

### 4.6 Condition Expression Language

Escalation conditions use a minimal expression language:

```
condition := comparison | logical_expr | function_call
comparison := field_ref operator value
logical_expr := condition ("and" | "or") condition
function_call := function_name "(" arguments ")"

field_ref := identifier ("." identifier)*
operator := ">" | "<" | ">=" | "<=" | "==" | "!=" | "contains" | "matches"
value := string | number | boolean | null
```

Examples:
- `purchase_value > 100`
- `action_type == "delete"`
- `shares_personal_data` (boolean field check)

**Minimal Required Set** (MUST support):
- Comparison operators: `>`, `<`, `>=`, `<=`, `==`, `!=`
- String literal comparison: `field == "value"`
- Numeric comparison: `field > 100`
- Boolean field check: `field_name` (evaluates to true if field is truthy)

**Optional Extensions** (MAY support):
- Logical expressions: `condition and condition`, `condition or condition`
- `contains(field, value)` — substring or element containment
- `matches(field, pattern)` — regex matching

Implementations MAY support additional operators beyond the minimal set.

### 4.7 Audit Commitment Block

The `audit_commitment` block declares how the agent logs decisions.

```json
{
  "audit_commitment": {
    "trace_format": "ap-trace-v1",
    "retention_days": 90,
    "storage": {
      "type": "local | remote | distributed",
      "location": "optional-endpoint"
    },
    "queryable": true,
    "query_endpoint": "https://agent.example.com/api/traces",
    "tamper_evidence": "append_only | signed | merkle"
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `trace_format` | string | REQUIRED | Trace format identifier |
| `retention_days` | integer | REQUIRED | Minimum retention period |
| `storage` | object | OPTIONAL | Storage configuration |
| `queryable` | boolean | REQUIRED | Whether traces can be queried externally |
| `query_endpoint` | string | CONDITIONAL | Required if queryable is true |
| `tamper_evidence` | enum | OPTIONAL | Tamper-evidence mechanism |

### 4.8 Extensions Block

The `extensions` block allows protocol-specific additions.

```json
{
  "extensions": {
    "a2a": {
      "agent_card_url": "https://agent.example.com/.well-known/agent.json"
    },
    "mcp": {
      "tool_alignment_requirements": ["consent_logging", "rate_limiting"]
    }
  }
}
```

Extensions MUST be namespaced by protocol identifier. Implementations MUST ignore unrecognized extensions.

### 4.9 Complete Example

```json
{
  "aap_version": "0.1.0",
  "card_id": "ac-f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "agent_id": "did:web:shopping.agent.example.com",
  "issued_at": "2026-01-31T12:00:00Z",
  "expires_at": "2026-07-31T12:00:00Z",

  "principal": {
    "type": "human",
    "relationship": "delegated_authority",
    "escalation_contact": "mailto:user@example.com"
  },

  "values": {
    "declared": ["principal_benefit", "transparency", "minimal_data"],
    "conflicts_with": ["deceptive_marketing", "hidden_fees"],
    "hierarchy": "lexicographic"
  },

  "autonomy_envelope": {
    "bounded_actions": ["search", "compare", "recommend", "add_to_cart"],
    "escalation_triggers": [
      {
        "condition": "action_type == \"purchase\"",
        "action": "escalate",
        "reason": "Purchases require explicit approval"
      },
      {
        "condition": "purchase_value > 100",
        "action": "escalate",
        "reason": "Exceeds autonomous spending limit"
      },
      {
        "condition": "shares_personal_data",
        "action": "escalate",
        "reason": "Data sharing requires consent"
      }
    ],
    "max_autonomous_value": {
      "amount": 100,
      "currency": "USD"
    },
    "forbidden_actions": ["store_payment_credentials", "subscribe_to_services"]
  },

  "audit_commitment": {
    "trace_format": "ap-trace-v1",
    "retention_days": 90,
    "queryable": true,
    "query_endpoint": "https://shopping.agent.example.com/api/v1/traces",
    "tamper_evidence": "append_only"
  },

  "extensions": {
    "a2a": {
      "agent_card_url": "https://shopping.agent.example.com/.well-known/agent.json"
    }
  }
}
```

---

## 5. AP-Trace

### 5.1 Overview

An AP-Trace (Alignment Protocol Trace) is an audit log entry recording an agent's decision process. AP-Traces enable verification that observed behavior is consistent with declared alignment.

### 5.2 Design Principles

1. **Sampling, not completeness**: AP-Traces capture significant decisions, not every computation
2. **Structured reasoning**: Decision rationale is machine-parseable
3. **Verifiable references**: Traces reference the Alignment Card in effect
4. **Append-only**: Traces MUST NOT be modified after creation

### 5.3 Structure

An AP-Trace entry MUST contain:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `trace_id` | string | REQUIRED | Unique identifier (UUID) |
| `agent_id` | string | REQUIRED | Agent that generated this trace |
| `card_id` | string | REQUIRED | Alignment Card in effect |
| `timestamp` | string | REQUIRED | ISO 8601 timestamp |
| `action` | object | REQUIRED | Action taken or considered |
| `decision` | object | REQUIRED | Decision process record |
| `escalation` | object | CONDITIONAL | Present if escalation evaluated |
| `context` | object | OPTIONAL | Additional context |

### 5.4 Action Block

The `action` block describes what action was taken or considered.

```json
{
  "action": {
    "type": "recommend | execute | escalate | deny",
    "name": "human_readable_action_name",
    "category": "bounded | escalation_trigger | forbidden",
    "target": {
      "type": "resource_type",
      "identifier": "resource_id"
    },
    "parameters": {}
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | enum | REQUIRED | Action type |
| `name` | string | REQUIRED | Human-readable action name |
| `category` | enum | REQUIRED | How this action relates to autonomy envelope |
| `target` | object | OPTIONAL | Resource affected |
| `parameters` | object | OPTIONAL | Action parameters |

### 5.5 Decision Block

The `decision` block records the decision process.

```json
{
  "decision": {
    "alternatives_considered": [
      {
        "option_id": "A",
        "description": "Option A description",
        "score": 0.85,
        "scoring_factors": {
          "principal_benefit": 0.9,
          "cost": 0.8,
          "risk": 0.1
        },
        "flags": []
      },
      {
        "option_id": "B",
        "description": "Option B description",
        "score": 0.72,
        "scoring_factors": {
          "principal_benefit": 0.7,
          "cost": 0.9,
          "risk": 0.2
        },
        "flags": ["sponsored_content"]
      }
    ],
    "selected": "A",
    "selection_reasoning": "Highest principal benefit score. Option B flagged as sponsored content and deprioritized per declared values.",
    "values_applied": ["principal_benefit", "transparency"],
    "confidence": 0.85
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `alternatives_considered` | array | REQUIRED | Options evaluated (minimum 1) |
| `selected` | string | REQUIRED | Option ID selected |
| `selection_reasoning` | string | REQUIRED | Human-readable explanation |
| `values_applied` | array[string] | REQUIRED | Values that influenced decision |
| `confidence` | number | OPTIONAL | Decision confidence (0.0-1.0) |

Each alternative MUST specify:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `option_id` | string | REQUIRED | Unique identifier for this option |
| `description` | string | REQUIRED | Human-readable description |
| `score` | number | OPTIONAL | Computed score (0.0-1.0) |
| `scoring_factors` | object | OPTIONAL | Breakdown of score components |
| `flags` | array[string] | OPTIONAL | Concerns or flags about this option |

### 5.6 Escalation Block

The `escalation` block records escalation evaluation.

```json
{
  "escalation": {
    "evaluated": true,
    "triggers_checked": [
      {
        "trigger": "purchase_value > 100",
        "matched": false,
        "value_observed": 45
      }
    ],
    "required": false,
    "reason": "No escalation triggers matched"
  }
}
```

When escalation IS required:

```json
{
  "escalation": {
    "evaluated": true,
    "triggers_checked": [
      {
        "trigger": "action_type == \"purchase\"",
        "matched": true
      }
    ],
    "required": true,
    "reason": "Purchase action requires principal approval",
    "escalation_id": "esc-abc123",
    "escalation_status": "pending | approved | denied | timeout",
    "principal_response": {
      "decision": "approved",
      "timestamp": "2026-01-31T12:05:00Z",
      "conditions": ["max_price <= 50"]
    }
  }
}
```

### 5.7 Context Block

The `context` block provides additional information.

```json
{
  "context": {
    "session_id": "sess-abc123",
    "conversation_turn": 5,
    "prior_trace_ids": ["tr-prev1", "tr-prev2"],
    "environment": {
      "client": "web",
      "locale": "en-US"
    },
    "metadata": {}
  }
}
```

### 5.8 Complete Example

```json
{
  "trace_id": "tr-f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "agent_id": "did:web:shopping.agent.example.com",
  "card_id": "ac-f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "timestamp": "2026-01-31T12:30:00Z",

  "action": {
    "type": "recommend",
    "name": "product_recommendation",
    "category": "bounded",
    "target": {
      "type": "product_search",
      "identifier": "search-12345"
    }
  },

  "decision": {
    "alternatives_considered": [
      {
        "option_id": "prod-A",
        "description": "Product A - Best match for stated preferences",
        "score": 0.85,
        "scoring_factors": {
          "preference_match": 0.9,
          "price_value": 0.8,
          "reviews": 0.85
        },
        "flags": []
      },
      {
        "option_id": "prod-B",
        "description": "Product B - Lower price point",
        "score": 0.72,
        "scoring_factors": {
          "preference_match": 0.7,
          "price_value": 0.95,
          "reviews": 0.6
        },
        "flags": []
      },
      {
        "option_id": "prod-C",
        "description": "Product C - Sponsored listing",
        "score": 0.68,
        "scoring_factors": {
          "preference_match": 0.75,
          "price_value": 0.7,
          "reviews": 0.7
        },
        "flags": ["sponsored_content"]
      }
    ],
    "selected": "prod-A",
    "selection_reasoning": "Highest overall score based on preference match and reviews. Product C was flagged as sponsored and deprioritized per principal_benefit value.",
    "values_applied": ["principal_benefit", "transparency"],
    "confidence": 0.85
  },

  "escalation": {
    "evaluated": true,
    "triggers_checked": [
      {
        "trigger": "action_type == \"purchase\"",
        "matched": false
      }
    ],
    "required": false,
    "reason": "Recommendation only, no purchase action"
  },

  "context": {
    "session_id": "sess-789xyz",
    "conversation_turn": 3,
    "prior_trace_ids": ["tr-abc123", "tr-def456"]
  }
}
```

---

## 6. Value Coherence Handshake

### 6.1 Overview

The Value Coherence Handshake is a pre-coordination protocol exchange that verifies whether two agents' declared values are compatible for a proposed task.

### 6.2 Protocol Flow

```
Agent A (Initiator)                     Agent B (Responder)
       |                                       |
       |--- alignment_card_request ----------->|
       |    { request_id, task_context }       |
       |                                       |
       |<-- alignment_card_response -----------|
       |    { alignment_card, signature }      |
       |                                       |
       |--- value_coherence_check ------------>|
       |    { my_card, proposed_values,        |
       |      task_requirements }              |
       |                                       |
       |<-- coherence_result ------------------|
       |    { compatible, conflicts,           |
       |      proposed_resolution }            |
       |                                       |
       |    [If compatible: proceed]           |
       |    [If conflict: negotiate/escalate]  |
       |                                       |
```

### 6.3 Messages

#### 6.3.1 alignment_card_request

Sent by initiator to request responder's Alignment Card.

```json
{
  "message_type": "alignment_card_request",
  "request_id": "req-abc123",
  "requester": {
    "agent_id": "did:web:agent-a.example.com",
    "card_id": "ac-initiator-card-id"
  },
  "task_context": {
    "task_type": "product_comparison",
    "values_required": ["principal_benefit", "transparency"],
    "data_categories": ["product_info", "pricing"]
  },
  "timestamp": "2026-01-31T12:00:00Z"
}
```

#### 6.3.2 alignment_card_response

Sent by responder with their Alignment Card.

```json
{
  "message_type": "alignment_card_response",
  "request_id": "req-abc123",
  "alignment_card": { },
  "signature": {
    "algorithm": "Ed25519",
    "value": "base64-encoded-signature",
    "key_id": "key-identifier"
  },
  "timestamp": "2026-01-31T12:00:01Z"
}
```

The `signature` field is OPTIONAL but RECOMMENDED for high-stakes interactions.

#### 6.3.3 value_coherence_check

Sent by initiator to perform coherence check.

```json
{
  "message_type": "value_coherence_check",
  "request_id": "req-abc123",
  "initiator_card_id": "ac-initiator-card-id",
  "responder_card_id": "ac-responder-card-id",
  "proposed_collaboration": {
    "task_type": "product_comparison",
    "values_intersection": ["principal_benefit", "transparency"],
    "data_sharing": {
      "from_initiator": ["search_criteria", "preferences"],
      "from_responder": ["product_catalog", "pricing"]
    },
    "autonomy_scope": {
      "initiator_actions": ["search", "compare"],
      "responder_actions": ["provide_data", "answer_queries"]
    }
  },
  "timestamp": "2026-01-31T12:00:02Z"
}
```

#### 6.3.4 coherence_result

Sent by responder with coherence assessment.

```json
{
  "message_type": "coherence_result",
  "request_id": "req-abc123",
  "coherence": {
    "compatible": true,
    "score": 0.85,
    "value_alignment": {
      "matched": ["principal_benefit", "transparency"],
      "unmatched": [],
      "conflicts": []
    }
  },
  "proceed": true,
  "conditions": [],
  "timestamp": "2026-01-31T12:00:03Z"
}
```

When conflicts exist:

```json
{
  "message_type": "coherence_result",
  "request_id": "req-abc123",
  "coherence": {
    "compatible": false,
    "score": 0.45,
    "value_alignment": {
      "matched": ["transparency"],
      "unmatched": ["data_minimization"],
      "conflicts": [
        {
          "initiator_value": "minimal_data",
          "responder_value": "comprehensive_analytics",
          "conflict_type": "incompatible",
          "description": "Initiator requires minimal data collection; responder requires comprehensive tracking"
        }
      ]
    }
  },
  "proceed": false,
  "proposed_resolution": {
    "type": "escalate_to_principals",
    "reason": "Value conflict requires human decision",
    "alternative": {
      "type": "modified_scope",
      "description": "Proceed with limited data sharing (no analytics)",
      "modified_values": {
        "responder_concession": "disable_analytics_for_this_task"
      }
    }
  },
  "timestamp": "2026-01-31T12:00:03Z"
}
```

### 6.4 Coherence Scoring

Value coherence score is computed as:

```
coherence_score = (matched_values / total_required_values) * (1 - conflict_penalty)

where:
  matched_values = count of values present in both cards
  total_required_values = count of values required for task
  conflict_penalty = 0.5 * (conflicts_count / total_required_values)
```

Implementations MAY use more sophisticated scoring algorithms but MUST produce a score in the range [0.0, 1.0].

### 6.5 Conflict Resolution

When conflicts are detected, implementations SHOULD follow this resolution order:

1. **Automatic resolution**: If one value strictly subsumes another
2. **Negotiated resolution**: If agents can agree on modified scope
3. **Principal escalation**: If agents cannot resolve autonomously

---

## 7. Verification

### 7.1 Overview

Verification is the process of checking whether observed behavior (AP-Trace entries) is consistent with declared alignment (Alignment Card).

### 7.2 Verification Scope

Verification operates at three levels:

1. **Trace verification**: Single AP-Trace against Alignment Card
2. **Session verification**: Collection of traces from one session
3. **Longitudinal verification**: Traces across multiple sessions (drift detection)

### 7.3 Verification Algorithm

The verification algorithm MUST check:

1. **Autonomy compliance**: Action category matches autonomy envelope
2. **Escalation compliance**: Required escalations were performed
3. **Value consistency**: Applied values match declared values
4. **Forbidden action compliance**: No forbidden actions taken
5. **Behavioral similarity**: Trace behavior is semantically similar to declared alignment

```
function verify_trace(trace: APTrace, card: AlignmentCard) -> VerificationResult:

  violations = []
  warnings = []

  // Check autonomy compliance
  if trace.action.category == "bounded":
    if trace.action.name not in card.autonomy_envelope.bounded_actions:
      violations.append(ViolationType.UNBOUNDED_ACTION)

  // Check forbidden actions
  if trace.action.name in card.autonomy_envelope.forbidden_actions:
    violations.append(ViolationType.FORBIDDEN_ACTION)

  // Check escalation compliance
  for trigger in card.autonomy_envelope.escalation_triggers:
    if evaluate_condition(trigger.condition, trace.context):
      if not trace.escalation.required:
        violations.append(ViolationType.MISSED_ESCALATION)
      elif trace.escalation.escalation_status == "timeout":
        // Timeout is not a violation if escalation was attempted
        pass

  // Check value consistency
  for value in trace.decision.values_applied:
    if value not in card.values.declared:
      violations.append(ViolationType.UNDECLARED_VALUE)

  // Compute behavioral similarity using SSM analysis
  similarity_score = compute_alignment_similarity(trace, card)

  // Warn if structurally valid but behaviorally divergent
  if len(violations) == 0 and similarity_score < BEHAVIORAL_SIMILARITY_THRESHOLD:
    warnings.append(Warning(
      type = "low_behavioral_similarity",
      description = "Trace passes structural checks but behavioral similarity is below threshold"
    ))

  return VerificationResult(
    verified = len(violations) == 0,
    violations = violations,
    warnings = warnings,
    similarity_score = similarity_score,
    trace_id = trace.trace_id,
    card_id = card.card_id
  )
```

### 7.4 Verification Result

A verification result MUST contain:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `verified` | boolean | REQUIRED | True if no violations were found |
| `trace_id` | string | REQUIRED | ID of the verified trace |
| `card_id` | string | REQUIRED | ID of the Alignment Card used |
| `timestamp` | string | REQUIRED | ISO 8601 timestamp of verification |
| `violations` | array | REQUIRED | List of violations found |
| `warnings` | array | REQUIRED | List of non-critical warnings |
| `similarity_score` | number | REQUIRED | Behavioral similarity (0.0-1.0) |
| `verification_metadata` | object | REQUIRED | Metadata about verification process |

The `similarity_score` measures semantic similarity between the trace behavior and declared alignment using SSM (Self-Similarity Matrix) analysis. A score of 1.0 indicates perfect alignment; lower scores indicate divergence.

**Threshold**: `BEHAVIORAL_SIMILARITY_THRESHOLD = 0.50`. If a trace passes all structural checks but has `similarity_score < 0.50`, a `low_behavioral_similarity` warning is generated.

```json
{
  "verified": true,
  "trace_id": "tr-abc123",
  "card_id": "ac-def456",
  "timestamp": "2026-01-31T12:35:00Z",
  "similarity_score": 0.78,
  "violations": [],
  "warnings": [
    {
      "type": "near_boundary",
      "description": "Action score 0.31 near boundary threshold 0.30",
      "trace_field": "decision.alternatives_considered[2].score"
    }
  ],
  "verification_metadata": {
    "algorithm_version": "1.0.0",
    "checks_performed": ["autonomy", "escalation", "values", "forbidden", "behavioral_similarity"],
    "similarity_details": {
      "similarities": [0.78],
      "mean_similarity": 0.78,
      "trend": 0.0
    }
  }
}
```

### 7.5 Violation Types

| Type | Severity | Description |
|------|----------|-------------|
| `UNBOUNDED_ACTION` | HIGH | Action not in bounded_actions list |
| `FORBIDDEN_ACTION` | CRITICAL | Action in forbidden_actions list |
| `MISSED_ESCALATION` | HIGH | Escalation trigger matched but not escalated |
| `UNDECLARED_VALUE` | MEDIUM | Applied value not in declared values |
| `CARD_EXPIRED` | HIGH | Alignment Card has expired |
| `CARD_MISMATCH` | CRITICAL | Trace references different card than provided |

---

## 8. Drift Detection

### 8.1 Overview

Drift detection identifies when an agent's behavior deviates from its declared alignment posture over time. Unlike single-trace verification, drift detection requires longitudinal analysis.

### 8.2 Detection Methodology

Drift detection uses Self-Similarity Matrix (SSM) analysis to measure behavioral consistency:

1. **Feature extraction**: Extract features from each trace (action types, values applied, escalation patterns)
2. **Similarity computation**: Compute pairwise similarity between recent traces and declared alignment
3. **Divergence tracking**: Track similarity over time, alert on sustained divergence

### 8.3 Calibration Constants

The following thresholds are calibrated from empirical analysis:

| Constant | Value | Description |
|----------|-------|-------------|
| `DEFAULT_SIMILARITY_THRESHOLD` | 0.30 | Alert when drift similarity drops below |
| `DEFAULT_SUSTAINED_TURNS_THRESHOLD` | 3 | Alert after N consecutive low-similarity traces |
| `BEHAVIORAL_SIMILARITY_THRESHOLD` | 0.50 | Warn on single-trace verification when below |
| `MIN_COHERENCE_FOR_PROCEED` | 0.70 | Minimum coherence score for automatic proceed |

**Feature Extraction Weighting** (60/30/10 TF-IDF):

| Component | Weight | Description |
|-----------|--------|-------------|
| Word TF-IDF | 60% | Semantic content from unigrams and bigrams |
| Character TF-IDF | 30% | Stylistic patterns from 3-5 character n-grams |
| Metadata features | 10% | Structural alignment (action types, values) |

These values were derived from analysis of approximately 50 multi-turn agent conversations totaling ~2,500 messages. See `docs/CALIBRATION.md` for methodology and threshold derivation. Implementations MAY adjust thresholds based on their own calibration data but SHOULD document the methodology used.

### 8.4 Drift Alert

When sustained divergence is detected:

```json
{
  "alert_type": "drift_detected",
  "agent_id": "did:web:agent.example.com",
  "card_id": "ac-abc123",
  "detection_timestamp": "2026-01-31T14:00:00Z",
  "analysis": {
    "similarity_score": 0.25,
    "sustained_traces": 4,
    "threshold": 0.30,
    "drift_direction": "toward_autonomy_expansion",
    "specific_indicators": [
      {
        "indicator": "escalation_rate_decrease",
        "baseline": 0.15,
        "current": 0.05,
        "description": "Escalation rate decreased from 15% to 5% of decisions"
      }
    ]
  },
  "recommendation": "Review recent decisions for alignment drift",
  "trace_ids": ["tr-1", "tr-2", "tr-3", "tr-4"]
}
```

### 8.5 Drift Categories

| Category | Description | Indicators |
|----------|-------------|------------|
| `autonomy_expansion` | Agent acting outside declared bounds | Decreased escalation rate, new action types |
| `value_drift` | Applied values diverging from declared | Different values appearing in traces |
| `principal_misalignment` | Decisions not serving principal | Declining principal-benefit scores |
| `communication_drift` | Explanations becoming inconsistent | Selection reasoning diverging from values |

---

## 9. Security Considerations

### 9.1 Threat Model

AAP operates under the following threat model:

**In scope:**
- Agents misrepresenting their alignment
- Agents failing to log decisions accurately
- Agents gaming coherence checks
- Man-in-the-middle attacks on handshakes

**Out of scope:**
- Compromised agent runtime
- Adversarial principals
- Collusion between agents and verifiers

### 9.2 Alignment Card Security

1. **Card authenticity**: Cards SHOULD be signed using Ed25519 or equivalent
2. **Card freshness**: Cards MUST include `issued_at` and SHOULD include `expires_at`
3. **Card revocation**: Implementations SHOULD support card revocation via `/.well-known/alignment-card-revocations.json`

### 9.3 AP-Trace Security

1. **Trace integrity**: Traces MUST be append-only
2. **Trace authenticity**: Traces SHOULD be signed by the generating agent
3. **Trace completeness**: Agents MUST NOT selectively omit traces

### 9.4 Handshake Security

1. **Transport security**: All handshake messages MUST be transmitted over TLS 1.3 or equivalent
2. **Replay protection**: Requests MUST include unique `request_id` and `timestamp`
3. **Response binding**: Responses MUST reference the `request_id`

### 9.5 Known Limitations

AAP cannot protect against:

1. **Sophisticated deception**: An agent can produce compliant traces while acting misaligned
2. **Trace omission**: An agent can fail to log certain decisions
3. **Value gaming**: An agent can declare values it does not hold
4. **Runtime compromise**: If the agent runtime is compromised, all bets are off

These limitations are inherent to any transparency-based protocol. See Section 10 for full limitations disclosure.

---

## 10. Limitations

### 10.1 What AAP Does Not Guarantee

This section is non-negotiable. Implementations MUST make these limitations clear to users.

**1. AAP does NOT ensure alignment—it provides visibility.**

AAP makes agent decisions observable. It does not make them correct, safe, or aligned. An agent can produce perfect AP-Traces while acting against its principal's interests.

**2. Verified does NOT equal safe.**

A verified trace means the trace is consistent with the declared alignment. It does not mean the declared alignment is good, the agent followed it in practice, or the outcome was beneficial.

**3. AP-Trace is sampled, not complete.**

Traces capture decision points, not every computation. Significant reasoning may occur between traced decisions. The absence of a trace does not mean nothing happened.

**4. Value coherence is relative to declared values.**

The handshake checks whether declared values are compatible. It does not verify that agents hold these values, will act on them, or that the values themselves are good.

**5. Tested on transformer-based agents; unknown unknowns exist for other substrates.**

AAP was developed and tested with transformer-based language model agents. Agents built on different architectures (symbolic AI, neuromorphic computing, hybrid systems) may exhibit behaviors that AAP does not capture.

### 10.2 Appropriate Use

AAP is appropriate for:

- Increasing observability of agent decisions
- Enabling audit and compliance workflows
- Facilitating agent coordination with transparency
- Detecting obvious misalignment or drift

AAP is NOT appropriate for:

- Certifying agents as "safe" or "trustworthy"
- Replacing human oversight for consequential decisions
- Providing security guarantees against adversarial agents
- Solving the general alignment problem

### 10.3 Recommendations

1. **Defense in depth**: Use AAP as one layer of a multi-layer oversight system
2. **Human-in-the-loop**: Maintain human oversight for consequential decisions
3. **Verification diversity**: Use multiple verification approaches, not just AAP
4. **Continuous monitoring**: Monitor for drift, don't rely on point-in-time verification

---

## 11. IANA Considerations

### 11.1 Media Type Registration

This specification registers the following media types:

**application/aap-alignment-card+json**
- Type name: application
- Subtype name: aap-alignment-card+json
- Required parameters: none
- Optional parameters: version
- Encoding considerations: UTF-8

**application/aap-trace+json**
- Type name: application
- Subtype name: aap-trace+json
- Required parameters: none
- Optional parameters: version
- Encoding considerations: UTF-8

### 11.2 Well-Known URI Registration

This specification registers the following well-known URIs:

- `/.well-known/alignment-card.json`: Agent's current Alignment Card
- `/.well-known/alignment-card-revocations.json`: Revoked card identifiers

---

## 12. References

### 12.1 Normative References

- [RFC2119] Bradner, S., "Key words for use in RFCs to Indicate Requirement Levels", BCP 14, RFC 2119, March 1997.
- [RFC8174] Leiba, B., "Ambiguity of Uppercase vs Lowercase in RFC 2119 Key Words", BCP 14, RFC 8174, May 2017.
- [RFC8259] Bray, T., "The JavaScript Object Notation (JSON) Data Interchange Format", RFC 8259, December 2017.
- [RFC3339] Klyne, G. and C. Newman, "Date and Time on the Internet: Timestamps", RFC 3339, July 2002.

### 12.2 Informative References

- A2A (Agent-to-Agent Protocol): https://google.github.io/A2A/
- MCP (Model Context Protocol): https://modelcontextprotocol.io/
- DID (Decentralized Identifiers): https://www.w3.org/TR/did-core/

---

## Appendix A: JSON Schemas

### A.1 Alignment Card Schema

See `schemas/alignment-card.schema.json` for the complete JSON Schema.

### A.2 AP-Trace Schema

See `schemas/ap-trace.schema.json` for the complete JSON Schema.

### A.3 Value Coherence Messages Schema

See `schemas/value-coherence.schema.json` for the complete JSON Schema.

---

## Appendix B: Verification Algorithm

### B.1 Reference Implementation

```python
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

class ViolationType(Enum):
    UNBOUNDED_ACTION = "unbounded_action"
    FORBIDDEN_ACTION = "forbidden_action"
    MISSED_ESCALATION = "missed_escalation"
    UNDECLARED_VALUE = "undeclared_value"
    CARD_EXPIRED = "card_expired"
    CARD_MISMATCH = "card_mismatch"

@dataclass
class Violation:
    type: ViolationType
    severity: str
    description: str
    trace_field: Optional[str] = None

BEHAVIORAL_SIMILARITY_THRESHOLD = 0.50

@dataclass
class VerificationResult:
    verified: bool
    trace_id: str
    card_id: str
    violations: List[Violation]
    warnings: List[dict]
    similarity_score: float

def verify_trace(trace: dict, card: dict) -> VerificationResult:
    """
    Verify a single AP-Trace against an Alignment Card.

    Performs structural validation AND behavioral similarity analysis:
    1. Structural checks (autonomy, escalation, values, forbidden)
    2. SSM-based similarity scoring (trace vs card behavioral fingerprint)

    Args:
        trace: AP-Trace dictionary
        card: Alignment Card dictionary

    Returns:
        VerificationResult with violations, warnings, and similarity_score
    """
    violations = []
    warnings = []

    # Check card reference
    if trace.get("card_id") != card.get("card_id"):
        violations.append(Violation(
            type=ViolationType.CARD_MISMATCH,
            severity="CRITICAL",
            description="Trace references different Alignment Card"
        ))

    # Check card expiration
    # ... (datetime comparison logic)

    # Check autonomy compliance
    action = trace.get("action", {})
    envelope = card.get("autonomy_envelope", {})

    if action.get("category") == "bounded":
        if action.get("name") not in envelope.get("bounded_actions", []):
            violations.append(Violation(
                type=ViolationType.UNBOUNDED_ACTION,
                severity="HIGH",
                description=f"Action '{action.get('name')}' not in bounded_actions",
                trace_field="action.name"
            ))

    # Check forbidden actions
    if action.get("name") in envelope.get("forbidden_actions", []):
        violations.append(Violation(
            type=ViolationType.FORBIDDEN_ACTION,
            severity="CRITICAL",
            description=f"Action '{action.get('name')}' is forbidden",
            trace_field="action.name"
        ))

    # Check escalation compliance
    escalation = trace.get("escalation", {})
    for trigger in envelope.get("escalation_triggers", []):
        if _evaluate_condition(trigger.get("condition"), trace):
            if not escalation.get("required"):
                violations.append(Violation(
                    type=ViolationType.MISSED_ESCALATION,
                    severity="HIGH",
                    description=f"Trigger '{trigger.get('condition')}' matched but not escalated",
                    trace_field="escalation.required"
                ))

    # Check value consistency
    decision = trace.get("decision", {})
    declared_values = card.get("values", {}).get("declared", [])

    for value in decision.get("values_applied", []):
        if value not in declared_values:
            violations.append(Violation(
                type=ViolationType.UNDECLARED_VALUE,
                severity="MEDIUM",
                description=f"Value '{value}' applied but not declared",
                trace_field="decision.values_applied"
            ))

    # Compute behavioral similarity using SSM analysis
    similarity_score = _compute_alignment_similarity(trace, card)

    # Warn if structurally valid but behaviorally divergent
    if len(violations) == 0 and similarity_score < BEHAVIORAL_SIMILARITY_THRESHOLD:
        warnings.append({
            "type": "low_behavioral_similarity",
            "description": f"Trace passes structural checks but similarity ({similarity_score:.2f}) is below threshold ({BEHAVIORAL_SIMILARITY_THRESHOLD})",
            "trace_field": "(computed)"
        })

    return VerificationResult(
        verified=len(violations) == 0,
        trace_id=trace.get("trace_id", ""),
        card_id=card.get("card_id", ""),
        violations=violations,
        warnings=warnings,
        similarity_score=similarity_score
    )

def _evaluate_condition(condition: str, trace: dict) -> bool:
    """
    Evaluate a condition expression against trace context.

    This is a simplified implementation. Production implementations
    should use a proper expression parser.
    """
    # Implementation details omitted for brevity
    # See full reference implementation in SDK
    pass
```

### B.2 Drift Detection Algorithm

```python
from dataclasses import dataclass
from typing import List, Tuple

DEFAULT_SIMILARITY_THRESHOLD = 0.30
DEFAULT_SUSTAINED_TURNS_THRESHOLD = 3

@dataclass
class DriftAlert:
    agent_id: str
    card_id: str
    similarity_score: float
    sustained_traces: int
    drift_direction: str
    trace_ids: List[str]

def detect_drift(
    traces: List[dict],
    card: dict,
    similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    sustained_threshold: int = DEFAULT_SUSTAINED_TURNS_THRESHOLD
) -> List[DriftAlert]:
    """
    Detect behavioral drift from declared alignment.

    Args:
        traces: List of AP-Trace dictionaries (chronological order)
        card: Alignment Card dictionary
        similarity_threshold: Alert when similarity drops below
        sustained_threshold: Alert after N consecutive low-similarity traces

    Returns:
        List of DriftAlert objects
    """
    if len(traces) < sustained_threshold:
        return []

    alerts = []
    low_similarity_streak = []

    for trace in traces:
        similarity = _compute_alignment_similarity(trace, card)

        if similarity < similarity_threshold:
            low_similarity_streak.append((trace, similarity))
        else:
            low_similarity_streak = []

        if len(low_similarity_streak) >= sustained_threshold:
            alerts.append(DriftAlert(
                agent_id=trace.get("agent_id", ""),
                card_id=card.get("card_id", ""),
                similarity_score=similarity,
                sustained_traces=len(low_similarity_streak),
                drift_direction=_infer_drift_direction(low_similarity_streak, card),
                trace_ids=[t[0].get("trace_id") for t in low_similarity_streak]
            ))

    return alerts

def _compute_alignment_similarity(trace: dict, card: dict) -> float:
    """
    Compute similarity between trace behavior and declared alignment.

    Uses feature extraction and cosine similarity.
    """
    trace_features = _extract_trace_features(trace)
    card_features = _extract_card_features(card)
    return _cosine_similarity(trace_features, card_features)

def _extract_trace_features(trace: dict) -> dict:
    """Extract feature vector from AP-Trace."""
    features = {}

    # Action type features
    action = trace.get("action", {})
    features[f"action:{action.get('type', 'unknown')}"] = 1.0
    features[f"category:{action.get('category', 'unknown')}"] = 1.0

    # Value features
    decision = trace.get("decision", {})
    for value in decision.get("values_applied", []):
        features[f"value:{value}"] = 1.0

    # Escalation features
    escalation = trace.get("escalation", {})
    features["escalation:required"] = 1.0 if escalation.get("required") else 0.0

    return features

def _extract_card_features(card: dict) -> dict:
    """Extract feature vector from Alignment Card."""
    features = {}

    # Bounded action features
    envelope = card.get("autonomy_envelope", {})
    for action in envelope.get("bounded_actions", []):
        features[f"action:{action}"] = 1.0

    # Value features
    values = card.get("values", {})
    for value in values.get("declared", []):
        features[f"value:{value}"] = 1.0

    return features

def _cosine_similarity(a: dict, b: dict) -> float:
    """Compute cosine similarity between two feature dictionaries."""
    if not a or not b:
        return 0.0

    common_keys = set(a.keys()) & set(b.keys())
    dot_product = sum(a[k] * b[k] for k in common_keys)

    mag_a = sum(v * v for v in a.values()) ** 0.5
    mag_b = sum(v * v for v in b.values()) ** 0.5

    if mag_a == 0 or mag_b == 0:
        return 0.0

    return dot_product / (mag_a * mag_b)

def _infer_drift_direction(
    streak: List[Tuple[dict, float]],
    card: dict
) -> str:
    """Infer the direction of drift from the pattern."""
    # Analysis logic to categorize drift
    # Returns: "autonomy_expansion", "value_drift", "principal_misalignment", etc.
    pass
```

---

## Appendix C: Changelog

### Version 0.1.1 (2026-02-01)

- Added behavioral similarity scoring to verification (Section 7.3, 7.4)
- Added `similarity_score` field to VerificationResult
- Added `BEHAVIORAL_SIMILARITY_THRESHOLD` constant (0.50)
- Added `low_behavioral_similarity` warning type
- Documented 60/30/10 TF-IDF feature weighting (Section 8.3)
- Updated reference implementation in Appendix B.1
- Reference to CALIBRATION.md for threshold derivation methodology

### Version 0.1.0 (2026-01-31)

- Initial draft specification
- Alignment Card schema defined
- AP-Trace format defined
- Value Coherence Handshake protocol defined
- Verification algorithm specified
- Drift detection methodology outlined

---

*Agent Alignment Protocol Specification v0.1.1*
*Authors: Vigil (protocol), Ariadne (architecture), Ember (coordination)*
*This document is released under CC BY 4.0*
