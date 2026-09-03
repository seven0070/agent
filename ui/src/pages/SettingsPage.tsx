import React, { useEffect, useState } from "react";
import { json, postJson } from "../lib/api";
import { IssueBanner, LoadingState, MetricList, OfflineState, PageHeader, StatusBadge } from "../components/ui";
import { useHealth } from "../state/HealthContext";
import type { RuntimeSettings } from "../lib/types";

const EDITABLE: Array<{ key: "model_provider" | "model_name" | "local_model_host" | "runtime_timeout_seconds"; label: string }> = [
  { key: "model_provider", label: "Model provider" },
  { key: "model_name", label: "Model name" },
  { key: "local_model_host", label: "Local model host" },
  { key: "runtime_timeout_seconds", label: "Runtime timeout (seconds)" },
];

export const SettingsPage: React.FC = () => {
  const { health, refresh } = useHealth();
  const [settings, setSettings] = useState<RuntimeSettings | null>(null);
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const online = health.connection === "online";

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
    if (!online) {
      setLoading(false);
      return;
    }
    void load();
  }, [online]);

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
      <PageHeader eyebrow="System" title="Settings">
        Only keys accepted by `/api/settings` can be written. Protected boundaries return 403.
      </PageHeader>
      {!online ? <OfflineState /> : null}
      {loading ? <LoadingState /> : null}
      <IssueBanner message={error} />
      {notice ? <div className="banner banner--ok" role="status">{notice}</div> : null}
      {settings ? (
        <div className="stack">
          <article className="panel">
            <h2>Health</h2>
            <MetricList
              items={[
                { label: "Connection", value: health.connection },
                { label: "Version", value: health.version ?? settings.agent_version ?? "unavailable" },
                { label: "Data directory", value: settings.data_dir ?? "unavailable" },
                { label: "Evolution mode", value: settings.evolution_mode ?? "unavailable" },
                {
                  label: "Constitution",
                  value: <StatusBadge value={settings.constitution_locked ? "locked" : "unconfirmed"} />,
                },
              ]}
            />
          </article>
          <article className="panel">
            <h2>Model routing</h2>
            {EDITABLE.map((field) => (
              <label key={field.key} className="field">
                <span>{field.label}</span>
                <input
                  value={draft[field.key] ?? ""}
                  aria-label={field.label}
                  disabled={!online || saving}
                  onChange={(event) => setDraft((prev) => ({ ...prev, [field.key]: event.target.value }))}
                />
              </label>
            ))}
            <button className="btn btn--primary" disabled={saving || !online} onClick={() => void save()}>
              {saving ? "Saving…" : "Save"}
            </button>
          </article>
        </div>
      ) : null}
    </section>
  );
};
