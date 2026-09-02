/**
 * Agent Overlay Main Frame Component.
 * Integrates OpenHands Workspace Canvas with Native Agent Overlay/Control Layer.
 */

import React, { useEffect, useState } from 'react';
import { agentStore, AgentState } from '../state/agentStore';
import { AgentPanel } from './AgentPanel';
import { AgentCommandBar } from './AgentCommandBar';

import { MissionPanel } from '../missions/MissionPanel';
import { EvolutionPanel } from '../evolution/EvolutionPanel';
import { TrustPanel } from '../trust/TrustPanel';
import { CodingPanel } from '../coding/CodingPanel';
import { RuntimePanel } from '../runtime/RuntimePanel';
import { MemoryPanel } from '../memory/MemoryPanel';
import { ApprovalPanel } from '../approvals/ApprovalPanel';
import { SystemPanel } from '../system/SystemPanel';

export const AgentOverlay: React.FC = () => {
  const [state, setState] = useState<AgentState>(agentStore.getState());

  useEffect(() => {
    agentStore.loadAll();
    return agentStore.subscribe(() => {
      setState({ ...agentStore.getState() });
    });
  }, []);

  const handleCommand = (cmd: string) => {
    // Send command
    fetch('http://127.0.0.1:8000/api/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: 'sess-overlay', prompt: cmd }),
    });
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', width: '100%', background: '#020617' }}>
      {/* Header Bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 20px', background: '#0f172a', borderBottom: '1px solid #334155' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{ fontSize: '20px' }}>🤖</span>
          <span style={{ fontSize: '18px', fontWeight: 'bold', color: '#f8fafc' }}>Agent</span>
          <span style={{ fontSize: '11px', padding: '2px 8px', borderRadius: '12px', background: '#1e293b', color: '#38bdf8', border: '1px solid #0284c7' }}>
            Sovereign OS Active
          </span>
        </div>
        <button
          onClick={() => agentStore.toggleOverlay()}
          style={{ padding: '6px 12px', borderRadius: '4px', background: '#334155', color: '#f8fafc', border: 'none', cursor: 'pointer', fontSize: '12px' }}
        >
          {state.overlayOpen ? 'Hide Overlay' : 'Show Overlay'}
        </button>
      </div>

      {state.overlayOpen && (
        <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
          <AgentPanel activeTab={state.activeTab} onSelectTab={(tab) => agentStore.setActiveTab(tab)} />

          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            <AgentCommandBar onExecuteCommand={handleCommand} />

            <div style={{ flex: 1, padding: '16px', overflowY: 'auto' }}>
              {state.activeTab === 'missions' && <MissionPanel missions={state.missions} />}
              {state.activeTab === 'evolution' && <EvolutionPanel candidates={state.evolutionCandidates} />}
              {state.activeTab === 'trust' && <TrustPanel constitution={state.constitution} />}
              {state.activeTab === 'coding' && <CodingPanel />}
              {state.activeTab === 'runtime' && <RuntimePanel />}
              {state.activeTab === 'memory' && <MemoryPanel />}
              {state.activeTab === 'approvals' && (
                <ApprovalPanel
                  approvals={state.approvals}
                  onResolve={(id, app) => agentStore.resolveApproval(id, app)}
                />
              )}
              {state.activeTab === 'system' && <SystemPanel />}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
