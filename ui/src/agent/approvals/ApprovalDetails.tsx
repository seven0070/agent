import React from 'react';
import { ApprovalRequest } from '../api/types';

export const ApprovalDetails: React.FC<{ approval: ApprovalRequest; onResolve: (id: string, approved: boolean) => void }> = ({ approval, onResolve }) => {
  return (
    <div style={{ padding: '12px', background: '#0f172a', borderRadius: '6px', border: '1px solid #f59e0b' }}>
      <div style={{ fontWeight: 'bold', color: '#f8fafc' }}>{approval.title}</div>
      <div style={{ fontSize: '12px', color: '#94a3b8', margin: '4px 0' }}>{approval.description}</div>
      <div style={{ display: 'flex', gap: '8px', marginTop: '8px' }}>
        <button onClick={() => onResolve(approval.id, true)} style={{ flex: 1, padding: '4px', background: '#10b981', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>Approve</button>
        <button onClick={() => onResolve(approval.id, false)} style={{ flex: 1, padding: '4px', background: '#ef4444', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>Reject</button>
      </div>
    </div>
  );
};
