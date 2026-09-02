import React from 'react';

export const RuntimeStatus: React.FC = () => {
  return (
    <div style={{ padding: '12px', background: '#0f172a', borderRadius: '6px', border: '1px solid #0284c7' }}>
      <div style={{ fontSize: '12px', color: '#38bdf8', fontWeight: 'bold' }}>LOCAL AGENTSCOPE RUNTIME & SANDBOX</div>
      <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '4px' }}>
        NetworkPolicy: DENY | Process Timeout: 30s | Output Cap: 1MB
      </div>
    </div>
  );
};
