import React from 'react';

export const VersionLineage: React.FC<{ activeGen: string }> = ({ activeGen }) => {
  return (
    <div style={{ padding: '12px', background: '#0f172a', borderRadius: '6px', border: '1px solid #334155' }}>
      <div style={{ fontSize: '11px', color: '#94a3b8' }}>ACTIVE METAMORPHOSIS GENERATION</div>
      <div style={{ fontSize: '16px', fontWeight: 'bold', color: '#a855f7', marginTop: '4px' }}>{activeGen}</div>
    </div>
  );
};
