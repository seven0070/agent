import React from 'react';
import { AgentMission } from '../api/types';
import { MissionStatus } from './MissionStatus';

export const MissionPanel: React.FC<{ missions: AgentMission[] }> = ({ missions }) => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
      <h3 style={{ margin: '0 0 8px 0', color: '#38bdf8' }}>MISSION CONTROL & ORCHESTRATION</h3>
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
    </div>
  );
};
