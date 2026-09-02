import React from 'react';
import { EvolutionCandidate } from '../api/types';

export const CandidateCard: React.FC<{ candidate: EvolutionCandidate }> = ({ candidate }) => {
  return (
    <div style={{ padding: '12px', background: '#0f172a', borderRadius: '6px', border: '1px solid #a855f7' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
        <span style={{ fontWeight: 'bold', color: '#f8fafc' }}>{candidate.candidateVersion}</span>
        <span style={{ fontSize: '11px', padding: '2px 6px', borderRadius: '4px', background: '#6b21a8', color: '#fff' }}>
          {candidate.status.toUpperCase()}
        </span>
      </div>
      <div style={{ fontSize: '12px', color: '#94a3b8' }}>Parent: {candidate.currentVersion}</div>
    </div>
  );
};
