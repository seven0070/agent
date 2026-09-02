/**
 * Dynamic Agent State Store managing active sessions, workspace files, and event streams.
 */

import {
  AgentMission,
  EvolutionCandidate,
  ApprovalRequest,
  ConstitutionStatus,
} from '../api/types';
import {
  fetchMissions,
  fetchEvolutionCandidates,
  fetchApprovals,
  resolveApproval as resolveApprovalApi,
  fetchConstitutionStatus,
  createSession as createSessionApi,
  fetchWorkspaceFiles,
} from '../api/agentApi';

export interface AgentState {
  activeSessionId: string | null;
  activeTab: 'missions' | 'evolution' | 'trust' | 'coding' | 'runtime' | 'memory' | 'approvals' | 'system';
  overlayOpen: boolean;
  missions: AgentMission[];
  workspaceFiles: any[];
  evolutionCandidates: EvolutionCandidate[];
  approvals: ApprovalRequest[];
  constitution: ConstitutionStatus | null;
}

class AgentStore {
  private state: AgentState = {
    activeSessionId: null,
    activeTab: 'missions',
    overlayOpen: true,
    missions: [],
    workspaceFiles: [],
    evolutionCandidates: [],
    approvals: [],
    constitution: null,
  };

  private listeners: Set<() => void> = new Set();

  public getState(): AgentState {
    return this.state;
  }

  public subscribe(listener: () => void): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  private notify(): void {
    this.listeners.forEach((fn) => fn());
  }

  public setActiveTab(tab: AgentState['activeTab']): void {
    this.state.activeTab = tab;
    this.notify();
  }

  public setActiveSessionId(sessionId: string): void {
    this.state.activeSessionId = sessionId;
    this.loadWorkspaceFiles(sessionId);
    this.notify();
  }

  public toggleOverlay(): void {
    this.state.overlayOpen = !this.state.overlayOpen;
    this.notify();
  }

  public async createNewSession(title?: string): Promise<string> {
    const session = await createSessionApi(title);
    this.state.activeSessionId = session.session_id;
    await this.loadAll();
    return session.session_id;
  }

  public async loadWorkspaceFiles(sessionId?: string): Promise<void> {
    const files = await fetchWorkspaceFiles(sessionId || this.state.activeSessionId || undefined);
    this.state.workspaceFiles = files;
    this.notify();
  }

  public async loadAll(): Promise<void> {
    try {
      const [missions, candidates, approvals, constStatus] = await Promise.all([
        fetchMissions(),
        fetchEvolutionCandidates(),
        fetchApprovals(),
        fetchConstitutionStatus(),
      ]);
      this.state.missions = missions;
      if (missions.length > 0 && !this.state.activeSessionId) {
        this.state.activeSessionId = missions[0].id;
      }
      await this.loadWorkspaceFiles();
      this.state.evolutionCandidates = candidates;
      this.state.approvals = approvals;
      this.state.constitution = constStatus;
      this.notify();
    } catch {
      // API Offline fallback
    }
  }

  public async resolveApproval(id: string, approved: boolean): Promise<void> {
    await resolveApprovalApi(id, approved);
    this.state.approvals = this.state.approvals.filter((a) => a.id !== id);
    this.notify();
  }
}

export const agentStore = new AgentStore();
