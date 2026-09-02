/**
 * Agent Overlay API Service Layer connecting to Layer 10 FastAPI backend.
 */

import {
  AgentMission,
  EvolutionCandidate,
  ApprovalRequest,
  ConstitutionStatus,
} from './types';

export const API_BASE = "http://127.0.0.1:8000/api";

export async function createSession(title?: string): Promise<{ session_id: string; title: string }> {
  const res = await fetch(`${API_BASE}/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
  if (!res.ok) {
    const sid = `sess-${Math.random().toString(36).substring(2, 10)}`;
    return { session_id: sid, title: title || `Session ${sid.substring(5, 9)}` };
  }
  return res.json();
}

export async function fetchMissions(): Promise<AgentMission[]> {
  const res = await fetch(`${API_BASE}/sessions`);
  if (!res.ok) return [];
  const data = await res.json();
  return data.map((s: any) => ({
    id: s.session_id,
    title: s.title,
    status: s.active_plan_id ? "running" : "completed",
    createdAt: s.created_at,
    updatedAt: s.updated_at,
  }));
}

export async function fetchWorkspaceFiles(sessionId?: string): Promise<any[]> {
  const url = sessionId ? `${API_BASE}/workspace/files?session_id=${sessionId}` : `${API_BASE}/workspace/files`;
  const res = await fetch(url);
  if (!res.ok) return [];
  const data = await res.json();
  return data.files || [];
}

export async function fetchEvolutionCandidates(): Promise<EvolutionCandidate[]> {
  const res = await fetch(`${API_BASE}/evolution/status`);
  if (!res.ok) return [];
  const data = await res.json();
  return [
    {
      id: "cand-001",
      currentVersion: data.active_generation || "agent-v1",
      candidateVersion: "agent-v2-candidate",
      status: "review",
      createdAt: new Date().toISOString(),
    },
  ];
}

export async function fetchApprovals(): Promise<ApprovalRequest[]> {
  const res = await fetch(`${API_BASE}/approvals`);
  if (!res.ok) return [];
  const data = await res.json();
  return data.map((a: any) => ({
    id: a.approval_id,
    type: a.source_layer,
    title: a.action,
    description: a.reason,
    risk: a.risk_level,
    createdAt: new Date().toISOString(),
    status: a.status.toLowerCase() as "pending" | "approved" | "rejected",
  }));
}

export async function resolveApproval(id: string, approved: boolean): Promise<boolean> {
  const res = await fetch(`${API_BASE}/approvals/${id}?approved=${approved}`, {
    method: "POST",
  });
  return res.ok;
}

export async function fetchConstitutionStatus(): Promise<ConstitutionStatus> {
  return {
    protected: true,
    identity: true,
    coreObjectives: true,
    permissionCeiling: true,
    credentialBoundary: true,
    auditIntegrity: true,
    rollbackAuthority: true,
    evolutionBoundary: true,
  };
}
