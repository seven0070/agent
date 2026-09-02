import React from 'react';
import { WorkspaceStatus } from './WorkspaceStatus';
import { CodingActivity } from './CodingActivity';

export const CodingPanel: React.FC = () => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
      <h3 style={{ margin: '0 0 8px 0', color: '#10b981' }}>JCODE CODING SUBSYSTEM WORKSPACE</h3>
      <WorkspaceStatus />
      <CodingActivity />
    </div>
  );
};
