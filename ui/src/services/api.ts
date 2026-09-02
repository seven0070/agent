/**
 * Local API Service Layer & SSE Event Stream Client.
 */

export const API_BASE = "http://127.0.0.1:8000/api";

export interface Session {
  session_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
  active_plan_id?: string;
  metadata?: Record<string, any>;
}

export interface SystemHealth {
  status: string;
  timestamp: string;
  layers: Record<string, string>;
}

export interface ApprovalRequest {
  approval_id: string;
  source_layer: string;
  action: string;
  resource: string;
  risk_level: string;
  reason: string;
  status: string;
}

export async function fetchHealth(): Promise<SystemHealth> {
  const res = await fetch(`${API_BASE}/system/health`);
  return res.json();
}

export async function fetchSessions(): Promise<Session[]> {
  const res = await fetch(`${API_BASE}/sessions`);
  return res.json();
}

export async function createSession(title?: string): Promise<Session> {
  const res = await fetch(`${API_BASE}/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
  return res.json();
}

export async function fetchApprovals(): Promise<ApprovalRequest[]> {
  const res = await fetch(`${API_BASE}/approvals`);
  return res.json();
}

export async function resolveApproval(approvalId: string, approved: boolean): Promise<any> {
  const res = await fetch(`${API_BASE}/approvals/${approvalId}?approved=${approved}`, {
    method: "POST",
  });
  return res.json();
}
