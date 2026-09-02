/**
 * TypeScript Contracts for Agent System Overlay & Backend API.
 */

export type MissionStatus =
  | "queued"
  | "planning"
  | "running"
  | "waiting_approval"
  | "completed"
  | "failed"
  | "cancelled";

export interface AgentMission {
  id: string;
  title: string;
  description?: string;
  status: MissionStatus;
  progress?: number;
  createdAt: string;
  updatedAt: string;
}

export interface MissionEvent {
  id: string;
  missionId: string;
  timestamp: string;
  type: string;
  message: string;
  metadata?: Record<string, unknown>;
}

export type EvolutionStatus =
  | "observed"
  | "proposed"
  | "candidate"
  | "experiment"
  | "evaluating"
  | "review"
  | "canary"
  | "promoted"
  | "rejected"
  | "rolled_back";

export interface EvolutionCandidate {
  id: string;
  currentVersion: string;
  candidateVersion: string;
  mutationId?: string;
  status: EvolutionStatus;
  createdAt: string;
}

export interface EvaluationSummary {
  status: "pass" | "fail" | "warning";
  metrics: Record<string, number>;
  regressions: string[];
  safetyChecks: string[];
}

export interface ApprovalRequest {
  id: string;
  type: string;
  title: string;
  description: string;
  risk?: string;
  createdAt: string;
  status: "pending" | "approved" | "rejected";
}

export interface ConstitutionStatus {
  protected: boolean;
  identity: boolean;
  coreObjectives: boolean;
  permissionCeiling: boolean;
  credentialBoundary: boolean;
  auditIntegrity: boolean;
  rollbackAuthority: boolean;
  evolutionBoundary: boolean;
}
