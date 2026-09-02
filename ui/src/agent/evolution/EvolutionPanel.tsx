import React, { useEffect, useState } from 'react';
import { EvolutionCandidate } from '../api/types';
import { VersionLineage } from './VersionLineage';
import { CandidateCard } from './CandidateCard';
import { EvaluationResults } from './EvaluationResults';
import { PromotionGate } from './PromotionGate';
import { EvolutionTimeline } from './EvolutionTimeline';
import { API_BASE } from '../api/agentApi';

export const EvolutionPanel: React.FC<{ candidates: EvolutionCandidate[] }> = ({ candidates }) => {
  const [evoStatus, setEvoStatus] = useState<any>(null);

  useEffect(() => {
    fetch(`${API_BASE}/evolution/status`)
      .then((res) => res.json())
      .then((data) => setEvoStatus(data))
      .catch(() => {});
  }, []);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
      <h3 style={{ margin: '0 0 8px 0', color: '#a855f7' }}>EVOLUTION & METAMORPHOSIS DASHBOARD</h3>
      <VersionLineage activeGen={evoStatus?.active_generation || candidates[0]?.currentVersion || 'agent-v1'} />
      <EvolutionTimeline />

      <div style={{ margin: '8px 0', fontWeight: 'bold', fontSize: '13px', color: '#f8fafc' }}>CANDIDATE MUTATIONS (MODE: {evoStatus?.mode || 'SEMI_AUTOMATIC'})</div>
      {candidates.length === 0 ? (
        <div style={{ color: '#94a3b8', fontSize: '13px' }}>No pending candidate mutations.</div>
      ) : (
        candidates.map((c) => <CandidateCard key={c.id} candidate={c} />)
      )}

      <EvaluationResults />
      <PromotionGate />
    </div>
  );
};
