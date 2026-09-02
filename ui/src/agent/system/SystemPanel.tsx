import React, { useEffect, useState } from 'react';
import { API_BASE } from '../api/agentApi';

export const SystemPanel: React.FC = () => {
  const [health, setHealth] = useState<any>(null);

  useEffect(() => {
    fetch(`${API_BASE}/system/health`)
      .then((res) => res.json())
      .then((data) => setHealth(data))
      .catch(() => {});
  }, []);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
      <h3 style={{ margin: '0 0 8px 0', color: '#38bdf8' }}>SYSTEM HEALTH & SUBSYSTEMS</h3>
      {health ? (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: '8px' }}>
          {Object.entries(health.layers || {}).map(([layer, st]: [string, any]) => (
            <div key={layer} style={{ padding: '8px', background: '#0f172a', borderRadius: '6px', borderLeft: '3px solid #10b981' }}>
              <div style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase' }}>{layer}</div>
              <div style={{ fontSize: '12px', color: '#10b981', fontWeight: 'bold' }}>● {st}</div>
            </div>
          ))}
        </div>
      ) : (
        <div style={{ padding: '12px', background: '#0f172a', borderRadius: '6px', color: '#94a3b8', fontSize: '12px' }}>
          Connecting to System Health API...
        </div>
      )}
    </div>
  );
};
