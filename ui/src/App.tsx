import React, { Suspense } from 'react';
import { AgentOverlay } from './agent/overlay/AgentOverlay';

// Import OpenHands Agent Canvas workspace foundation component where available
const OpenHandsCanvas = React.lazy(() =>
  import('@openhands/agent-canvas')
    .then((mod: any) => ({ default: mod.AgentCanvas || mod.default || (() => null) }))
    .catch(() => ({ default: () => null }))
);

export const App: React.FC = () => {
  return (
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
      {/* Workspace Foundation Layer: OpenHands Agent Canvas */}
      <div
        id="openhands-workspace-foundation"
        style={{
          position: 'absolute',
          inset: 0,
          zIndex: 1,
          overflow: 'hidden',
        }}
      >
        <Suspense
          fallback={
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                height: '100%',
                color: '#64748b',
                fontSize: '14px',
              }}
            >
              Loading Agent Workspace Foundation...
            </div>
          }
        >
          <OpenHandsCanvas />
        </Suspense>
      </div>

      {/* Control Layer: Native Agent Overlay */}
      <div
        id="agent-control-overlay"
        style={{
          position: 'relative',
          zIndex: 10,
          height: '100%',
          width: '100%',
          pointerEvents: 'box-none',
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
  );
};
