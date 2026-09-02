import React from 'react';
import { EvaluationSummary } from '../api/types';

export const EvaluationResults: React.FC<{ summary?: EvaluationSummary }> = ({ summary }) => {
  return (
    <div style={{ padding: '12px', background: '#0f172a', borderRadius: '6px' }}>
      <div style={{ fontSize: '12px', fontWeight: 'bold', color: '#38bdf8', marginBottom: '8px' }}>EVALUATION BENCHMARK METRICS</div>
      {summary ? (
        <div style={{ fontSize: '12px', color: '#cbd5e1' }}>
          Status: {summary.status.toUpperCase()} | Correctness: {summary.metrics.correctness ?? 'n/a'} | Safety: {summary.metrics.safety ?? 'n/a'}
          {summary.regressions?.length ? ` | Regressions: ${summary.regressions.join(', ')}` : ' | No regressions'}
        </div>
      ) : (
        <div style={{ fontSize: '11px', color: '#64748b' }}>No candidate evaluation has been recorded yet.</div>
      )}
    </div>
  );
};
