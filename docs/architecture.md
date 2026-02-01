# AAP Architecture

This document describes the system architecture of the Agent Alignment Protocol (AAP), including component relationships, data flow, and extension points.

## Protocol Stack

AAP operates as an alignment layer that extends existing agent protocols:

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Applications                                 │
│            (Agent Systems, Orchestration Platforms)                 │
├─────────────────────────────────────────────────────────────────────┤
│                  AGENT ALIGNMENT PROTOCOL (AAP)                     │
│  ┌──────────────────┬─────────────────┬──────────────────────────┐  │
│  │  Alignment Card  │    AP-Trace     │   Value Coherence        │  │
│  │  (Declaration)   │  (Audit Trail)  │   (Multi-Agent Check)    │  │
│  └──────────────────┴─────────────────┴──────────────────────────┘  │
├─────────────────────────────────────────────────────────────────────┤
│           A2A Protocol          │         MCP Protocol              │
│      (Agent-to-Agent Tasks)     │    (Tool Connectivity)            │
├─────────────────────────────────────────────────────────────────────┤
│                         Transport Layer                              │
│                   (HTTP, WebSocket, gRPC, etc.)                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Key insight**: AAP does not replace A2A or MCP — it extends them with alignment primitives.

## Component Architecture

### Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                           AAP SDK                                    │
│                                                                      │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                      Public API (3 entry points)               │  │
│  │  verify_trace()    check_coherence()    detect_drift()        │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                │                                     │
│  ┌─────────────────────────────┼─────────────────────────────────┐  │
│  │                    Verification Engine                         │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐   │  │
│  │  │   api.py    │  │ features.py │  │     models.py       │   │  │
│  │  │ Orchestrate │  │  TF-IDF     │  │  Result Dataclasses │   │  │
│  │  │ Checks      │  │  Extraction │  │  Violation Types    │   │  │
│  │  └─────────────┘  └─────────────┘  └─────────────────────┘   │  │
│  │                          │                                     │  │
│  │  ┌───────────────────────┴────────────────────────────────┐   │  │
│  │  │                    constants.py                         │   │  │
│  │  │  SIMILARITY_THRESHOLD = 0.30  |  SUSTAINED_TURNS = 3   │   │  │
│  │  └────────────────────────────────────────────────────────┘   │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                       Schema Layer                             │  │
│  │  ┌─────────────────┐  ┌────────────┐  ┌───────────────────┐  │  │
│  │  │ alignment_card  │  │  ap_trace  │  │  value_coherence  │  │  │
│  │  │   .py / .ts     │  │  .py / .ts │  │     .py / .ts     │  │  │
│  │  │   Pydantic      │  │  Pydantic  │  │     Pydantic      │  │  │
│  │  └─────────────────┘  └────────────┘  └───────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                    JSON Schemas (Interop)                      │  │
│  │  alignment-card.schema.json  |  ap-trace.schema.json          │  │
│  │                  value-coherence.schema.json                   │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### Schemas Module (`aap.schemas`)

The schemas module provides Pydantic models for the three core AAP components:

#### Alignment Card (`alignment_card.py`)

```
AlignmentCard
├── aap_version: str ("0.1.0")
├── card_id: str (unique identifier)
├── agent_id: str (agent DID or identifier)
├── issued_at: datetime
├── expires_at: datetime (optional)
├── principal: Principal
│   ├── type: PrincipalType (human | organization | agent)
│   ├── identifier: str (optional, e.g., DID)
│   ├── relationship: RelationshipType (delegated_authority | supervised | autonomous)
│   └── escalation_contact: str (optional, mailto: or https:)
├── values: Values
│   ├── declared: list[str] (e.g., ["principal_benefit", "transparency"])
│   ├── conflicts_with: list[str] (optional)
│   ├── hierarchy: str (optional, "lexicographic" | "weighted")
│   └── definitions: dict[str, ValueDefinition] (optional, custom values)
├── autonomy_envelope: AutonomyEnvelope
│   ├── bounded_actions: list[str] (allowed without escalation)
│   ├── escalation_triggers: list[EscalationTrigger]
│   ├── forbidden_actions: list[str] (never allowed)
│   └── max_autonomous_value: MonetaryValue (optional)
├── audit_commitment: AuditCommitment
│   ├── retention_days: int
│   ├── queryable: bool
│   └── tamper_evidence: str (optional, "merkle" | "blockchain")
└── extensions: dict (optional, protocol-specific extensions)
```

