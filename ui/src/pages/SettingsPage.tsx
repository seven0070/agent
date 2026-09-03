import React, { useEffect, useState } from "react";
import { json } from "../lib/api";
import { useHealth } from "../state/HealthContext";

type ToolRow = {
  tool_id?: string;
  permission?: string;
  description?: string;
};

export const SettingsPage: React.FC = () => {
  const { health } = useHealth();
  const [settings, setSettings] = useState<Record<string, unknown> | null>(null);
  const [tools, setTools] = useState<ToolRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      setLoading(true);
      try {
        const conf = await json<Record<string, unknown>>("/api/settings");
        const toolList = await json<ToolRow[]>("/api/tools");
        if (cancelled) return;
        setSettings(conf);
        setTools(toolList);
        setError(null);
      } catch (err) {
        if (cancelled) return;
        setSettings(null);
        setTools(null);
        setError(err instanceof Error ? err.message : "Settings unavailable");
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    void load();
    return () => {
      cancelled = true;
    };
  }, [health.connection]);

  return (
    <section className="page">
      <p className="eyebrow">Runtime</p>
      <h1>Settings</h1>
      <p className="muted">Read-only values from the local backend. The permission ceiling cannot be raised here.</p>
      {loading ? <p className="muted">Loading settings…</p> : null}
      {error ? <div className="banner banner--danger">{error}</div> : null}
      {!loading && !error && settings ? (
        <div className="stack">
          <article className="panel">
            <h2>Backend</h2>
            <dl className="meta-list">
              <div>
                <dt>Provider</dt>
                <dd>{String(settings.model_provider ?? "unavailable")}</dd>
              </div>
              <div>
                <dt>Model</dt>
                <dd>{String(settings.model_name ?? "unavailable")}</dd>
              </div>
              <div>
                <dt>Data directory</dt>
                <dd>{String(settings.data_dir ?? "unavailable")}</dd>
              </div>
              <div>
                <dt>Agent version</dt>
                <dd>{String(settings.agent_version ?? health.version ?? "unavailable")}</dd>
              </div>
            </dl>
          </article>
          <article className="panel">
            <h2>Registered tools</h2>
            {tools && tools.length > 0 ? (
              <ul className="tool-list">
                {tools.map((tool) => (
                  <li key={String(tool.tool_id)}>
                    <span className="mono">{String(tool.tool_id)}</span>
                    <span>{String(tool.permission ?? "unavailable")}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="muted">No tools reported by the backend.</p>
            )}
          </article>
        </div>
      ) : null}
      {!loading && health.connection === "offline" && !settings ? (
        <p className="muted">Backend disconnected. Settings cannot be loaded.</p>
      ) : null}
    </section>
  );
};
