import React from 'react';

export const PermissionStatus: React.FC = () => {
  return (
    <div style={{ padding: '12px', background: '#0f172a', borderRadius: '6px' }}>
      <div style={{ fontSize: '12px', fontWeight: 'bold', color: '#38bdf8' }}>LAYER 4 PERMISSION POLICY CEILING</div>
      <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '4px' }}>
        ALLOW | REQUIRE_APPROVAL | DENY Policy Rules Enforced
      </div>
    </div>
  );
};
