import React from 'react';
import { RuntimeStatus } from './RuntimeStatus';

export const RuntimePanel: React.FC = () => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
      <h3 style={{ margin: '0 0 8px 0', color: '#0284c7' }}>RUNTIME & SANDBOX CONTROLS</h3>
      <RuntimeStatus />
    </div>
  );
};
