import React from "react";
import { StatusIndicator } from "../components/StatusIndicator";
import { displayValue } from "../lib/health";
import { useHealth } from "../state/HealthContext";

export const AgentPage: React.FC = () => {
  const { health } = useHealth();

  return (
    <section className="page">
      <p className="eyebrow">Desktop</p>
      <h1>Agent</h1>
      <p className="muted">
        This is the desktop shell for the local Agent backend. The Agent Workspace will be implemented in the next
        GUI phase.
      </p>
      {health.connection === "loading" ? <p className="muted">Connecting to the local backend…</p> : null}
      {health.connection === "offline" ? (
        <div className="banner banner--danger">
          Backend disconnected. {health.error ?? "Health endpoint is unreachable."}
        </div>
      ) : null}
      {health.connection === "online" ? (
        <article className="panel">
          <h2>Backend</h2>
          <div className="landing-status">
            <StatusIndicator state={health.connection} label="Backend Online" />
          </div>
          <dl className="meta-list">
            <div>
              <dt>Status</dt>
              <dd>{displayValue(health.backendStatus)}</dd>
            </div>
            <div>
              <dt>Version</dt>
              <dd>{displayValue(health.version)}</dd>
            </div>
            <div>
              <dt>Generation</dt>
              <dd>{displayValue(health.generation)}</dd>
            </div>
          </dl>
        </article>
      ) : null}
    </section>
  );
};
