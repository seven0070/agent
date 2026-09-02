import React from 'react';
import { ContextPanel } from './ContextPanel';

export const MemoryPanel: React.FC = () => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
      <h3 style={{ margin: '0 0 8px 0', color: '#eab308' }}>MEMORY & KNOWLEDGE STORE</h3>
      <ContextPanel />
    </div>
  );
};
