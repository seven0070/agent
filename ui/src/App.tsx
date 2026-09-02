import React, { useEffect, useState, Suspense } from 'react';
import { AgentOverlay } from './agent/overlay/AgentOverlay';
import { agentStore, AgentState } from './agent/state/agentStore';

import {
  AgentServerUIProviders,
  ConversationPanel,
  FileExplorer,
  TerminalPanel,
} from '@openhands/agent-canvas';

export const App: React.FC = () => {
  const [storeState, setStoreState] = useState<AgentState>(agentStore.getState());

  useEffect(() => {
    return agentStore.subscribe(() => {
      setStoreState({ ...agentStore.getState() });
    });
  }, []);

  return (
    <AgentServerUIProviders>
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          height: '100vh',
          width: '100vw',
          background: '#020617',
          color: '#f8fafc',
          overflow: 'hidden',
          position: 'relative',
        }}
      >
        {/* Workspace Foundation Layer: OpenHands Agent Canvas Panels */}
        <div
          id="openhands-workspace-foundation"
          style={{
            position: 'absolute',
            inset: 0,
            zIndex: 1,
            display: 'grid',
            gridTemplateColumns: '280px 1fr 1fr',
            height: '100%',
            width: '100%',
            overflow: 'hidden',
            background: '#0f172a',
          }}
        >
          {/* OpenHands File Explorer Workspace Panel */}
          <div
            style={{
              borderRight: '1px solid #334155',
              overflowY: 'auto',
              background: '#090d16',
            }}
          >
            <Suspense fallback={<div style={{ padding: '16px', color: '#64748b' }}>Loading File Workspace...</div>}>
              <FileExplorer files={storeState.workspaceFiles || []} />
            </Suspense>
          </div>

          {/* OpenHands Conversation Panel */}
          <div
            style={{
              borderRight: '1px solid #334155',
              display: 'flex',
              flexDirection: 'column',
              overflow: 'hidden',
              background: '#0f172a',
            }}
          >
            <Suspense fallback={<div style={{ padding: '16px', color: '#64748b' }}>Loading Conversation Canvas...</div>}>
              <ConversationPanel />
            </Suspense>
          </div>

          {/* OpenHands Terminal Panel */}
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              overflow: 'hidden',
              background: '#020617',
            }}
          >
            <Suspense fallback={<div style={{ padding: '16px', color: '#64748b' }}>Loading Terminal...</div>}>
              <TerminalPanel />
            </Suspense>
          </div>
        </div>

        {/* Control Layer: Native Agent Overlay */}
        <div
          id="agent-control-overlay"
          style={{
            position: 'relative',
            zIndex: 10,
            height: '100%',
            width: '100%',
            pointerEvents: 'none',
          }}
        >
          <AgentOverlay />
        </div>

        {/* OpenHands Open Source Attribution Footer */}
        <div
          style={{
            position: 'absolute',
            bottom: '4px',
            right: '12px',
            zIndex: 20,
            fontSize: '10px',
            color: '#475569',
            pointerEvents: 'none',
          }}
        >
          Workspace powered by OpenHands (MIT License)
        </div>
      </div>
    </AgentServerUIProviders>
  );
};
