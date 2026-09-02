import React from 'react';

export const EvolutionTimeline: React.FC = () => {
  return (
    <div style={{ padding: '12px', background: '#0f172a', borderRadius: '6px' }}>
      <div style={{ fontSize: '12px', fontWeight: 'bold', color: '#a855f7', marginBottom: '8px' }}>EVOLUTION CONTROL TIMELINE</div>
      <div style={{ fontSize: '11px', color: '#94a3b8' }}>OBSERVE → PROPOSE → EXPERIMENT → GATE → CANARY → PROMOTE</div>
    </div>
  );
};
