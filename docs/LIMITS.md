# What AAP Does and Doesn't Guarantee

Honesty about limitations is essential for credibility.

## What AAP Provides

### Transparency
- Standardized format for declaring alignment properties
- Audit trail of decision-making process
- Machine-readable value declarations

### Interoperability
- Common vocabulary for alignment across agents
- Integration patterns for A2A and MCP
- Protocol for value-coherence verification

### Accountability Infrastructure
- Queryable audit logs
- Traceable decision history
- Clear escalation patterns

## What AAP Does NOT Guarantee

### No Behavioral Guarantee
AAP does **not** guarantee agents will behave as declared. An agent can declare values and then violate them. AAP makes claims observable, not enforceable.

### No Deception Protection
AAP does **not** protect against sophisticated deception. A malicious agent can:
- Declare false values
- Generate misleading traces
- Game compatibility checks

AAP is a transparency protocol. It surfaces information but does not verify truthfulness.

### No Safety Certification
AAP does **not** certify agents as "safe" or "trustworthy." Compliance with AAP means:
- The agent declares its alignment properties
- The agent logs its decisions
- The agent participates in value coherence handshakes

It does **not** mean the agent is aligned, beneficial, or safe.

### No Human Replacement
AAP does **not** replace human judgment for consequential decisions. It provides:
- Information for humans to evaluate
- Escalation triggers for human involvement
- Audit trails for human review

The final authority for high-stakes decisions remains with humans.

## The Right Mental Model

Think of AAP like financial auditing standards:
- GAAP doesn't prevent fraud—it makes fraud harder to hide
- AAP doesn't prevent misalignment—it makes misalignment harder to hide

Transparency is valuable even without enforcement. Markets can price observed behavior. Regulators can audit. Reputation can accumulate.

## Security Considerations

See [SPEC.md](SPEC.md#security-considerations) for the security model, threat analysis, and mitigation strategies.
