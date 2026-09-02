import React, { useEffect, useState } from 'react';
import { AgentMission } from '../api/types';
import { MissionStatus } from './MissionStatus';
import { API_BASE } from '../api/agentApi';

export const MissionPanel: React.FC<{ missions: AgentMission[] }> = ({ missions }) => {
  const [selectedPlan, setSelectedPlan] = useState<any>(null);

  useEffect(() => {
    if (missions.length > 0) {
      fetch(`${API_BASE}/plans/${missions[0].id}`)
        .then((res) => res.json())
        .then((data) => setSelectedPlan(data))
        .catch(() => {});
    }
  }, [missions]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
      <h3 style={{ margin: '0 0 8px 0', color: '#38bdf8' }}>MISSION CONTROL & LAYER 5 ORCHESTRATION</h3>
      {missions.length === 0 ? (
        <div style={{ color: '#94a3b8', fontSize: '13px' }}>No active or past agent missions.</div>
      ) : (
        missions.map((m) => (
          <div key={m.id} style={{ padding: '14px', background: '#0f172a', borderRadius: '8px', border: '1px solid #334155' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <span style={{ fontWeight: 'bold', fontSize: '14px', color: '#f8fafc' }}>{m.title}</span>
              <MissionStatus status={m.status} />
            </div>
            <div style={{ fontSize: '11px', color: '#64748b' }}>Mission ID: {m.id} | Started: {m.createdAt}</div>
          </div>
        ))
      )}

      {selectedPlan && (
        <div style={{ padding: '12px', background: '#0f172a', borderRadius: '8px', border: '1px solid #0284c7', marginTop: '8px' }}>
          <div style={{ fontSize: '12px', fontWeight: 'bold', color: '#38bdf8', marginBottom: '8px' }}>ACTIVE PLAN DAG [{selectedPlan.plan_id}]</div>
          {selectedPlan.tasks.map((t: any) => (
            <div key={t.id} style={{ fontSize: '12px', color: '#cbd5e1', padding: '4px 0' }}>
              ● {t.id}: {t.description} — <strong style={{ color: t.status === 'SUCCEEDED' ? '#10b981' : '#f59e0b' }}>{t.status}</strong>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
