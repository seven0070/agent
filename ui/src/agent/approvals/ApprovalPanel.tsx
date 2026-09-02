import React from 'react';
import { ApprovalRequest } from '../api/types';
import { ApprovalDetails } from './ApprovalDetails';

export const ApprovalPanel: React.FC<{ approvals: ApprovalRequest[]; onResolve: (id: string, approved: boolean) => void }> = ({ approvals, onResolve }) => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
      <h3 style={{ margin: '0 0 8px 0', color: '#f59e0b' }}>HUMAN APPROVAL CENTER</h3>
      {approvals.length === 0 ? (
        <div style={{ color: '#94a3b8', fontSize: '13px' }}>No pending approval requests.</div>
      ) : (
        approvals.map((a) => <ApprovalDetails key={a.id} approval={a} onResolve={onResolve} />)
      )}
    </div>
  );
};
