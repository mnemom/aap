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
 *   EU_COMPLIANCE_AUDIT,
 *   EU_COMPLIANCE_EXTENSIONS,
 *   EU_COMPLIANCE_VALUES,
 * } from "agent-alignment-protocol";
 *
 * const card: AlignmentCard = {
 *   ...,
 *   audit: { ...EU_COMPLIANCE_AUDIT },
 *   values: { declared: EU_COMPLIANCE_VALUES, ... },
 *   extensions: { ...EU_COMPLIANCE_EXTENSIONS },
 * };
 * ```
 *
 * DISCLAIMER: These presets reflect a technical mapping of AAP features to
 * Article 50 requirements. They do not constitute legal advice. Consult
 * qualified legal counsel for your specific compliance obligations.
 */

/**
 * Audit values that satisfy Article 50(4) audit trail requirements.
 * Spread into the unified card's `audit` section.
 */
export const EU_COMPLIANCE_AUDIT = {
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

/**
 * Extension block for EU AI Act Article 15 (Accuracy, Robustness, Cybersecurity).
 *
 * Declares that the agent uses AIP-based monitoring for Article 15 obligations.
 * Spread into `extensions` alongside `EU_COMPLIANCE_EXTENSIONS` for combined
 * Article 50 + Article 15 coverage.
 *
 * @example
 * ```typescript
 * const card: AlignmentCard = {
 *   ...,
 *   extensions: {
 *     ...EU_COMPLIANCE_EXTENSIONS,
 *     ...EU_COMPLIANCE_ARTICLE_15_EXTENSIONS,
 *   },
 * };
 * ```
 */
export const EU_COMPLIANCE_ARTICLE_15_EXTENSIONS = {
  eu_ai_act_article_15: {
    accuracy_monitoring: true,
    robustness_monitoring: true,
    cybersecurity_monitoring: true,
    monitoring_protocol: "aip-v1",
    compliance_version: "2026-08",
  },
} as const;
