import React, { useEffect, useState } from "react";
import { json, postJson } from "../lib/api";
import { ErrorState, LoadingState, StatusBadge } from "../components/ui";
import { useHealth } from "../state/HealthContext";
import type { RuntimeSettings } from "../lib/types";

const EDITABLE = ["model_provider", "model_name", "local_model_host", "runtime_timeout_seconds"] as const;

export const SettingsPage: React.FC = () => {
  const { health, refresh } = useHealth();
  const [settings, setSettings] = useState<RuntimeSettings | null>(null);
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const conf = await json<RuntimeSettings>("/api/settings");
      setSettings(conf);
      setDraft({
        model_provider: String(conf.model_provider ?? ""),
        model_name: String(conf.model_name ?? ""),
        local_model_host: String(conf.local_model_host ?? ""),
        runtime_timeout_seconds: String(conf.runtime_timeout_seconds ?? ""),
      });
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Settings unavailable");
      setSettings(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const save = async () => {
    setSaving(true);
    setNotice(null);
    try {
      const body: Record<string, string | number> = {
        model_provider: draft.model_provider ?? "",
        model_name: draft.model_name ?? "",
        local_model_host: draft.local_model_host ?? "",
        runtime_timeout_seconds: Number(draft.runtime_timeout_seconds),
      };
      const saved = await postJson<RuntimeSettings>("/api/settings", body);
      setSettings(saved);
      setNotice("Saved allowed settings. Constitution and permission ceiling remain locked.");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="page">
      <p className="eyebrow">System</p>
      <h1>Settings</h1>
      <p className="muted">Only keys accepted by `/api/settings` can be written. Protected boundaries return 403.</p>
      {loading ? <LoadingState /> : null}
      {error ? <ErrorState>{error}</ErrorState> : null}
      {notice ? <div className="banner">{notice}</div> : null}
      {settings ? (
        <div className="stack">
          <article className="panel">
            <h2>Health</h2>
            <dl className="meta-list">
              <div>
                <dt>Connection</dt>
                <dd>{health.connection}</dd>
              </div>
              <div>
                <dt>Version</dt>
                <dd>{health.version ?? settings.agent_version ?? "unavailable"}</dd>
              </div>
              <div>
                <dt>Data directory</dt>
                <dd>{settings.data_dir ?? "unavailable"}</dd>
              </div>
              <div>
                <dt>Evolution mode</dt>
                <dd>{settings.evolution_mode ?? "unavailable"}</dd>
              </div>
              <div>
                <dt>Constitution</dt>
                <dd>
                  <StatusBadge value={settings.constitution_locked ? "locked" : "unconfirmed"} />
                </dd>
              </div>
            </dl>
          </article>
          <article className="panel">
            <h2>Editable</h2>
            {EDITABLE.map((key) => (
              <label key={key} className="field">
                <span>{key}</span>
                <input
                  value={draft[key] ?? ""}
                  onChange={(event) => setDraft((prev) => ({ ...prev, [key]: event.target.value }))}
                />
              </label>
            ))}
            <button className="btn" disabled={saving || health.connection !== "online"} onClick={() => void save()}>
              {saving ? "Saving…" : "Save"}
            </button>
          </article>
        </div>
      ) : null}
    </section>
  );
};
