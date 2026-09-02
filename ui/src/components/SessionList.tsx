import React from 'react';
import { Session } from '../services/api';

interface SessionListProps {
  sessions: Session[];
  activeSessionId: string;
  onSelectSession: (sessionId: string) => void;
  onCreateSession: () => void;
}

export const SessionList: React.FC<SessionListProps> = ({
  sessions,
  activeSessionId,
  onSelectSession,
  onCreateSession,
}) => {
  return (
    <div style={{ width: '260px', background: '#0f172a', borderRight: '1px solid #334155', padding: '16px' }}>
      <button
        onClick={onCreateSession}
        style={{
          width: '100%',
          padding: '10px',
          borderRadius: '6px',
          background: '#0284c7',
          color: '#ffffff',
          border: 'none',
          cursor: 'pointer',
          marginBottom: '16px',
          fontWeight: 'bold',
        }}
      >
        + New Session
      </button>

      <h4 style={{ color: '#94a3b8', margin: '0 0 12px 0' }}>ACTIVE SESSIONS</h4>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {sessions.map((s) => (
          <div
            key={s.session_id}
            onClick={() => onSelectSession(s.session_id)}
            style={{
              padding: '10px',
              borderRadius: '6px',
              background: s.session_id === activeSessionId ? '#1e293b' : 'transparent',
              border: s.session_id === activeSessionId ? '1px solid #38bdf8' : '1px solid transparent',
              cursor: 'pointer',
              fontSize: '14px',
            }}
          >
            <div style={{ fontWeight: 'bold', color: '#f1f5f9' }}>{s.title}</div>
            <div style={{ fontSize: '11px', color: '#64748b' }}>ID: {s.session_id}</div>
          </div>
        ))}
      </div>
    </div>
  );
};
