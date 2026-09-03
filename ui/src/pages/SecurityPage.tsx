import React, { useEffect, useState } from "react";
import { json } from "../lib/api";
import {
  DataTable,
  EmptyState,
  IssueBanner,
  LoadingState,
  OfflineState,
  PageHeader,
  StatusBadge,
} from "../components/ui";
import { formatTime } from "../lib/format";
import { useHealth } from "../state/HealthContext";
import type { AuditEvent, ConstitutionStatus, RuntimeSettings } from "../lib/types";

export const SecurityPage: React.FC = () => {
  const { health } = useHealth();
  const [constitution, setConstitution] = useState<ConstitutionStatus | null>(null);
  const [settings, setSettings] = useState<RuntimeSettings | null>(null);
  const [audit, setAudit] = useState<AuditEvent[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const online = health.connection === "online";

  useEffect(() => {
    if (!online) {
      setLoading(false);
      return;
    }
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
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, [online]);

  return (
    <section className="page">
      <PageHeader eyebrow="Governance" title="Security">
        Constitution, broker permissions, and audit events. Secrets are not requested or displayed.
      </PageHeader>
      {!online ? <OfflineState /> : null}
      <IssueBanner message={error} />
      {loading ? <LoadingState /> : null}
      {constitution ? (
        <article className="panel">
          <div className="row-between">
            <h2>Constitution</h2>
            <StatusBadge value={constitution.protected ? "protected" : "unconfirmed"} />
          </div>
          <p className="muted">
            {constitution.protected
              ? "Protected boundaries are enforced. This UI cannot raise permissions or mutate constitution targets."
              : "Constitution status was not confirmed by the trust endpoint."}
          </p>
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
            <div key={item.name} className="task-card">
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
        <DataTable
          columns={[
            { key: "time", label: "Time", mono: true },
            { key: "type", label: "Event" },
            { key: "action", label: "Action" },
            { key: "result", label: "Result" },
          ]}
          rows={(audit ?? []).map((event, index) => ({
            id: `${event.timestamp}-${index}`,
            time: formatTime(event.timestamp) || event.timestamp,
            type: event.event_type,
            action: event.action ?? "—",
            result: <StatusBadge value={event.result ?? "recorded"} />,
          }))}
          empty={<EmptyState title="No audit events">The audit log is empty.</EmptyState>}
        />
      </article>
    </section>
  );
};
