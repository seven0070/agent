import React from 'react';
import { MissionStatus as StatusType } from '../api/types';

export const MissionStatus: React.FC<{ status: StatusType }> = ({ status }) => {
  const getBadgeStyle = () => {
    switch (status) {
      case 'running': return { bg: '#1e3a8a', color: '#60a5fa' };
      case 'completed': return { bg: '#064e3b', color: '#34d399' };
      case 'failed': return { bg: '#7f1d1d', color: '#f87171' };
      case 'waiting_approval': return { bg: '#78350f', color: '#fbbf24' };
      default: return { bg: '#334155', color: '#94a3b8' };
    }
  };

  const style = getBadgeStyle();
  return (
    <span style={{ fontSize: '11px', padding: '2px 8px', borderRadius: '4px', background: style.bg, color: style.color, fontWeight: 'bold' }}>
      {status.toUpperCase()}
    </span>
  );
};
