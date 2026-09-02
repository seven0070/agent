/**
 * Agent Control Panel Navigation Drawer.
 */

import React from 'react';
import { AgentState } from '../state/agentStore';

interface AgentPanelProps {
  activeTab: AgentState['activeTab'];
  onSelectTab: (tab: AgentState['activeTab']) => void;
}

export const AgentPanel: React.FC<AgentPanelProps> = ({ activeTab, onSelectTab }) => {
  const tabs: Array<{ id: AgentState['activeTab']; label: string; icon: string }> = [
    { id: 'missions', label: 'Missions', icon: '🎯' },
    { id: 'evolution', label: 'Evolution', icon: '🧬' },
    { id: 'trust', label: 'Trust & Safety', icon: '🛡️' },
    { id: 'coding', label: 'Coding Workspace', icon: '💻' },
    { id: 'runtime', label: 'Runtime Sandbox', icon: '⚙️' },
    { id: 'memory', label: 'Memory & Context', icon: '🧠' },
    { id: 'approvals', label: 'Approvals', icon: '🔔' },
    { id: 'system', label: 'System Health', icon: '📊' },
  ];

  return (
    <div style={{ width: '220px', background: '#0f172a', borderRight: '1px solid #334155', display: 'flex', flexDirection: 'column' }}>
      <div style={{ padding: '16px', fontWeight: 'bold', fontSize: '16px', color: '#38bdf8', borderBottom: '1px solid #334155' }}>
        Agent Control
      </div>
      <div style={{ flex: 1, padding: '8px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => onSelectTab(t.id)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              padding: '10px 12px',
              borderRadius: '6px',
              background: activeTab === t.id ? '#1e293b' : 'transparent',
              color: activeTab === t.id ? '#38bdf8' : '#94a3b8',
              border: 'none',
              cursor: 'pointer',
              textAlign: 'left',
              fontWeight: activeTab === t.id ? 'bold' : 'normal',
            }}
          >
            <span>{t.icon}</span>
            <span style={{ fontSize: '13px' }}>{t.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
};
