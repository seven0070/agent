import React, { useEffect, useState } from 'react';
import { RuntimeStatus } from './RuntimeStatus';
import { API_BASE } from '../api/agentApi';

export const RuntimePanel: React.FC = () => {
  const [health, setHealth] = useState<any>(null);

  useEffect(() => {
    fetch(`${API_BASE}/system/health`)
      .then((res) => res.json())
      .then((data) => setHealth(data))
      .catch(() => {});
  }, []);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
      <h3 style={{ margin: '0 0 8px 0', color: '#0284c7' }}>RUNTIME & SANDBOX CONTROLS</h3>
      <RuntimeStatus />
      {health && (
        <div style={{ padding: '12px', background: '#0f172a', borderRadius: '6px', fontSize: '12px', color: '#cbd5e1' }}>
          Layer 7 Runtime Sandbox Status: <strong style={{ color: '#10b981' }}>{health.layers?.runtime || 'active'}</strong>
        </div>
      )}
    </div>
  );
};
