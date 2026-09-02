/**
 * Agent Command Bar Component.
 */

import React, { useState } from 'react';

interface AgentCommandBarProps {
  onExecuteCommand: (command: string) => void;
}

export const AgentCommandBar: React.FC<AgentCommandBarProps> = ({ onExecuteCommand }) => {
  const [input, setInput] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;
    onExecuteCommand(input.trim());
    setInput('');
  };

  return (
    <form onSubmit={handleSubmit} style={{ display: 'flex', gap: '8px', padding: '12px', background: '#0f172a', borderBottom: '1px solid #334155' }}>
      <input
        type="text"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        placeholder="Issue command to Agent..."
        style={{
          flex: 1,
          padding: '8px 12px',
          borderRadius: '6px',
          border: '1px solid #475569',
          background: '#1e293b',
          color: '#f8fafc',
          fontSize: '13px',
        }}
      />
      <button
        type="submit"
        style={{
          padding: '8px 16px',
          borderRadius: '6px',
          background: '#2563eb',
          color: '#ffffff',
          border: 'none',
          fontWeight: 'bold',
          cursor: 'pointer',
        }}
      >
        Command
      </button>
    </form>
  );
};
