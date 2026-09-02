import React, { useEffect, useState } from 'react';
import { WorkspaceStatus } from './WorkspaceStatus';
import { CodingActivity } from './CodingActivity';
import { API_BASE } from '../api/agentApi';

export const CodingPanel: React.FC = () => {
  const [workspace, setWorkspace] = useState<any>(null);

  useEffect(() => {
    fetch(`${API_BASE}/coding/workspace`)
      .then((res) => res.json())
      .then((data) => setWorkspace(data))
      .catch(() => {});
  }, []);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
      <h3 style={{ margin: '0 0 8px 0', color: '#10b981' }}>JCODE CODING SUBSYSTEM WORKSPACE</h3>
      <WorkspaceStatus />
      <CodingActivity />
      {workspace && (
        <div style={{ padding: '12px', background: '#0f172a', borderRadius: '6px', fontSize: '12px', color: '#cbd5e1' }}>
          Status: <strong style={{ color: '#38bdf8' }}>{workspace.status}</strong> | Root: <code>{workspace.workspace_root}</code>
        </div>
      )}
    </div>
  );
};
