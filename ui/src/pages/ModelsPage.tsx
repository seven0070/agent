import React, { useEffect, useState } from "react";
import { json } from "../lib/api";
import { IssueBanner, LoadingState, MetricList, OfflineState, PageHeader, UnavailableState } from "../components/ui";
import { useHealth } from "../state/HealthContext";
import type { RuntimeSettings } from "../lib/types";

export const ModelsPage: React.FC = () => {
  const { health } = useHealth();
  const [settings, setSettings] = useState<RuntimeSettings | null>(null);
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
  }, [online]);

  return (
    <section className="page">
      <PageHeader eyebrow="Intelligence" title="Models">
        Active model configuration from `/api/settings`. A full model-registry HTTP API is not exposed.
      </PageHeader>
      {!online ? <OfflineState /> : null}
      {loading ? <LoadingState /> : null}
      <IssueBanner message={error} />
      {settings ? (
        <article className="panel">
          <h2>Configured routing</h2>
          <MetricList
            items={[
              { label: "Provider", value: settings.model_provider ?? "unavailable" },
              { label: "Model name", value: settings.model_name ?? "unavailable" },
              { label: "Local host", value: settings.local_model_host ?? "unavailable" },
              {
                label: "Health layer",
                value: health.connection === "online" ? "models layer reported active" : "unavailable",
              },
            ]}
          />
        </article>
      ) : null}
      <UnavailableState title="Registry listing NOT EXPOSED">
        ModelSpec entries live inside the process ModelRegistry. There is no `/api/models` endpoint, so additional
        providers, capabilities, and fallbacks are not listed here.
      </UnavailableState>
    </section>
  );
};