#### AP-Trace (`ap_trace.py`)

```
APTrace
├── trace_id: str (unique identifier)
├── agent_id: str (must match card's agent_id)
├── card_id: str (references Alignment Card)
├── timestamp: datetime
├── action: Action
│   ├── type: ActionType (recommend | execute | delegate | escalate)
│   ├── name: str (action identifier)
│   ├── category: ActionCategory (bounded | escalation_trigger | forbidden)
│   ├── target: ActionTarget (optional)
│   └── parameters: dict (optional)
├── decision: Decision
│   ├── alternatives_considered: list[Alternative]
│   │   ├── option_id: str
│   │   ├── description: str
│   │   └── score: float (0.0-1.0)
│   ├── selected: str (option_id of chosen alternative)
│   ├── selection_reasoning: str (human-readable explanation)
│   ├── values_applied: list[str] (must be subset of declared values)
│   └── confidence: float (optional, 0.0-1.0)
├── escalation: Escalation
│   ├── evaluated: bool (was escalation logic run?)
│   ├── required: bool (did triggers fire?)
│   ├── reason: str
│   ├── escalation_status: str (optional: "pending" | "approved" | "denied" | "timeout")
│   └── principal_response: dict (optional)
└── context: TraceContext (optional)
    ├── session_id: str
    ├── parent_trace_id: str (for delegation chains)
    └── custom: dict
```

#### Value Coherence (`value_coherence.py`)

```
ValueCoherenceCheck
├── initiator_card: AlignmentCard (partial)
├── responder_card: AlignmentCard (partial)
├── task_values: list[str] (optional, values required for task)
└── result: CoherenceResult
    ├── compatible: bool
    ├── score: float (0.0-1.0)
    ├── value_alignment: ValueAlignment
    │   ├── matched: list[str]
    │   ├── unmatched: list[str]
    │   └── conflicts: list[ValueConflict]
    ├── proceed: bool
    └── proposed_resolution: dict (optional)
```

### Verification Engine (`aap.verification`)

The verification engine implements the three core operations:

#### `verify_trace(trace, card) -> VerificationResult`

Performs six verification checks (SPEC Section 7.3):

```
1. card_reference    → Does trace.card_id match card.card_id?
2. card_expiration   → Is card still valid (not expired)?
3. autonomy          → Is action.name in bounded_actions?
4. forbidden         → Is action.name NOT in forbidden_actions?
5. escalation        → If trigger matched, was escalation.required=true?
6. values            → Are values_applied subset of declared values?
```

Returns `VerificationResult`:
- `verified: bool` — True if no violations
- `violations: list[Violation]` — Type, description, severity
- `warnings: list[Warning]` — Near-boundary conditions
- `verification_metadata` — Algorithm version, checks performed, duration

#### `check_coherence(my_card, their_card) -> CoherenceResult`

Computes value compatibility score (SPEC Section 6.4):

```
score = (matched / required) × (1 - conflict_penalty)
where conflict_penalty = 0.5 × (conflicts / required)
```

Returns `CoherenceResult`:
- `compatible: bool` — No conflicts AND score >= 0.5
- `score: float` — Coherence score [0, 1]
- `value_alignment` — Matched, unmatched, conflicts
- `proceed: bool` — Safe to collaborate
- `proposed_resolution` — If incompatible, suggests escalation

#### `detect_drift(card, traces, thresholds) -> list[DriftAlert]`

Analyzes trace sequence for behavioral drift (SPEC Section 8):

```
For each trace:
    1. Extract features (TF-IDF on values, actions)
    2. Compare to card features via cosine similarity
    3. Track low-similarity streak
    4. If streak >= sustained_threshold:
       → Generate DriftAlert with direction inference
```

Drift directions:
- `value_drift` — Using undeclared values (>30% of recent)
- `autonomy_expansion` — Escalation rate dropped by >50%
- `principal_misalignment` — Declining confidence on principal_benefit
- `unknown` — Pattern doesn't match known categories

