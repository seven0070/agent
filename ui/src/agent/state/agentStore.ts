/**
 * Agent State Management Store for Overlay UI.
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
} from '../api/agentApi';

export interface AgentState {
  activeTab: 'missions' | 'evolution' | 'trust' | 'coding' | 'runtime' | 'memory' | 'approvals' | 'system';
  overlayOpen: boolean;
  missions: AgentMission[];
  evolutionCandidates: EvolutionCandidate[];
  approvals: ApprovalRequest[];
  constitution: ConstitutionStatus | null;
}

class AgentStore {
  private state: AgentState = {
    activeTab: 'missions',
    overlayOpen: true,
    missions: [],
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

  public toggleOverlay(): void {
    this.state.overlayOpen = !this.state.overlayOpen;
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
