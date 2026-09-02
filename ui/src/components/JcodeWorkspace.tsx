import React, { useEffect, useState } from 'react';
import { API_BASE } from '../services/api';

export const JcodeWorkspace: React.FC = () => {
  const [workspace, setWorkspace] = useState<any>(null);

  useEffect(() => {
    fetch(`${API_BASE}/coding/workspace`)
      .then((res) => res.json())
      .then((data) => setWorkspace(data))
      .catch(() => {});
  }, []);

  return (
    <div style={{ background: '#1e293b', padding: '16px', borderRadius: '8px', border: '1px solid #334155' }}>
      <h3 style={{ margin: '0 0 12px 0', color: '#10b981' }}>JCODE CODING WORKSPACE</h3>
      {workspace ? (
        <div>
          <div style={{ fontSize: '13px', color: '#cbd5e1', marginBottom: '8px' }}>
            Root Isolation: <code>{workspace.workspace_root}</code>
          </div>
          <div style={{ fontSize: '13px', color: '#cbd5e1' }}>
            Last Test Suite: <strong style={{ color: '#10b981' }}>{workspace.last_test_run.passed} passed</strong>, {workspace.last_test_run.failed} failed
          </div>
        </div>
      ) : (
        <div style={{ color: '#94a3b8', fontSize: '13px' }}>Loading Jcode workspace status...</div>
      )}
    </div>
  );
};
