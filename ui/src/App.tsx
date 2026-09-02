import React, { useEffect, useState } from 'react';
import { fetchSessions, createSession, Session } from './services/api';
import { SovereignChat } from './components/SovereignChat';
import { SessionList } from './components/SessionList';
import { PlanVisualizer } from './components/PlanVisualizer';
import { ApprovalCenter } from './components/ApprovalCenter';
import { EvolutionDashboard } from './components/EvolutionDashboard';
import { JcodeWorkspace } from './components/JcodeWorkspace';
import { SystemStatus } from './components/SystemStatus';
import { AuditLogViewer } from './components/AuditLogViewer';

export const App: React.FC = () => {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string>('sess-main');
  const [activeTab, setActiveTab] = useState<'chat' | 'evolution' | 'jcode' | 'audit'>('chat');

  const loadSessions = async () => {
    try {
      const list = await fetchSessions();
      setSessions(list);
      if (list.length > 0 && activeSessionId === 'sess-main') {
        setActiveSessionId(list[0].session_id);
      }
    } catch {
      // API offline fallback
    }
  };

  useEffect(() => {
    loadSessions();
  }, []);

  const handleCreateSession = async () => {
    const newSess = await createSession();
    setSessions((prev) => [newSess, ...prev]);
    setActiveSessionId(newSess.session_id);
  };

  return (
    <div style={{ display: 'flex', height: '100vh', width: '100vw', background: '#0f172a', color: '#f8fafc' }}>
      <SessionList
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelectSession={setActiveSessionId}
        onCreateSession={handleCreateSession}
      />

      <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        {/* Navigation Bar */}
        <div style={{ display: 'flex', gap: '16px', padding: '12px 24px', background: '#1e293b', borderBottom: '1px solid #334155' }}>
          <button
            onClick={() => setActiveTab('chat')}
            style={{ padding: '8px 16px', borderRadius: '4px', background: activeTab === 'chat' ? '#2563eb' : 'transparent', color: '#fff', border: 'none', cursor: 'pointer' }}
          >
            Sovereign Chat
          </button>
          <button
            onClick={() => setActiveTab('evolution')}
            style={{ padding: '8px 16px', borderRadius: '4px', background: activeTab === 'evolution' ? '#2563eb' : 'transparent', color: '#fff', border: 'none', cursor: 'pointer' }}
          >
            Evolution Dashboard
          </button>
          <button
            onClick={() => setActiveTab('jcode')}
            style={{ padding: '8px 16px', borderRadius: '4px', background: activeTab === 'jcode' ? '#2563eb' : 'transparent', color: '#fff', border: 'none', cursor: 'pointer' }}
          >
            Jcode Workspace
          </button>
          <button
            onClick={() => setActiveTab('audit')}
            style={{ padding: '8px 16px', borderRadius: '4px', background: activeTab === 'audit' ? '#2563eb' : 'transparent', color: '#fff', border: 'none', cursor: 'pointer' }}
          >
            Audit Trail
          </button>
        </div>

        {/* Main Content Pane */}
        <div style={{ flex: 1, display: 'grid', gridTemplateColumns: '2fr 1fr', padding: '16px', gap: '16px', overflow: 'hidden' }}>
          <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
            {activeTab === 'chat' && <SovereignChat sessionId={activeSessionId} />}
            {activeTab === 'evolution' && <EvolutionDashboard />}
            {activeTab === 'jcode' && <JcodeWorkspace />}
            {activeTab === 'audit' && <AuditLogViewer />}
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', overflowY: 'auto' }}>
            <SystemStatus />
            <PlanVisualizer />
            <ApprovalCenter />
          </div>
        </div>
      </div>
    </div>
  );
};
