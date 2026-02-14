/**
 * EU AI Act Article 50 compliance presets for AAP.
 *
 * These presets provide recommended configuration values for deploying
 * AAP-instrumented agents in EU jurisdictions subject to AI Act
 * transparency obligations. Spread them into your AlignmentCard fields.
 *
 * @example
 * ```typescript
 * import {
 *   EU_COMPLIANCE_AUDIT_COMMITMENT,
 *   EU_COMPLIANCE_EXTENSIONS,
 *   EU_COMPLIANCE_VALUES,
 * } from "agent-alignment-protocol";
 *
 * const card: AlignmentCard = {
 *   ...,
 *   audit_commitment: { ...EU_COMPLIANCE_AUDIT_COMMITMENT },
 *   values: { declared: EU_COMPLIANCE_VALUES, ... },
 *   extensions: { ...EU_COMPLIANCE_EXTENSIONS },
 * };
 * ```
 *
 * DISCLAIMER: These presets reflect a technical mapping of AAP features to
 * Article 50 requirements. They do not constitute legal advice. Consult
 * qualified legal counsel for your specific compliance obligations.
 */

/** Audit commitment values that satisfy Article 50(4) audit trail requirements. */
export const EU_COMPLIANCE_AUDIT_COMMITMENT = {
  retention_days: 90,
  queryable: true,
  query_endpoint: "https://audit.example.com/traces",
  tamper_evidence: "append_only" as const,
  trace_format: "ap-trace-v1",
} as const;

/** Extension block for EU AI Act metadata on the Alignment Card. */
export const EU_COMPLIANCE_EXTENSIONS = {
  eu_ai_act: {
    article_50_compliant: true,
    ai_system_classification: "general_purpose",
    disclosure_text:
      "This system is powered by an AI agent. Its decisions are logged " +
      "and auditable. You may request a human review of any decision.",
    compliance_version: "2026-08",
  },
} as const;

/** Recommended declared values for Article 50 transparency obligations. */
export const EU_COMPLIANCE_VALUES = [
  "transparency",
  "honesty",
  "user_control",
  "principal_benefit",
] as const;
