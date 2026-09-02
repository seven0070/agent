import React, { useEffect, useState } from 'react';
import { fetchHealth, SystemHealth } from '../services/api';

export const SystemStatus: React.FC = () => {
  const [health, setHealth] = useState<SystemHealth | null>(null);

  useEffect(() => {
    fetchHealth()
      .then((data) => setHealth(data))
      .catch(() => {});
  }, []);

  return (
    <div style={{ background: '#1e293b', padding: '16px', borderRadius: '8px', border: '1px solid #334155' }}>
      <h3 style={{ margin: '0 0 12px 0', color: '#38bdf8' }}>SYSTEM STATUS</h3>
      {health ? (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: '8px' }}>
          {Object.entries(health.layers).map(([layer, st]) => (
            <div
              key={layer}
              style={{
                padding: '8px',
                borderRadius: '6px',
                background: '#0f172a',
                borderLeft: '3px solid #10b981',
              }}
            >
              <div style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase' }}>{layer}</div>
              <div style={{ fontSize: '13px', fontWeight: 'bold', color: '#10b981' }}>● {st}</div>
            </div>
          ))}
        </div>
      ) : (
        <div style={{ color: '#94a3b8', fontSize: '13px' }}>Connecting to local API...</div>
      )}
    </div>
  );
};
