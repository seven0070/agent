import React from 'react';
import { resolveApproval, rollbackMutation } from '../api/agentApi';

export const PromotionGate: React.FC<{ gate?: any; pending?: any[] }> = ({ gate, pending }) => {
  const decision = gate?.decision || 'IDLE';
  const pendingCards = Array.isArray(pending) ? pending : [];

  return (
    <div style={{ padding: '12px', background: '#0f172a', borderRadius: '6px', border: '1px solid #10b981' }}>
      <div style={{ fontSize: '12px', fontWeight: 'bold', color: '#10b981' }}>PROMOTION GATE — GOVERNANCE</div>
      <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '4px' }}>
        Layer -1 Constitutional Protection Enforced | Decision {decision}
      </div>
      {pendingCards.length === 0 ? (
        <div style={{ fontSize: '11px', color: '#64748b', marginTop: '8px' }}>No evolution promotions awaiting human approval.</div>
      ) : (
        pendingCards.map((card) => (
          <div key={card.approval_id} style={{ marginTop: '8px', fontSize: '12px', color: '#e2e8f0' }}>
            <div>{card.reason || card.resource}</div>
            <div style={{ display: 'flex', gap: '8px', marginTop: '6px' }}>
              <button
                onClick={() => resolveApproval(card.approval_id, true)}
                style={{ background: '#065f46', color: '#ecfdf5', border: 0, borderRadius: 4, padding: '4px 8px' }}
              >
                Approve
              </button>
              <button
                onClick={() => resolveApproval(card.approval_id, false)}
                style={{ background: '#7f1d1d', color: '#fef2f2', border: 0, borderRadius: 4, padding: '4px 8px' }}
              >
                Reject
              </button>
              {card.mutation_id ? (
                <button
                  onClick={() => rollbackMutation(card.mutation_id, 'operator rollback')}
                  style={{ background: '#1e3a5f', color: '#dbeafe', border: 0, borderRadius: 4, padding: '4px 8px' }}
                >
                  Rollback
                </button>
              ) : null}
            </div>
          </div>
        ))
      )}
    </div>
  );
};
