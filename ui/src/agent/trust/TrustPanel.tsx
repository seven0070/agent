import React, { useEffect, useState } from 'react';
import { ConstitutionStatus } from '../api/types';
import { ConstitutionPanel } from './ConstitutionPanel';
import { PermissionStatus } from './PermissionStatus';
import { API_BASE } from '../api/agentApi';

export const TrustPanel: React.FC<{ constitution: ConstitutionStatus | null }> = ({ constitution }) => {
  const [health, setHealth] = useState<any>(null);

  useEffect(() => {
    fetch(`${API_BASE}/system/health`)
      .then((res) => res.json())
      .then((data) => setHealth(data))
      .catch(() => {});
  }, []);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
      <h3 style={{ margin: '0 0 8px 0', color: '#10b981' }}>TRUST & SAFETY GOVERNANCE</h3>
      <ConstitutionPanel status={constitution} />
      <PermissionStatus />
      {health && (
        <div style={{ fontSize: '11px', color: '#64748b' }}>
          Layer -1 Active Status: {health.layers?.constitution || 'active'} | Broker: {health.layers?.capabilities || 'active'}
        </div>
      )}
    </div>
  );
};
