import React from 'react';

export const SystemPanel: React.FC = () => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
      <h3 style={{ margin: '0 0 8px 0', color: '#38bdf8' }}>SYSTEM HEALTH & AGENT SUBSYSTEMS</h3>
      <div style={{ padding: '12px', background: '#0f172a', borderRadius: '6px', color: '#10b981', fontWeight: 'bold' }}>
        ● All Layers (-1 through 10) Operating Normally
      </div>
    </div>
  );
};
