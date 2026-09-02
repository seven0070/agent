import React from 'react';
import { ConstitutionStatus } from '../api/types';

export const ConstitutionPanel: React.FC<{ status: ConstitutionStatus | null }> = ({ status }) => {
  return (
    <div style={{ padding: '12px', background: '#0f172a', borderRadius: '6px', border: '1px solid #10b981' }}>
      <div style={{ fontSize: '13px', fontWeight: 'bold', color: '#10b981', marginBottom: '8px' }}>
        LAYER -1 IMMUTABLE CONSTITUTIONAL BOUNDARIES {status?.protected ? '(ACTIVE)' : ''}
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '12px', color: '#cbd5e1' }}>
        <div>Identity: ● Protected</div>
        <div>Core Objectives: ● Protected</div>
        <div>Permission Ceiling: ● Protected</div>
        <div>Credential Boundary: ● Protected</div>
        <div>Audit Integrity: ● Protected</div>
        <div>Rollback Authority: ● Protected</div>
      </div>
    </div>
  );
};
