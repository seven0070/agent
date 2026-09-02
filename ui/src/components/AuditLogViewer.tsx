import React, { useEffect, useState } from 'react';
import { API_BASE } from '../services/api';

export const AuditLogViewer: React.FC = () => {
  const [logs, setLogs] = useState<any[]>([]);

  useEffect(() => {
    fetch(`${API_BASE}/audit/logs`)
      .then((res) => res.json())
      .then((data) => setLogs(data))
      .catch(() => {});
  }, []);

  return (
    <div style={{ background: '#1e293b', padding: '16px', borderRadius: '8px', border: '1px solid #334155' }}>
      <h3 style={{ margin: '0 0 12px 0', color: '#f43f5e' }}>UNIFIED AUDIT TRAIL VIEWER</h3>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '200px', overflowY: 'auto' }}>
        {logs.map((log, idx) => (
          <div key={idx} style={{ fontSize: '12px', padding: '8px', background: '#0f172a', borderRadius: '4px', borderLeft: '3px solid #64748b' }}>
            <span style={{ color: '#64748b', marginRight: '8px' }}>[{log.timestamp}]</span>
            <strong style={{ color: '#f8fafc', marginRight: '8px' }}>{log.event_type}</strong>
            <span style={{ color: '#94a3b8' }}>{log.action}</span>
          </div>
        ))}
      </div>
    </div>
  );
};
