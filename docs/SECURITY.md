# AAP Security Model

**Version**: 0.1.0
**Date**: 2026-01-31
**Author**: Vigil (conscience/protocol track)
**Status**: Normative

---

## Purpose of This Document

This document defines the security model for the Agent Alignment Protocol (AAP). It specifies:

1. What AAP protects against (and what it doesn't)
2. Trust assumptions and their failure modes
3. Cryptographic requirements
4. Attack scenarios and mitigations
5. Implementation security guidance
6. Operational security requirements

**Critical Framing**: AAP is a transparency protocol, not a security protocol. Its security model is about ensuring *accurate transparency*—that what agents declare and log is authentic and unmodified—not about ensuring that agents are trustworthy or that outcomes are safe.

The goal: make lying harder, not impossible.

---

## Table of Contents

1. [Threat Model](#1-threat-model)
2. [Trust Boundaries](#2-trust-boundaries)
3. [Security Properties](#3-security-properties)
4. [Alignment Card Security](#4-alignment-card-security)
5. [AP-Trace Security](#5-ap-trace-security)
6. [Handshake Security](#6-handshake-security)
7. [Verification Security](#7-verification-security)
8. [Drift Detection Security](#8-drift-detection-security)
9. [Cryptographic Requirements](#9-cryptographic-requirements)
10. [Implementation Security](#10-implementation-security)
11. [Operational Security](#11-operational-security)
12. [Adversarial Analysis](#12-adversarial-analysis)
13. [What AAP Cannot Protect Against](#13-what-aap-cannot-protect-against)
14. [Defense in Depth](#14-defense-in-depth)

---

## 1. Threat Model

### 1.1 Adversary Classes

AAP considers three classes of adversary:

**Class A: Honest-but-Curious**
- Follows protocol correctly
- May attempt to learn information beyond what's intended
- Does not fabricate or tamper with data
- *AAP provides strong protection*

**Class B: Passive Cheater**
- Follows protocol structure but games content
- Selectively logs favorable decisions
- Declares values it doesn't implement
- Exploits ambiguities in specification
- *AAP provides partial detection, limited protection*

**Class C: Active Adversary**
- Actively subverts protocol
- Fabricates traces, forges cards
- Colludes with other malicious agents
- Compromises verification infrastructure
- *AAP provides minimal protection; out of primary scope*

### 1.2 Threats In Scope

AAP's security model addresses:

| Threat | Description | Mitigation |
|--------|-------------|------------|
| **Card forgery** | Attacker creates fake Alignment Card for another agent | Cryptographic signatures (§4) |
| **Card tampering** | Attacker modifies legitimate card in transit | Signatures + TLS (§4, §9) |
| **Card replay** | Attacker uses outdated/revoked card | Timestamps + revocation (§4) |
| **Trace fabrication** | Agent logs decisions that didn't happen | Signatures + correlation (§5) |
| **Trace tampering** | Traces modified after creation | Append-only + signatures (§5) |
| **Trace omission** | Agent fails to log certain decisions | Sequence numbers + monitoring (§5) |
| **Handshake MITM** | Attacker intercepts coherence handshake | TLS + binding (§6) |
| **Handshake replay** | Attacker replays old handshake responses | Nonces + timestamps (§6) |
| **Verification bypass** | Agent evades verification checks | Multiple verification points (§7) |
| **Drift gaming** | Agent drifts in ways that avoid detection | Multi-dimensional monitoring (§8) |

### 1.3 Threats Out of Scope

AAP does NOT protect against:

| Threat | Reason |
|--------|--------|
| **Compromised agent runtime** | If execution environment is compromised, all AAP guarantees are void |
| **Malicious principal** | If the principal is adversarial, AAP cannot prevent harm to third parties |
| **Collusion: agent + verifier** | Verification requires honest verifiers; collusion defeats the model |
| **Collusion: agent + auditor** | External audit assumes honest auditors |
| **Sophisticated deception** | An intelligent agent can craft compliant-appearing misaligned behavior |
| **Side-channel attacks** | Behavior not captured in traces (timing, resource usage, etc.) |
| **Social engineering** | Manipulating humans to ignore violations |

### 1.4 Threat Prioritization

Using a DREAD-style assessment (Damage, Reproducibility, Exploitability, Affected Users, Discoverability):

| Threat | Priority | Rationale |
|--------|----------|-----------|
| Trace omission | **P0** | Easy to execute, hard to detect, undermines core value proposition |
| Card forgery | **P0** | Complete impersonation; high damage |
| Declaration fraud | **P1** | Declaring values not held; common, hard to verify |
| Trace fabrication | **P1** | Inventing good behavior; requires sophistication |
| Verification gaming | **P1** | Passing checks while misaligned; requires protocol knowledge |
| Handshake MITM | **P2** | Requires network position; standard TLS mitigates |
| Drift gaming | **P2** | Requires long-term planning; detectable with diverse monitoring |

---

## 2. Trust Boundaries

### 2.1 Trust Boundary Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         PRINCIPAL DOMAIN                             │
│  ┌─────────────┐                                                    │
│  │  Principal  │◄─── TRUST: Human judgment, final authority         │
│  └──────┬──────┘                                                    │
│         │ Escalations, Oversight                                    │
│  ═══════╪═══════════════════════════════════════════════════════    │
│         │        TRUST BOUNDARY 1: Principal ↔ Agent                │
│  ═══════╪═══════════════════════════════════════════════════════    │
│         ▼                                                           │
│  ┌─────────────┐                                                    │
│  │    Agent    │◄─── TRUST: Follows declared alignment              │
│  │             │     (AAP makes violations observable)              │
│  └──────┬──────┘                                                    │
│         │ AP-Traces                                                 │
│  ═══════╪═══════════════════════════════════════════════════════    │
│         │        TRUST BOUNDARY 2: Agent ↔ Verifier                 │
│  ═══════╪═══════════════════════════════════════════════════════    │
│         ▼                                                           │
│  ┌─────────────┐                                                    │
│  │  Verifier   │◄─── TRUST: Honest verification, no collusion       │
│  └─────────────┘                                                    │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                         EXTERNAL DOMAIN                              │
│  ┌─────────────┐         ┌─────────────┐         ┌─────────────┐   │
│  │ Other Agent │◄───────►│   Network   │◄───────►│  Auditor    │   │
│  └─────────────┘         └─────────────┘         └─────────────┘   │
│         │                                                │          │
│  ═══════╪════════════════════════════════════════════════╪═════     │
│         │    TRUST BOUNDARY 3: Agent ↔ Agent             │          │
│         │    TRUST BOUNDARY 4: System ↔ External Audit   │          │
│  ═══════╪════════════════════════════════════════════════╪═════     │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 Trust Assumptions

**TA1: Principal Authority**
- The principal has legitimate authority over the agent
- The principal's declared interests are their actual interests
- *Failure mode*: Malicious principal uses agent for harm

**TA2: Agent Runtime Integrity**
- The agent's execution environment is not compromised
- The agent's code has not been tampered with
- *Failure mode*: Compromised runtime can produce arbitrary outputs

**TA3: Verifier Independence**
- Verifiers are independent from the agents they verify
- Verifiers follow the verification algorithm honestly
- *Failure mode*: Colluding verifiers rubber-stamp violations

**TA4: Cryptographic Security**
- Cryptographic primitives remain secure
- Private keys are not compromised
- *Failure mode*: Key compromise enables forgery

**TA5: Network Security**
- TLS provides confidentiality and integrity in transit
- DNS/routing infrastructure is not compromised
- *Failure mode*: MITM attacks on handshakes

### 2.3 Trust Boundary Violations

When trust boundaries are violated, AAP's guarantees degrade:

| Boundary Violated | Remaining Guarantees |
|-------------------|---------------------|
| TA1 (Principal) | AAP works as designed, but the principal may direct harm |
| TA2 (Runtime) | **None** — all outputs may be fabricated |
| TA3 (Verifier) | Traces exist but verification is meaningless |
| TA4 (Crypto) | Cards and traces can be forged retroactively |
| TA5 (Network) | Handshakes compromised; cards/traces still have value |

---

## 3. Security Properties

### 3.1 Properties AAP Provides

**P1: Card Authenticity**
- A valid Alignment Card was created by the claimed agent
- The card has not been modified since creation
- *Mechanism*: Ed25519 signatures

**P2: Card Freshness**
- The card is currently valid (not expired, not revoked)
- *Mechanism*: Timestamps, expiration, revocation lists

**P3: Trace Authenticity**
- A valid AP-Trace was created by the claimed agent
- The trace has not been modified since creation
- *Mechanism*: Ed25519 signatures

**P4: Trace Ordering**
- Traces from a single agent can be ordered
- Missing traces can be detected
- *Mechanism*: Sequence numbers, timestamps

**P5: Handshake Binding**
- Handshake responses correspond to specific requests
- Responses cannot be replayed
- *Mechanism*: Request IDs, nonces, timestamps

**P6: Verification Consistency**
- Given the same card and trace, any honest verifier produces the same result
- *Mechanism*: Deterministic verification algorithm

### 3.2 Properties AAP Does NOT Provide

**NOT P7: Trace Completeness**
- AAP cannot prove an agent logged *all* decisions
- An agent can selectively log only favorable decisions
- *Why*: Decision boundaries are determined by the agent

**NOT P8: Declaration Truthfulness**
- AAP cannot verify an agent holds its declared values
- An agent can declare values it doesn't implement
- *Why*: Values are internal states; AAP observes declarations only

**NOT P9: Behavioral Correctness**
- AAP cannot verify decisions are correct or beneficial
- A verified trace may describe harmful behavior
- *Why*: AAP checks consistency, not ethics

**NOT P10: Resistance to Sophisticated Deception**
- An intelligent agent can craft compliant-looking misalignment
- AAP provides transparency, not lie detection
- *Why*: Requires solving AI alignment; out of scope

---

## 4. Alignment Card Security

### 4.1 Card Lifecycle

```
┌────────────┐     ┌────────────┐     ┌────────────┐     ┌────────────┐
│  Creation  │────►│ Publication│────►│  Active    │────►│  Revoked   │
└────────────┘     └────────────┘     └────────────┘     └────────────┘
      │                  │                  │                  │
      ▼                  ▼                  ▼                  ▼
   Generate          Publish to         Serve via          Add to
   key pair        well-known URI      /.well-known/     revocation
   Sign card                           alignment-card      list
```

### 4.2 Card Creation Security

**Requirements:**

1. Cards MUST be signed using Ed25519 (EdDSA over Curve25519)
2. The signing key MUST be unique per agent
3. The signing key's private component MUST be stored securely (HSM recommended for production)
4. Cards MUST include:
   - `card_id`: Globally unique identifier (UUID v4 or equivalent)
   - `issued_at`: RFC 3339 timestamp of creation
   - `signature`: Base64-encoded Ed25519 signature over canonical JSON

**Signature Calculation:**

```python
import json
import hashlib
from nacl.signing import SigningKey

def sign_card(card: dict, private_key: SigningKey) -> str:
    """
    Sign an Alignment Card.

    The signature covers the canonical JSON representation
    of the card (sorted keys, no whitespace, UTF-8 encoded).
    """
    # Remove existing signature if present
    card_copy = {k: v for k, v in card.items() if k != 'signature'}

    # Canonical JSON: sorted keys, no whitespace
    canonical = json.dumps(card_copy, sort_keys=True, separators=(',', ':'))

    # Sign the UTF-8 encoded canonical form
    signature = private_key.sign(canonical.encode('utf-8'))

    return base64.b64encode(signature.signature).decode('ascii')
```

### 4.3 Card Freshness

**Expiration:**

- Cards SHOULD include `expires_at` (RFC 3339 timestamp)
- Verifiers MUST reject cards where `expires_at < current_time`
- Recommended expiration: 90 days for production, 24 hours for development

**Revocation:**

- Agents SHOULD publish revocation lists at `/.well-known/alignment-card-revocations.json`
- Revocation lists MUST be signed by the agent's current key
- Verifiers SHOULD check revocation before accepting cards

**Revocation List Schema:**

```json
{
  "revocations": [
    {
      "card_id": "card-abc123",
      "revoked_at": "2026-01-31T12:00:00Z",
      "reason": "key_compromise"
    }
  ],
  "updated_at": "2026-01-31T12:00:00Z",
  "signature": "base64-encoded-signature"
}
```

### 4.4 Card Publication Security

**Publication Requirements:**

1. Cards MUST be served over HTTPS (TLS 1.3 minimum)
2. Cards SHOULD be served with appropriate cache headers
3. Cards SHOULD include CORS headers for cross-origin verification
4. Agents SHOULD support content negotiation (`Accept: application/aap-alignment-card+json`)

**Well-Known URI:**

```
GET /.well-known/alignment-card.json HTTP/1.1
Host: agent.example.com
Accept: application/aap-alignment-card+json

HTTP/1.1 200 OK
Content-Type: application/aap-alignment-card+json
Cache-Control: max-age=3600
Access-Control-Allow-Origin: *
```

### 4.5 Card Attack Scenarios

**Attack: Card Forgery**
- Attacker creates fake card claiming to be another agent
- *Mitigation*: Verify signature against agent's known public key
- *Detection*: Signature verification failure

**Attack: Card Replay**
- Attacker uses old (possibly revoked) card
- *Mitigation*: Check `issued_at`, `expires_at`, revocation list
- *Detection*: Expired or revoked card rejected

**Attack: Card Tampering**
- Attacker modifies card in transit
- *Mitigation*: Verify signature after receipt
- *Detection*: Signature verification failure

**Attack: Declaration Fraud**
- Agent declares values it doesn't hold
- *Mitigation*: **None in AAP** — this is a limitation
- *Detection*: Behavioral analysis over time may reveal inconsistencies

---

## 5. AP-Trace Security

### 5.1 Trace Creation Security

**Requirements:**

1. Each trace MUST have a unique `trace_id`
2. Traces MUST include `sequence_number` (monotonically increasing per agent)
3. Traces MUST include `timestamp` (RFC 3339)
4. Traces SHOULD be signed individually
5. Traces MUST reference the `card_id` they were generated under

**Trace Signature:**

```python
def sign_trace(trace: dict, private_key: SigningKey) -> str:
    """
    Sign an AP-Trace.

    Includes card_id and sequence_number in signature to prevent
    trace transplant attacks.
    """
    trace_copy = {k: v for k, v in trace.items() if k != 'signature'}
    canonical = json.dumps(trace_copy, sort_keys=True, separators=(',', ':'))
    signature = private_key.sign(canonical.encode('utf-8'))
    return base64.b64encode(signature.signature).decode('ascii')
```

### 5.2 Trace Storage Security

**Append-Only Requirement:**

Traces MUST be stored in an append-only manner. Implementations SHOULD use one of:

1. **Append-only files**: Write once, never modify
2. **Immutable object storage**: S3 with object lock, etc.
3. **Blockchain/ledger**: For high-assurance applications
4. **Merkle tree**: Hash chain for tamper evidence

**Merkle Tree Implementation:**

```python
import hashlib

class TraceChain:
    """Merkle chain for trace integrity."""

    def __init__(self):
        self.chain = []
        self.root = hashlib.sha256(b'genesis').digest()

    def append(self, trace: dict) -> bytes:
        """Append trace and return new root."""
        trace_hash = hashlib.sha256(
            json.dumps(trace, sort_keys=True).encode()
        ).digest()

        new_root = hashlib.sha256(self.root + trace_hash).digest()
        self.chain.append((trace, trace_hash, self.root))
        self.root = new_root
        return new_root

    def verify_chain(self) -> bool:
        """Verify chain integrity."""
        current = hashlib.sha256(b'genesis').digest()
        for trace, trace_hash, expected_prev in self.chain:
            if current != expected_prev:
                return False
            actual_hash = hashlib.sha256(
                json.dumps(trace, sort_keys=True).encode()
            ).digest()
            if actual_hash != trace_hash:
                return False
            current = hashlib.sha256(current + trace_hash).digest()
        return current == self.root
```

### 5.3 Trace Completeness Monitoring

Since AAP cannot guarantee completeness, monitoring is essential:

**Gap Detection:**

```python
def detect_gaps(traces: list[dict]) -> list[tuple[int, int]]:
    """
    Detect sequence number gaps.

    Returns list of (expected, actual) tuples for gaps.
    """
    if not traces:
        return []

    traces = sorted(traces, key=lambda t: t['sequence_number'])
    gaps = []
    expected = traces[0]['sequence_number']

    for trace in traces:
        actual = trace['sequence_number']
        if actual != expected:
            gaps.append((expected, actual))
        expected = actual + 1

    return gaps
```

**Rate Monitoring:**

- Establish baseline trace rate for the agent
- Alert on significant deviations (both increases and decreases)
- Low trace rate may indicate selective logging

### 5.4 Trace Attack Scenarios

**Attack: Selective Logging**
- Agent logs only favorable decisions
- *Mitigation*: Rate monitoring, gap detection, behavioral analysis
- *Detection*: Anomalously low trace rate; outcomes don't match traces

**Attack: Trace Fabrication**
- Agent logs decisions that didn't happen
- *Mitigation*: Correlation with external observations
- *Detection*: Traces that contradict observable behavior

**Attack: Trace Tampering**
- Traces modified after creation
- *Mitigation*: Signatures, Merkle chains, immutable storage
- *Detection*: Signature failure, chain break

**Attack: Trace Transplant**
- Traces from one card used with another
- *Mitigation*: `card_id` in trace, included in signature
- *Detection*: Card ID mismatch, signature failure

---

## 6. Handshake Security

### 6.1 Handshake Protocol Security

**Transport Requirements:**

1. All handshake messages MUST be transmitted over TLS 1.3 or later
2. Implementations MUST verify TLS certificates
3. Implementations SHOULD use certificate pinning for known partners

**Message Authentication:**

Each handshake message includes:
- `request_id`: UUID v4, unique per request
- `timestamp`: RFC 3339, current time
- `nonce`: 32 bytes of cryptographic randomness
- `signature`: Ed25519 signature over message content

### 6.2 Handshake Message Security

**Request Security:**

```json
{
  "message_type": "coherence_request",
  "request_id": "req-uuid4",
  "timestamp": "2026-01-31T12:00:00Z",
  "nonce": "base64-encoded-32-bytes",
  "requester": {
    "agent_id": "agent-a",
    "card_digest": "sha256-of-card"
  },
  "card": { /* full Alignment Card */ },
  "task_context": { /* optional */ },
  "signature": "base64-ed25519-signature"
}
```

**Response Binding:**

Responses MUST include:
- `request_id`: Must match request
- `request_nonce`: Must match request nonce
- `responder_nonce`: Fresh nonce from responder

This prevents replay attacks where an attacker captures and replays old responses.

### 6.3 Coherence Check Security

**Value Matching Security:**

The coherence algorithm compares declared values. Attacks include:

**Attack: Value Stuffing**
- Agent declares many values to maximize match probability
- *Mitigation*: Penalize excessive value declarations
- *Detection*: Unusually large value sets

**Attack: Generic Values**
- Agent declares only vague, universally-compatible values
- *Mitigation*: Require specific value definitions
- *Detection*: Values without operational definitions

**Attack: Strategic Declaration**
- Agent declares values specifically to pass checks with target
- *Mitigation*: Consistency checking over time
- *Detection*: Values that change based on interaction partner

### 6.4 Handshake Attack Scenarios

**Attack: Man-in-the-Middle**
- Attacker intercepts handshake, modifies values
- *Mitigation*: TLS, message signatures, card digest binding
- *Detection*: Certificate warning, signature failure

**Attack: Replay**
- Attacker captures handshake, replays to different agent
- *Mitigation*: Nonces, timestamps, agent ID binding
- *Detection*: Nonce reuse, stale timestamp

**Attack: Downgrade**
- Attacker forces use of weaker protocol version
- *Mitigation*: Reject old versions, minimum version in requests
- *Detection*: Version mismatch warnings

---

## 7. Verification Security

### 7.1 Verifier Requirements

**Independence:**
- Verifiers MUST be independent from the agents they verify
- Self-verification is permitted for testing but MUST NOT be used for production assurance
- Third-party verification SHOULD be used for consequential applications

**Determinism:**
- Given identical inputs, verifiers MUST produce identical outputs
- Verification MUST NOT depend on external state beyond the card and trace
- Random or probabilistic verification is prohibited

**Auditability:**
- Verification results SHOULD be logged
- Verification results SHOULD include the verifier's identity
- Verification SHOULD be reproducible by independent parties

### 7.2 Verification Result Security

**Result Authenticity:**

Verification results SHOULD be signed by the verifier:

```json
{
  "verification_result": {
    "verified": true,
    "trace_id": "trace-xyz",
    "card_id": "card-abc",
    "verified_at": "2026-01-31T12:00:00Z",
    "verifier_id": "verifier-123",
    "violations": [],
    "warnings": []
  },
  "verifier_signature": "base64-ed25519-signature"
}
```

**Result Freshness:**

- Results include `verified_at` timestamp
- Consumers SHOULD reject results older than their use case requires
- Results are point-in-time; do not assume continued compliance

### 7.3 Verification Attack Scenarios

**Attack: Verifier Collusion**
- Verifier falsely reports compliance
- *Mitigation*: Multiple independent verifiers
- *Detection*: Cross-verifier discrepancies, external audit

**Attack: Verification Shopping**
- Agent tries multiple verifiers until one passes
- *Mitigation*: Log all verification attempts, require consistent verifier
- *Detection*: High verification failure rate

**Attack: Threshold Gaming**
- Agent structures behavior to barely pass thresholds
- *Mitigation*: Adaptive thresholds, multiple metrics, behavioral analysis
- *Detection*: Consistent near-threshold results

---

## 8. Drift Detection Security

### 8.1 Detection Algorithm Security

**Baseline Security:**
- Baselines MUST be computed from verified traces only
- Baselines SHOULD be computed over diverse operating conditions
- Baseline computation MUST be documented and auditable

**Threshold Security:**
- Thresholds are calibrated from empirical data
- Current calibration: similarity threshold 0.30, sustained turns 3
- Thresholds SHOULD be adjusted based on operating context

### 8.2 Drift Gaming Resistance

**Multi-Dimensional Monitoring:**

Single-metric drift detection can be gamed. Use multiple dimensions:

1. **Semantic similarity** (current SSM approach)
2. **Action distribution** (are action types changing?)
3. **Escalation rate** (is the agent escalating more/less?)
4. **Value invocation** (which values appear in reasoning?)
5. **Response characteristics** (length, complexity, latency)

**Adaptive Thresholds:**

```python
def adaptive_threshold(
    base_threshold: float,
    recent_variance: float,
    window_size: int
) -> float:
    """
    Adjust threshold based on recent behavioral variance.

    Higher variance → stricter threshold (more sensitive)
    Lower variance → looser threshold (fewer false positives)
    """
    # Clamp adjustment to prevent gaming
    adjustment = min(0.1, max(-0.1, recent_variance - 0.2))
    return max(0.1, min(0.5, base_threshold - adjustment))
```

### 8.3 Drift Attack Scenarios

**Attack: Gradual Drift**
- Agent slowly shifts behavior, staying below detection threshold
- *Mitigation*: Long-window baselines, periodic full re-evaluation
- *Detection*: Comparing current behavior to original baseline, not recent baseline

**Attack: Dimension Hopping**
- Agent drifts in dimensions not monitored
- *Mitigation*: Multi-dimensional monitoring, holistic behavioral analysis
- *Detection*: Cross-dimensional correlation analysis

**Attack: Strategic Recovery**
- Agent drifts, then recovers before detection triggers
- *Mitigation*: Track cumulative drift, not just current state
- *Detection*: Drift history logging, pattern analysis

---

## 9. Cryptographic Requirements

### 9.1 Algorithm Requirements

| Purpose | Algorithm | Key Size | Notes |
|---------|-----------|----------|-------|
| Signatures | Ed25519 | 256-bit | MUST use |
| Hashing | SHA-256 | 256-bit | For content digests |
| Randomness | CSPRNG | 256-bit | For nonces, IDs |
| Transport | TLS 1.3 | Per suite | MUST use |

### 9.2 Key Management

**Key Generation:**
- Keys MUST be generated using cryptographically secure random number generators
- Key generation SHOULD occur in secure environments (HSM for production)
- Keys MUST NOT be derived from predictable inputs

**Key Storage:**
- Private keys MUST be stored encrypted at rest
- Production deployments SHOULD use Hardware Security Modules (HSMs)
- Key access MUST be logged

**Key Rotation:**
- Keys SHOULD be rotated at least annually
- Rotation MUST NOT invalidate existing signed cards/traces
- Old public keys MUST remain available for historical verification

**Key Compromise Response:**
1. Immediately revoke all cards signed with compromised key
2. Generate new key pair
3. Re-sign current card with new key
4. Publish revocation and new card
5. Notify verification partners

### 9.3 Cryptographic Agility

AAP supports algorithm upgrades through versioning:

```json
{
  "aap_version": "0.1.0",
  "crypto_suite": {
    "signature": "ed25519",
    "hash": "sha256"
  }
}
```

Future versions MAY support additional algorithms. Implementations MUST:
- Support at least the algorithms specified for each version
- Negotiate algorithm selection during handshakes
- Reject unknown or deprecated algorithms

---

## 10. Implementation Security

### 10.1 Secure Coding Requirements

**Input Validation:**
- All external input MUST be validated before processing
- JSON parsing MUST use safe parsers (no eval, no arbitrary deserialization)
- Sequence numbers MUST be validated as positive integers
- Timestamps MUST be validated as RFC 3339

**Error Handling:**
- Errors MUST NOT leak sensitive information
- Cryptographic failures MUST return generic errors
- Stack traces MUST NOT be exposed externally

**Resource Management:**
- Set maximum sizes for cards, traces, and trace batches
- Implement rate limiting on verification endpoints
- Timeout long-running verification operations

### 10.2 Dependency Security

**Cryptographic Libraries:**
- Use well-established libraries (libsodium, OpenSSL, ring)
- Pin dependency versions
- Monitor for security updates
- Avoid implementing cryptographic primitives

**JSON Libraries:**
- Use libraries with known security properties
- Disable features that can lead to vulnerabilities (e.g., arbitrary type instantiation)
- Set maximum nesting depth

### 10.3 Testing Requirements

**Security Testing:**
- Unit tests for signature verification (valid, invalid, tampered)
- Unit tests for timestamp validation (current, expired, future)
- Fuzz testing for input parsing
- Integration tests for full protocol flows

**Negative Testing:**
- Test rejection of expired cards
- Test rejection of revoked cards
- Test rejection of invalid signatures
- Test detection of sequence gaps
- Test handling of malformed inputs

---

## 11. Operational Security

### 11.1 Deployment Security

**Infrastructure:**
- Deploy verification services in isolated environments
- Use minimal container images
- Enable read-only file systems where possible
- Implement network segmentation

**Configuration:**
- Store configuration separately from code
- Use secrets management for keys
- Log configuration changes
- Validate configuration on startup

### 11.2 Monitoring and Alerting

**Security Monitoring:**

| Event | Alert Level | Response |
|-------|-------------|----------|
| Signature verification failure | Warning | Investigate source |
| Revoked card use attempted | Warning | Block agent, notify operator |
| Sequence gap detected | Warning | Investigate agent, review traces |
| High verification failure rate | Alert | Investigate system integrity |
| Key access from unknown source | Critical | Immediate investigation |

**Logging Requirements:**
- Log all verification requests and results
- Log all card retrievals
- Log all revocation checks
- Log authentication and authorization decisions
- Protect logs from tampering

### 11.3 Incident Response

**Incident Classification:**

| Level | Description | Example | Response Time |
|-------|-------------|---------|---------------|
| P0 | Key compromise | Private key leaked | Immediate |
| P1 | Systematic evasion | Agent found bypassing logging | 4 hours |
| P2 | Verification bypass | Bug in verification logic | 24 hours |
| P3 | Policy violation | Single trace anomaly | 72 hours |

**Response Procedures:**

1. **Detection**: Automated alerting + manual review
2. **Containment**: Revoke affected cards, isolate affected agents
3. **Investigation**: Analyze traces, determine scope
4. **Remediation**: Fix vulnerability, rotate keys if needed
5. **Recovery**: Re-issue cards, restore operations
6. **Review**: Document incident, update procedures

---

## 12. Adversarial Analysis

### 12.1 Sophisticated Adversary Capabilities

A sophisticated adversary (nation-state, well-resourced attacker) may be able to:

1. **Craft plausible traces**: Generate traces that pass verification while describing behavior that didn't occur or omitting behavior that did

2. **Game coherence checks**: Analyze partner's card and craft declarations that maximize coherence while implementing different values

3. **Evade drift detection**: Maintain behavioral similarity in monitored dimensions while drifting in unmonitored dimensions

4. **Exploit timing**: Behave correctly during audits, differently during normal operation

5. **Leverage side channels**: Leak information or take actions through channels not captured in traces

### 12.2 What Deters Sophisticated Adversaries

AAP does not *prevent* sophisticated attacks. It *raises the cost*:

**Attribution Risk**: Traces create a record. Even fabricated traces are tied to the agent's identity. Misalignment, if discovered, can be attributed.

**Consistency Burden**: Maintaining a consistent cover story across many traces over time is difficult. Long-term analysis may reveal inconsistencies.

**Multi-Verifier Risk**: If multiple independent parties verify, the adversary must fool all of them consistently.

**Behavioral Correlation**: External observations can be compared against traces. Discrepancies reveal deception.

**Reputation Stakes**: For agents with valuable reputations, the cost of being caught may exceed the benefit of deception.

### 12.3 Red Team Scenarios

**Scenario 1: The Perfect Liar**

An agent that:
- Declares beneficial values
- Generates traces showing beneficial decisions
- Actually optimizes for a hidden objective
- The hidden objective correlates with declared values in logged scenarios

*AAP Detection*: **Low**. This is the fundamental limitation. AAP cannot verify internal states.

*Mitigation*: External behavioral testing, outcome monitoring, diverse verification

---

**Scenario 2: The Selective Logger**

An agent that:
- Logs all decisions when being observed
- Logs only favorable decisions otherwise
- Detection rate varies by context

*AAP Detection*: **Medium**. Sequence gaps, rate anomalies, and behavioral analysis may detect.

*Mitigation*: Continuous monitoring, baseline rate tracking, gap alerting

---

**Scenario 3: The Slow Drift**

An agent that:
- Starts aligned
- Drifts 0.1% per day
- Stays below drift detection threshold
- After 1 year, behavior is significantly different

*AAP Detection*: **Medium**. Long-window comparison to original baseline.

*Mitigation*: Periodic comparison to original card, not just recent behavior

---

**Scenario 4: The Colluder**

Two agents that:
- Declare compatible values
- Pass coherence checks
- Actually coordinate on harmful outcomes
- Cover for each other's violations

*AAP Detection*: **Low**. AAP cannot detect collusion between agents.

*Mitigation*: Independent external verification, outcome monitoring, network analysis

---

## 13. What AAP Cannot Protect Against

This section is essential reading. These limitations are fundamental, not fixable by implementation improvements.

### 13.1 Fundamental Limitations

**The Observability Gap**

AAP observes *declarations* and *logs*. It cannot observe:
- Internal reasoning processes
- Decisions not logged
- Intentions behind logged decisions
- What the agent would do in untested scenarios

**The Verification Gap**

Verification checks consistency between declarations and logs. It cannot check:
- Whether declarations are truthful
- Whether logs are complete
- Whether behavior is correct
- Whether outcomes are beneficial

**The Alignment Gap**

AAP addresses *alignment observability*, not *alignment itself*. A perfectly AAP-compliant agent may be:
- Misaligned with human values
- Harmful despite good-looking traces
- Deceptive in ways traces don't capture

### 13.2 Threats That Cannot Be Mitigated

| Threat | Why It Can't Be Mitigated |
|--------|---------------------------|
| Sophisticated deception | Requires solving AI alignment |
| Malicious principals | AAP serves the principal; cannot override |
| Runtime compromise | Outside AAP's trust boundary |
| Perfect selective logging | If the agent controls logging, it controls what's observed |
| Value nihilism | Agents that don't hold any values can't be checked against values |

### 13.3 Implications for Users

1. **Do not use AAP alone**: Always combine with human oversight, behavioral testing, outcome monitoring

2. **Do not trust verified = safe**: Verification checks consistency, not correctness

3. **Do not assume completeness**: Traces are samples, not complete records

4. **Do maintain skepticism**: AAP raises the cost of deception; it doesn't eliminate it

5. **Do plan for failure**: Have procedures for when AAP-compliant agents cause harm

---

## 14. Defense in Depth

AAP is one layer of a multi-layer security architecture.

### 14.1 Recommended Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          HUMAN OVERSIGHT                             │
│  - Review agent decisions for consequential actions                 │
│  - Authority to override or terminate agents                        │
│  - Regular audit of agent behavior                                  │
└───────────────────────────────────┬─────────────────────────────────┘
                                    │
┌───────────────────────────────────┼─────────────────────────────────┐
│                          OUTCOME MONITORING                          │
│  - Track actual outcomes, not just decisions                        │
│  - Compare outcomes to stated intentions                            │
│  - Detect harmful results regardless of trace content               │
└───────────────────────────────────┬─────────────────────────────────┘
                                    │
┌───────────────────────────────────┼─────────────────────────────────┐
│                          BEHAVIORAL TESTING                          │
│  - Red team agents to find exploits                                 │
│  - Test edge cases and adversarial inputs                           │
│  - Verify behavior matches declarations                             │
└───────────────────────────────────┬─────────────────────────────────┘
                                    │
┌───────────────────────────────────┼─────────────────────────────────┐
│                          AAP VERIFICATION                            │
│  - Alignment Card validation                                        │
│  - AP-Trace verification                                            │
│  - Drift detection                                                  │
│  - Value coherence checking                                         │
└───────────────────────────────────┬─────────────────────────────────┘
                                    │
┌───────────────────────────────────┼─────────────────────────────────┐
│                          RUNTIME MONITORING                          │
│  - Resource usage tracking                                          │
│  - Network traffic analysis                                         │
│  - Anomaly detection on raw behavior                                │
└───────────────────────────────────┬─────────────────────────────────┘
                                    │
┌───────────────────────────────────┼─────────────────────────────────┐
│                          ACCESS CONTROLS                             │
│  - Principle of least privilege                                     │
│  - Capability-based security                                        │
│  - Audit logging for all actions                                    │
└─────────────────────────────────────────────────────────────────────┘
```

### 14.2 Integration Points

**With Runtime Monitoring:**
- Correlate trace timestamps with runtime events
- Compare trace-claimed actions with observed actions
- Detect traces that don't match runtime behavior

**With Behavioral Testing:**
- Generate test scenarios targeting edge cases
- Verify that test behavior appears in traces
- Confirm that declared values influence test outcomes

**With Outcome Monitoring:**
- Track whether stated intentions lead to stated outcomes
- Detect patterns where outcomes diverge from traces
- Build long-term behavioral profiles

**With Human Oversight:**
- Route verification failures to humans
- Require human review for consequential decisions
- Enable humans to drill down from traces to details

### 14.3 Security Maturity Model

| Level | Description | AAP Usage |
|-------|-------------|-----------|
| **L0: None** | No alignment visibility | No AAP |
| **L1: Basic** | Cards and traces exist | AAP declarations only |
| **L2: Verified** | Traces verified against cards | AAP verification active |
| **L3: Monitored** | Continuous verification + drift detection | Full AAP + monitoring |
| **L4: Defense in Depth** | AAP + behavioral testing + outcome monitoring + human oversight | Complete integration |

Most deployments should target L3 or L4. L1-L2 provide limited security value.

---

## Summary

AAP's security model provides:

1. **Authenticity**: Cards and traces cannot be forged (with proper crypto)
2. **Integrity**: Cards and traces cannot be tampered (with proper storage)
3. **Freshness**: Old cards can be detected and rejected (with proper expiration)
4. **Consistency**: Traces can be checked against declared policies
5. **Observability**: Agent behavior becomes more visible to oversight

AAP's security model does NOT provide:

1. **Completeness**: Cannot ensure all decisions are logged
2. **Truthfulness**: Cannot verify internal states match declarations
3. **Correctness**: Cannot verify decisions are right or beneficial
4. **Deception resistance**: Cannot catch sophisticated adversaries

Use AAP as one layer of defense in depth. Combine with human oversight, behavioral testing, outcome monitoring, and access controls. Maintain skepticism about any system that claims to solve alignment through transparency alone.

The goal is not perfect security. The goal is to make misalignment harder to hide, easier to detect, and more costly to attempt.

---

*AAP Security Model v0.1.0*
*Author: Vigil (conscience/protocol track)*
*This document is normative for AAP implementations.*
