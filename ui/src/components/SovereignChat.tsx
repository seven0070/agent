import React, { useState } from 'react';
import { API_BASE } from '../services/api';

interface SovereignChatProps {
  sessionId: string;
}

export const SovereignChat: React.FC<SovereignChatProps> = ({ sessionId }) => {
  const [prompt, setPrompt] = useState('');
  const [messages, setMessages] = useState<Array<{ role: string; content: string }>>([
    { role: 'assistant', content: 'Sovereign Agent OS online. Systems nominal across Layers 0–9.' },
  ]);
  const [isProcessing, setIsProcessing] = useState(false);

  const handleSendMessage = async () => {
    if (!prompt.trim() || isProcessing) return;

    const userPrompt = prompt;
    setPrompt('');
    setMessages((prev) => [...prev, { role: 'user', content: userPrompt }]);
    setIsProcessing(true);

    try {
      const response = await fetch(`${API_BASE}/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, prompt: userPrompt }),
      });

      if (!response.ok) {
        throw new Error(`Server returned HTTP ${response.status}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (reader) {
        let assistantContent = '';
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          const chunk = decoder.decode(value);
          const lines = chunk.split('\n');

          for (const line of lines) {
            if (line.startsWith('data:')) {
              try {
                const frame = JSON.parse(line.replace('data:', '').trim());
                if (frame.event_type === 'MESSAGE_DELTA') {
                  assistantContent = frame.payload.delta;
                } else if (frame.event_type === 'MESSAGE_COMPLETED') {
                  assistantContent = frame.payload.content;
                }
              } catch {
                // Parse fallback
              }
            }
          }
        }

        setMessages((prev) => [
          ...prev,
          { role: 'assistant', content: assistantContent || 'Task completed cleanly.' },
        ]);
      }
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: `[ERROR]: ${err.message}` },
      ]);
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', padding: '16px' }}>
      <div style={{ flex: 1, overflowY: 'auto', marginBottom: '16px' }}>
        {messages.map((m, idx) => (
          <div
            key={idx}
            style={{
              marginBottom: '12px',
              padding: '12px',
              borderRadius: '8px',
              background: m.role === 'user' ? '#1e293b' : '#334155',
              borderLeft: m.role === 'user' ? '4px solid #3b82f6' : '4px solid #10b981',
            }}
          >
            <strong>{m.role === 'user' ? 'Operator' : 'Sovereign Agent'}:</strong>
            <p style={{ margin: '4px 0 0 0', whiteSpace: 'pre-wrap' }}>{m.content}</p>
          </div>
        ))}
      </div>

      <div style={{ display: 'flex', gap: '8px' }}>
        <input
          type="text"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
          placeholder="Command Sovereign Agent..."
          disabled={isProcessing}
          style={{
            flex: 1,
            padding: '12px',
            borderRadius: '6px',
            border: '1px solid #475569',
            background: '#1e293b',
            color: '#f8fafc',
          }}
        />
        <button
          onClick={handleSendMessage}
          disabled={isProcessing}
          style={{
            padding: '12px 24px',
            borderRadius: '6px',
            background: isProcessing ? '#64748b' : '#2563eb',
            color: '#ffffff',
            border: 'none',
            cursor: isProcessing ? 'not-allowed' : 'pointer',
          }}
        >
          {isProcessing ? 'Processing...' : 'Send'}
        </button>
      </div>
    </div>
  );
};
