import React from 'react';
import { AgentOverlay } from './agent/overlay/AgentOverlay';

export const App: React.FC = () => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', width: '100vw', background: '#020617', color: '#f8fafc', overflow: 'hidden' }}>
      {/* Workspace Foundation (OpenHands Canvas Base) */}
      <div style={{ flex: 1, position: 'relative' }}>
        <AgentOverlay />
      </div>
    </div>
  );
};