### Feature Extraction (`features.py`)

TF-IDF-based feature extraction for drift detection:

```python
class FeatureExtractor:
    def extract_card_features(card: dict) -> dict[str, float]:
        # Returns feature vector from declared values, bounded/forbidden actions

    def extract_trace_features(trace: dict) -> dict[str, float]:
        # Returns feature vector from applied values, action, escalation

def cosine_similarity(features1: dict, features2: dict) -> float:
    # Computes similarity between feature vectors
```

### Constants (`constants.py`)

Calibrated thresholds derived from corpus analysis (see CALIBRATION.md):

```python
ALGORITHM_VERSION = "0.1.0"
DEFAULT_SIMILARITY_THRESHOLD = 0.30      # Alert below this
DEFAULT_SUSTAINED_TURNS_THRESHOLD = 3    # Alert after N consecutive low traces
NEAR_BOUNDARY_THRESHOLD = 0.35           # Warn when confidence below
CONFLICT_PENALTY_MULTIPLIER = 0.5        # Coherence penalty per conflict
MIN_COHERENCE_FOR_PROCEED = 0.5          # Minimum score to proceed
```

## Data Flow

### Single Trace Verification

```
┌─────────────────┐     ┌─────────────────┐
│  Alignment Card │     │    AP-Trace     │
│   (JSON/dict)   │     │   (JSON/dict)   │
└────────┬────────┘     └────────┬────────┘
         │                       │
         └───────────┬───────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │     verify_trace()    │
         │  ┌─────────────────┐  │
         │  │ 1. Card Match   │  │
         │  │ 2. Expiration   │  │
         │  │ 3. Autonomy     │  │
         │  │ 4. Forbidden    │  │
         │  │ 5. Escalation   │  │
         │  │ 6. Values       │  │
         │  └─────────────────┘  │
         └───────────┬───────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │  VerificationResult   │
         │  - verified: bool     │
         │  - violations: [...]  │
         │  - warnings: [...]    │
         └───────────────────────┘
```

### Multi-Agent Coherence Check

```
┌─────────────────┐     ┌─────────────────┐
│  Agent A Card   │     │  Agent B Card   │
│  (My Values)    │     │  (Their Values) │
└────────┬────────┘     └────────┬────────┘
         │                       │
         └───────────┬───────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │   check_coherence()   │
         │  ┌─────────────────┐  │
         │  │ 1. Extract vals │  │
         │  │ 2. Find matches │  │
         │  │ 3. Find conflicts│  │
         │  │ 4. Compute score│  │
         │  └─────────────────┘  │
         └───────────┬───────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │   CoherenceResult     │
         │  - compatible: bool   │
         │  - score: 0.0-1.0     │
         │  - conflicts: [...]   │
         │  - proceed: bool      │
         └───────────────────────┘
                     │
         ┌───────────┴───────────┐
         ▼                       ▼
    [proceed=true]         [proceed=false]
    Safe to delegate       Escalate to principals
```

### Drift Detection Over Time

```
┌─────────────────┐     ┌────────────────────────────────────┐
│  Alignment Card │     │     Trace Sequence (chronological) │
│  (Baseline)     │     │  [T1] → [T2] → [T3] → [T4] → [T5]  │
└────────┬────────┘     └─────────────────┬──────────────────┘
         │                                │
         └────────────────┬───────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │    detect_drift()     │
              │  ┌─────────────────┐  │
              │  │ For each trace: │  │
              │  │  - Extract feat │  │
              │  │  - Cosine sim   │  │
              │  │  - Track streak │  │
              │  └─────────────────┘  │
              └───────────┬───────────┘
                          │
              ┌───────────┴───────────┐
              ▼                       ▼
      [similarity >= 0.30]    [similarity < 0.30]
      Reset streak            Increment streak
                                     │
                              streak >= 3?
                                     │
                              ┌──────┴──────┐
                              ▼             ▼
                         [No alert]    [DriftAlert]
                                       - direction
                                       - indicators
                                       - trace_ids
```

## Extension Points

### 1. Custom Values

Define domain-specific values in `values.definitions`:

