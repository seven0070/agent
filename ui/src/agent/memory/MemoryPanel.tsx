import React, { useEffect, useState } from 'react';
import { ContextPanel } from './ContextPanel';
import { API_BASE } from '../api/agentApi';

export const MemoryPanel: React.FC = () => {
  const [memoryItems, setMemoryItems] = useState<any[]>([]);

  useEffect(() => {
    fetch(`${API_BASE}/memory/search?query=all`)
      .then((res) => res.json())
      .then((data) => setMemoryItems(data))
      .catch(() => {});
  }, []);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
      <h3 style={{ margin: '0 0 8px 0', color: '#eab308' }}>MEMORY & KNOWLEDGE STORE</h3>
      <ContextPanel />
      <div style={{ padding: '12px', background: '#0f172a', borderRadius: '6px', fontSize: '12px', color: '#cbd5e1' }}>
        Stored Memory Entries: <strong style={{ color: '#38bdf8' }}>{memoryItems.length} entries</strong>
      </div>
    </div>
  );
};
