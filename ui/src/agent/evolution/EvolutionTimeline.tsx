import React, { useEffect, useState } from 'react';

export const EvolutionTimeline: React.FC<{ auditUrl?: string }> = ({ auditUrl }) => {
  const [events, setEvents] = useState<any[]>([]);

  useEffect(() => {
    if (!auditUrl) return;
    fetch(auditUrl)
      .then((res) => res.json())
      .then((data) => setEvents(Array.isArray(data) ? data.slice(0, 8) : []))
      .catch(() => {});
  }, [auditUrl]);

  return (
    <div style={{ padding: '12px', background: '#0f172a', borderRadius: '6px' }}>
      <div style={{ fontSize: '12px', fontWeight: 'bold', color: '#a855f7', marginBottom: '8px' }}>EVOLUTION CONTROL TIMELINE</div>
      <div style={{ fontSize: '11px', color: '#94a3b8' }}>OBSERVE → PROPOSE → CANDIDATE → JCODE → SANDBOX → EVAL → GATE → PROMOTE</div>
      {events.map((event, index) => (
        <div key={`${event.timestamp}-${index}`} style={{ fontSize: '11px', color: '#cbd5e1', marginTop: '4px' }}>
          {event.event_type} — {event.decision}
        </div>
      ))}
    </div>
  );
};
