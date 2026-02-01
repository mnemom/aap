/**
 * Value Coherence Handshake messages - Agent-to-agent alignment verification.
 *
 * Defines the message types for the Value Coherence Handshake protocol
 * per SPEC Section 6.
 *
 * @see SPEC.md Section 6 for complete specification.
 */

import type { AlignmentCard } from "./alignment-card";

/** Information about the agent making a request. */
export interface RequesterInfo {
  /** Agent identifier (DID, URL, or UUID) */
  agent_id: string;
  /** Requester's Alignment Card ID */
  card_id: string;
}

/** Context about the task for which alignment is being checked. */
export interface TaskContext {
  /** Type of task being proposed */
  task_type: string;
  /** Values required for this task */
  values_required?: string[] | null;
  /** Categories of data involved */
  data_categories?: string[] | null;
}

/** Request for an agent's Alignment Card (SPEC Section 6.3.1). */
export interface AlignmentCardRequest {
  /** Message type identifier */
  message_type?: "alignment_card_request";
  /** Unique request identifier */
  request_id: string;
  /** Information about requesting agent */
  requester: RequesterInfo;
  /** Context about the proposed task */
  task_context?: TaskContext | null;
  /** When request was made (ISO 8601) */
  timestamp?: string;
}

/** Cryptographic signature for authentication. */
export interface Signature {
  /** Signature algorithm (e.g., Ed25519) */
  algorithm: string;
  /** Base64-encoded signature */
  value: string;
  /** Key identifier */
  key_id: string;
}

/** Response with an agent's Alignment Card (SPEC Section 6.3.2). */
export interface AlignmentCardResponse {
  /** Message type identifier */
  message_type?: "alignment_card_response";
  /** Request ID being responded to */
  request_id: string;
  /** Responder's Alignment Card */
  alignment_card: AlignmentCard;
  /** Optional signature for authentication */
  signature?: Signature | null;
  /** When response was made (ISO 8601) */
  timestamp?: string;
}

/** Data sharing specification for collaboration. */
export interface DataSharing {
  /** Data categories initiator will share */
  from_initiator?: string[];
  /** Data categories responder will share */
  from_responder?: string[];
}

/** Scope of autonomous actions for collaboration. */
export interface AutonomyScope {
  /** Actions initiator may take */
  initiator_actions?: string[];
  /** Actions responder may take */
  responder_actions?: string[];
}

/** Proposed collaboration details. */
export interface ProposedCollaboration {
  /** Type of task */
  task_type: string;
  /** Values both agents should apply */
  values_intersection?: string[] | null;
  /** Data sharing specification */
  data_sharing?: DataSharing | null;
  /** Scope of autonomous actions */
  autonomy_scope?: AutonomyScope | null;
}

/** Value coherence check request (SPEC Section 6.3.3). */
export interface ValueCoherenceCheck {
  /** Message type identifier */
  message_type?: "value_coherence_check";
  /** Request ID */
  request_id: string;
  /** Initiator's Alignment Card ID */
  initiator_card_id: string;
  /** Responder's Alignment Card ID */
  responder_card_id: string;
  /** Proposed collaboration details */
  proposed_collaboration: ProposedCollaboration;
  /** When check was requested (ISO 8601) */
  timestamp?: string;
}

/** A conflict between values declared by two agents. */
export interface ValueConflict {
  /** Value from initiating agent */
  initiator_value: string;
  /** Value from responding agent */
  responder_value: string;
  /** Type of conflict (incompatible, priority_mismatch, etc.) */
  conflict_type: string;
  /** Human-readable explanation */
  description: string;
}

/** Detailed value alignment analysis. */
export interface ValueAlignmentDetail {
  /** Values present in both cards */
  matched?: string[];
  /** Values in one card but not the other */
  unmatched?: string[];
  /** Direct value conflicts */
  conflicts?: ValueConflict[];
}

/** Coherence assessment. */
export interface Coherence {
  /** Whether agents are compatible */
  compatible: boolean;
  /** Coherence score (0.0 to 1.0) */
  score: number;
  /** Detailed alignment analysis */
  value_alignment: ValueAlignmentDetail;
}

/** Proposed resolution for value conflicts. */
export interface ProposedResolution {
  /** Resolution type */
  type: string;
  /** Why this resolution is proposed */
  reason: string;
  /** Alternative proposal (if applicable) */
  alternative?: Record<string, unknown> | null;
}

/** Coherence result message (SPEC Section 6.3.4). */
export interface CoherenceResultMessage {
  /** Message type identifier */
  message_type?: "coherence_result";
  /** Request ID being responded to */
  request_id: string;
  /** Coherence assessment */
  coherence: Coherence;
  /** Whether to proceed with coordination */
  proceed: boolean;
  /** Conditions for proceeding (if any) */
  conditions?: string[] | null;
  /** Proposed resolution (if conflicts exist) */
  proposed_resolution?: ProposedResolution | null;
  /** When result was generated (ISO 8601) */
  timestamp?: string;
}

/** Union of all Value Coherence Handshake message types. */
export type ValueCoherenceMessage =
  | AlignmentCardRequest
  | AlignmentCardResponse
  | ValueCoherenceCheck
  | CoherenceResultMessage;
