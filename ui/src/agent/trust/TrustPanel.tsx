import React from 'react';
import { ConstitutionStatus } from '../api/types';
import { ConstitutionPanel } from './ConstitutionPanel';
import { PermissionStatus } from './PermissionStatus';

export const TrustPanel: React.FC<{ constitution: ConstitutionStatus | null }> = ({ constitution }) => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
      <h3 style={{ margin: '0 0 8px 0', color: '#10b981' }}>TRUST & SAFETY GOVERNANCE</h3>
      <ConstitutionPanel status={constitution} />
      <PermissionStatus />
    </div>
  );
};
