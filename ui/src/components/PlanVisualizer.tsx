import React from 'react';

export interface PlanTaskItem {
  id: string;
  description: string;
  status: 'PENDING' | 'READY' | 'RUNNING' | 'SUCCEEDED' | 'FAILED' | 'CANCELLED';
  dependencies: string[];
}

interface PlanVisualizerProps {
  planId?: string;
  tasks?: PlanTaskItem[];
}

export const PlanVisualizer: React.FC<PlanVisualizerProps> = ({ planId = 'plan-v1', tasks = [] }) => {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'SUCCEEDED': return '#10b981';
      case 'RUNNING': return '#3b82f6';
      case 'FAILED': return '#ef4444';
      case 'READY': return '#f59e0b';
      default: return '#64748b';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'SUCCEEDED': return '✓';
      case 'RUNNING': return '●';
      case 'FAILED': return '✗';
      case 'READY': return '◉';
      default: return '○';
    }
  };

  return (
    <div style={{ background: '#1e293b', padding: '16px', borderRadius: '8px', border: '1px solid #334155' }}>
      <h3 style={{ margin: '0 0 12px 0', color: '#38bdf8' }}>PLAN VISUALIZER [{planId}]</h3>
      {tasks.length === 0 ? (
        <div style={{ color: '#94a3b8', fontSize: '13px' }}>No active plan DAG. Command the Sovereign Agent to generate a goal plan.</div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {tasks.map((t) => (
            <div
              key={t.id}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                padding: '8px 12px',
                borderRadius: '6px',
                background: '#0f172a',
                borderLeft: `4px solid ${getStatusColor(t.status)}`,
              }}
            >
              <span style={{ color: getStatusColor(t.status), fontWeight: 'bold' }}>{getStatusIcon(t.status)}</span>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 'bold', fontSize: '13px', color: '#f8fafc' }}>{t.id}: {t.description}</div>
                {t.dependencies.length > 0 && (
                  <div style={{ fontSize: '11px', color: '#64748b' }}>Deps: {t.dependencies.join(', ')}</div>
                )}
              </div>
              <span style={{ fontSize: '11px', color: getStatusColor(t.status), fontWeight: 'bold' }}>{t.status}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
