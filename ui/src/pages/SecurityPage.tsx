import React, { useEffect, useState } from "react";
import { json } from "../lib/api";
import { EmptyState, ErrorState, LoadingState, StatusBadge } from "../components/ui";
import type { AuditEvent, ConstitutionStatus, RuntimeSettings } from "../lib/types";

export const SecurityPage: React.FC = () => {
  const [constitution, setConstitution] = useState<ConstitutionStatus | null>(null);
  const [settings, setSettings] = useState<RuntimeSettings | null>(null);
  const [audit, setAudit] = useState<AuditEvent[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const [trust, conf, logs] = await Promise.all([
          json<ConstitutionStatus>("/api/trust/constitution"),
          json<RuntimeSettings>("/api/settings"),
          json<AuditEvent[]>("/api/audit/logs?limit=50"),
        ]);
        setConstitution(trust);
        setSettings(conf);
        setAudit(logs);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Security APIs unavailable");
      }
    };
    void load();
  }, []);

  return (
    <section className="page">
      <p className="eyebrow">Governance</p>
      <h1>Security</h1>
      <p className="muted">Constitution, broker permissions, and audit events. Secrets are not requested or displayed.</p>
      {error ? <ErrorState>{error}</ErrorState> : null}
      {!constitution && !error ? <LoadingState /> : null}
      {constitution ? (
        <article className="panel">
          <h2>Constitution</h2>
          <StatusBadge value={constitution.protected ? "protected" : "unconfirmed"} />
          <h2>Boundaries</h2>
          <ul className="plain-list">
            {constitution.protected_boundaries.map((item) => (
              <li key={item} className="mono">
                {item}
              </li>
            ))}
          </ul>
          <h2>Invariants</h2>
          {constitution.invariants.map((item) => (
            <div key={item.name}>
              <strong>{item.name}</strong>
              <div className="muted">{item.description}</div>
            </div>
          ))}
        </article>
      ) : null}
      {settings?.permissions ? (
        <article className="panel">
          <h2>Permissions</h2>
          <ul className="tool-list">
            {Object.entries(settings.permissions).map(([id, level]) => (
              <li key={id}>
                <span className="mono">{id}</span>
                <StatusBadge value={level} />
              </li>
            ))}
          </ul>
        </article>
      ) : null}
      <article className="panel">
        <h2>Audit</h2>
        {!audit || audit.length === 0 ? (
          <EmptyState>No audit events.</EmptyState>
        ) : (
          <ul className="plain-list">
            {audit.map((event, index) => (
              <li key={`${event.timestamp}-${index}`}>
                <div className="mono subtle">{event.timestamp}</div>
                <div>
                  {event.event_type} · {event.action ?? ""} · {event.result ?? ""}
                </div>
              </li>
            ))}
          </ul>
        )}
      </article>
    </section>
  );
};
