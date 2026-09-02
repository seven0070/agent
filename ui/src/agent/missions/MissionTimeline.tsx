import React from 'react';
import { MissionEvent } from '../api/types';

export const MissionTimeline: React.FC<{ events: MissionEvent[] }> = ({ events }) => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', padding: '8px' }}>
      {events.map((e) => (
        <div key={e.id} style={{ fontSize: '12px', padding: '8px', background: '#0f172a', borderRadius: '4px', borderLeft: '3px solid #38bdf8' }}>
          <span style={{ color: '#64748b', marginRight: '8px' }}>[{e.timestamp}]</span>
          <strong style={{ color: '#f8fafc', marginRight: '8px' }}>{e.type}</strong>
          <span style={{ color: '#cbd5e1' }}>{e.message}</span>
        </div>
      ))}
    </div>
  );
};
