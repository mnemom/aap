# AAP Architecture

## Protocol Stack

```
┌─────────────────────────────────────────────────────────┐
│                    Applications                          │
├─────────────────────────────────────────────────────────┤
│          AGENT ALIGNMENT PROTOCOL (AAP)                  │
│    Alignment Card | AP-Trace | Value Coherence          │
├─────────────────────────────────────────────────────────┤
│              A2A              │          MCP             │
│       (Task Negotiation)      │    (Tool Connectivity)   │
├─────────────────────────────────────────────────────────┤
│                    Transport Layer                       │
└─────────────────────────────────────────────────────────┘
```

## Core Components

### Alignment Card
- Extends A2A Agent Card
- Declares principal, autonomy, values
- Machine-readable, schema-validated

### AP-Trace
- Audit log format
- Decision transparency
- Queryable history

### Value Coherence Handshake
- Agent-to-agent verification
- Conflict detection
- Escalation protocol

## Design Principles

1. **Transparency over Trust** - Make behavior observable, not guaranteed
2. **Extension not Replacement** - Work with existing protocols
3. **Honest Limits** - Clear about what we don't provide
4. **Open Protocol** - Free to implement, no vendor lock-in