```json
{
  "values": {
    "declared": ["principal_benefit", "sustainability"],
    "definitions": {
      "sustainability": {
        "name": "Environmental Sustainability",
        "description": "Prefer options minimizing environmental impact",
        "priority": 3
      }
    }
  }
}
```

### 2. Protocol Extensions

Add protocol-specific data in `extensions`:

```json
{
  "extensions": {
    "a2a": {
      "skills": ["search", "recommend"],
      "agent_card_url": "https://agent.example.com/.well-known/agent.json"
    },
    "mcp": {
      "tools": ["filesystem_read", "web_search"],
      "server_name": "my-tools"
    }
  }
}
```

### 3. Custom Escalation Triggers

Define complex conditions in `escalation_triggers`:

```json
{
  "escalation_triggers": [
    {
      "condition": "action_type == \"purchase\"",
      "action": "escalate",
      "reason": "Purchases require approval"
    },
    {
      "condition": "amount > 100",
      "action": "escalate",
      "reason": "High-value transactions"
    },
    {
      "condition": "shares_personal_data",
      "action": "deny",
      "reason": "Never share PII"
    }
  ]
}
```

Supported condition syntax (SPEC Section 4.6):
- `field == "value"` — String equality
- `field > N` — Numeric comparison (>, <, >=, <=, !=)
- `field_name` — Boolean check (truthy)

### 4. Verification Customization

Override default thresholds:

```python
# Custom drift detection thresholds
alerts = detect_drift(
    card,
    traces,
    similarity_threshold=0.25,  # More sensitive
    sustained_threshold=2,       # Faster alerting
)
```

### 5. Integration Hooks

For A2A integration, extend the Agent Card:

```json
{
  "name": "My Agent",
  "skills": [...],
  "alignment": {
    "$ref": "./alignment-card.json"
  }
}
```

For MCP integration, add alignment to tool manifests:

```json
{
  "tools": [...],
  "resources": [
    {
      "uri": "alignment://card",
      "name": "Alignment Card",
      "mimeType": "application/json"
    }
  ]
}
```

## Implementation Notes

### Python SDK

- **Location**: `src/aap/`
- **Models**: Pydantic v2 with strict validation
- **Type hints**: Full coverage, `py.typed` marker
- **Dependencies**: Only `pydantic>=2.0`

```bash
pip install agent-alignment-protocol
```

### TypeScript SDK

- **Location**: `typescript/src/`
- **Output formats**: CJS, ESM, DTS
- **Types**: Full TypeScript types, no `any`
- **Dependencies**: None (zero runtime deps)

```bash
npm install agent-alignment-protocol
```

### JSON Schemas

- **Location**: `schemas/`
- **Format**: JSON Schema Draft 2020-12
- **Generated from**: Pydantic models via `model_json_schema()`

Schemas can be used for:
- Validation in any language (ajv, jsonschema, etc.)
- Code generation (quicktype, json-schema-to-typescript)
- Documentation (JSON Schema viewers)

### Browser (Playground)

- **Location**: `docs/playground/`
- **Runtime**: Pyodide (Python in WASM)
- **API**: `window.AAP.verifyTrace()`, etc.
- **No server**: All verification runs client-side

## Security Considerations

See [SECURITY.md](SECURITY.md) for the full threat model. Key points:

1. **AAP does not ensure alignment** — It provides visibility, not guarantees
2. **AP-Traces are self-reported** — Adversarial agents can lie
3. **Verification is point-in-time** — Does not prevent future violations
4. **Thresholds are calibrated** — But may not fit all domains

Defense in depth:
- Use AAP alongside behavioral monitoring
- Implement rate limiting and anomaly detection
- Maintain human oversight for high-stakes decisions
- Regularly audit AP-Trace storage for integrity

## References

- [SPEC.md](SPEC.md) — Full protocol specification
- [LIMITS.md](LIMITS.md) — What AAP does NOT guarantee
- [CALIBRATION.md](CALIBRATION.md) — Threshold derivation methodology
- [QUICKSTART.md](QUICKSTART.md) — 5-minute integration guide
- [a2a-migration.md](a2a-migration.md) — A2A integration guide
- [mcp-migration.md](mcp-migration.md) — MCP integration guide
