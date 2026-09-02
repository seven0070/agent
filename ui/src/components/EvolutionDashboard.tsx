import React, { useEffect, useState } from 'react';
import { API_BASE } from '../services/api';

export const EvolutionDashboard: React.FC = () => {
  const [evoStatus, setEvoStatus] = useState<any>(null);

  useEffect(() => {
    fetch(`${API_BASE}/evolution/status`)
      .then((res) => res.json())
      .then((data) => setEvoStatus(data))
      .catch(() => {});
  }, []);

  return (
    <div style={{ background: '#1e293b', padding: '16px', borderRadius: '8px', border: '1px solid #334155' }}>
      <h3 style={{ margin: '0 0 12px 0', color: '#a855f7' }}>EVOLUTION & METAMORPHOSIS CONTROL PLANE</h3>
      {evoStatus ? (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
          <div style={{ background: '#0f172a', padding: '12px', borderRadius: '6px' }}>
            <div style={{ fontSize: '12px', color: '#94a3b8' }}>Operational Mode</div>
            <div style={{ fontSize: '18px', fontWeight: 'bold', color: '#38bdf8' }}>{evoStatus.mode}</div>
          </div>
          <div style={{ background: '#0f172a', padding: '12px', borderRadius: '6px' }}>
            <div style={{ fontSize: '12px', color: '#94a3b8' }}>Active Generation</div>
            <div style={{ fontSize: '18px', fontWeight: 'bold', color: '#10b981' }}>{evoStatus.active_generation}</div>
          </div>
        </div>
      ) : (
        <div style={{ color: '#94a3b8', fontSize: '13px' }}>Loading Evolution Controller state...</div>
      )}
    </div>
  );
};
