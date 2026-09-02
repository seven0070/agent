import React from 'react';

export const WorkspaceStatus: React.FC = () => {
  return (
    <div style={{ padding: '12px', background: '#0f172a', borderRadius: '6px' }}>
      <div style={{ fontSize: '12px', color: '#94a3b8' }}>WORKSPACE PATH ISOLATION</div>
      <div style={{ fontSize: '13px', color: '#10b981', fontWeight: 'bold', marginTop: '4px' }}>data/workspace (Restricted)</div>
    </div>
  );
};
