import React, { useEffect, useState } from "react";
import { json } from "../lib/api";
import { ErrorState, LoadingState, UnavailableState } from "../components/ui";
import { useHealth } from "../state/HealthContext";
import type { RuntimeSettings } from "../lib/types";

export const ModelsPage: React.FC = () => {
  const { health } = useHealth();
  const [settings, setSettings] = useState<RuntimeSettings | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        setSettings(await json<RuntimeSettings>("/api/settings"));
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Settings/model config unavailable");
        setSettings(null);
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, []);

  return (
    <section className="page">
      <p className="eyebrow">Intelligence</p>
      <h1>Models</h1>
      <p className="muted">Active model configuration from `/api/settings`. A full model-registry HTTP API is not exposed.</p>
      {loading ? <LoadingState /> : null}
      {error ? <ErrorState>{error}</ErrorState> : null}
      {settings ? (
        <article className="panel">
          <h2>Configured routing</h2>
          <dl className="meta-list">
            <div>
              <dt>Provider</dt>
              <dd>{settings.model_provider ?? "unavailable"}</dd>
            </div>
            <div>
              <dt>Model name</dt>
              <dd>{settings.model_name ?? "unavailable"}</dd>
            </div>
            <div>
              <dt>Local host</dt>
              <dd>{settings.local_model_host ?? "unavailable"}</dd>
            </div>
            <div>
              <dt>Health layer</dt>
              <dd>{health.connection === "online" ? "models layer reported active" : "unavailable"}</dd>
            </div>
          </dl>
        </article>
      ) : null}
      <UnavailableState title="Registry listing NOT EXPOSED">
        ModelSpec entries live inside the process ModelRegistry. There is no `/api/models` endpoint, so additional
        providers, capabilities, and fallbacks are not listed here.
      </UnavailableState>
    </section>
  );
};
