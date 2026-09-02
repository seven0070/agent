import React from 'react';

export const ContextPanel: React.FC = () => {
  return (
    <div style={{ padding: '12px', background: '#0f172a', borderRadius: '6px' }}>
      <div style={{ fontSize: '12px', color: '#94a3b8' }}>RAG ENGINE & CONTEXT BUILDER</div>
      <div style={{ fontSize: '11px', color: '#cbd5e1', marginTop: '4px' }}>
        ApproxTokenChunker | Secret Scrubbing Enabled
      </div>
    </div>
  );
};
