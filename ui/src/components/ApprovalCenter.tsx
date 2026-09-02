import React, { useEffect, useState } from 'react';
import { fetchApprovals, resolveApproval, ApprovalRequest } from '../services/api';

export const ApprovalCenter: React.FC = () => {
  const [approvals, setApprovals] = useState<ApprovalRequest[]>([]);

  const loadApprovals = async () => {
    try {
      const data = await fetchApprovals();
      setApprovals(data);
    } catch {
      // API error fallback
    }
  };

  useEffect(() => {
    loadApprovals();
  }, []);

  const handleResolve = async (id: string, approved: boolean) => {
    await resolveApproval(id, approved);
    loadApprovals();
  };

  return (
    <div style={{ background: '#1e293b', padding: '16px', borderRadius: '8px', border: '1px solid #334155' }}>
      <h3 style={{ margin: '0 0 12px 0', color: '#f59e0b' }}>HUMAN APPROVAL CENTER</h3>
      {approvals.length === 0 ? (
        <div style={{ color: '#94a3b8', fontSize: '13px' }}>No pending approval requests.</div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {approvals.map((a) => (
            <div
              key={a.approval_id}
              style={{
                padding: '12px',
                borderRadius: '6px',
                background: '#0f172a',
                border: '1px solid #f59e0b',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span style={{ fontWeight: 'bold', color: '#f8fafc' }}>{a.action}</span>
                <span style={{ fontSize: '11px', padding: '2px 6px', borderRadius: '4px', background: '#d97706', color: '#fff' }}>
                  Risk: {a.risk_level}
                </span>
              </div>
              <div style={{ fontSize: '12px', color: '#94a3b8', marginBottom: '4px' }}>Layer: {a.source_layer}</div>
              <div style={{ fontSize: '12px', color: '#cbd5e1', marginBottom: '8px' }}>Reason: {a.reason}</div>
              <div style={{ fontSize: '11px', color: '#64748b', marginBottom: '12px' }}>Resource: {a.resource}</div>

              <div style={{ display: 'flex', gap: '8px' }}>
                <button
                  onClick={() => handleResolve(a.approval_id, true)}
                  style={{ flex: 1, padding: '6px', borderRadius: '4px', background: '#10b981', color: '#fff', border: 'none', cursor: 'pointer' }}
                >
                  Approve
                </button>
                <button
                  onClick={() => handleResolve(a.approval_id, false)}
                  style={{ flex: 1, padding: '6px', borderRadius: '4px', background: '#ef4444', color: '#fff', border: 'none', cursor: 'pointer' }}
                >
                  Reject
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
