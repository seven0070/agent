export type JsonValue = string | number | boolean | null | JsonValue[] | { [key: string]: JsonValue };

export type SessionRecord = {
  session_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
  active_plan_id: string | null;
  metadata: Record<string, JsonValue>;
};

export type ChatMessage = {
  id: string;
  role: string;
  content: string;
};

export type ActivityEvent = {
  event_type: string;
  session_id?: string;
  payload?: Record<string, JsonValue>;
  timestamp?: string;
};

export type PlanTask = {
  id: string;
  description: string;
  dependencies: string[];
  status: string;
  required_tool_id: string | null;
  inputs: Record<string, JsonValue>;
  outputs: JsonValue;
  retry_count: number;
  max_retries: number;
  error: string | null;
  metadata: Record<string, JsonValue>;
};

export type PlanRecord = {
  plan_id: string;
  status: string;
  goal?: string;
  version?: string;
  tasks: PlanTask[];
};

export type ToolRecord = {
  tool_id: string;
  description: string;
  risk_level: string;
  permission: string;
};

export type WorkspaceFile = {
  id: string;
  name: string;
  path: string;
  type: string;
  size_bytes: number;
  modified_at: string;
};

export type WorkspaceListing = {
  workspace_root: string;
  files: WorkspaceFile[];
};

export type MemoryHit = {
  id?: string;
  type?: string;
  content?: string;
  source?: string;
  session_id?: string;
  role?: string;
};

export type CodingWorkspace = {
  status: string;
  active_task: string | null;
  workspace_root: string;
  changed_files: string[];
  last_test_run: { passed: number; failed: number; status: string };
};

export type RuntimeSettings = {
  model_provider?: string;
  model_name?: string;
  local_model_host?: string;
  runtime_timeout_seconds?: number;
  data_dir?: string;
  evolution_mode?: string;
  agent_version?: string;
  constitution_locked?: boolean;
  permissions?: Record<string, string>;
};

export type ConstitutionStatus = {
  protected: boolean;
  invariants: Array<{ name: string; description: string }>;
  protected_boundaries: string[];
};

export type EvolutionCandidate = {
  id: string;
  mutationId: string;
  currentVersion?: string;
  candidateVersion?: string;
  status: string;
  createdAt?: string;
  target?: string;
  risk_level?: string;
  requires_human_approval?: boolean;
  rationale?: string;
  canary_status?: string | null;
  workspace_dir?: string | null;
  candidate_status?: string | null;
};

export type EvolutionStatus = {
  mode: string;
  active_generation: string;
  pending_mutations: number;
  canary_deployments: Array<Record<string, JsonValue>>;
  candidates: EvolutionCandidate[];
  proposals: Array<Record<string, JsonValue>>;
  lineage: Array<Record<string, JsonValue>>;
  gate: Record<string, JsonValue> | null;
  evaluations: Array<Record<string, JsonValue>>;
  pending_approvals: Array<Record<string, JsonValue>>;
};

export type AuditEvent = {
  timestamp: string;
  event_type: string;
  subsystem?: string;
  action?: string;
  result?: string;
  risk_level?: string;
  mutation_id?: string | null;
};

export function asRecord(value: unknown): Record<string, JsonValue> {
  if (value && typeof value === "object" && !Array.isArray(value)) {
    return value as Record<string, JsonValue>;
  }
  return {};
}

export function asString(value: unknown, fallback = ""): string {
  if (typeof value === "string") return value;
  if (value == null) return fallback;
  return String(value);
}
