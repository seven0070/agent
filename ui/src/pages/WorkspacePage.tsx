import React, { useEffect, useState } from "react";
import { json } from "../lib/api";
import { EmptyState, ErrorState, LoadingState } from "../components/ui";
import type { WorkspaceListing } from "../lib/types";

export const WorkspacePage: React.FC = () => {
  const [data, setData] = useState<WorkspaceListing | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const listing = await json<WorkspaceListing>("/api/workspace/files");
      setData(listing);
      setError(null);
    } catch (err) {
      setData(null);
      setError(err instanceof Error ? err.message : "Workspace listing unavailable");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  return (
    <section className="page">
      <p className="eyebrow">Sandbox</p>
      <h1>Workspace</h1>
      <p className="muted">Governed Agent workspace only. The host filesystem is not exposed.</p>
      <button className="btn" onClick={() => void load()}>Refresh</button>
      {loading ? <LoadingState /> : null}
      {error ? <ErrorState>{error}</ErrorState> : null}
      {data ? (
        <article className="panel">
          <h2>Root</h2>
          <div className="mono">{data.workspace_root}</div>
          <p className="muted">{data.files.length} file{data.files.length === 1 ? "" : "s"} under the sandbox.</p>
        </article>
      ) : null}
      {data && data.files.length === 0 ? <EmptyState>Workspace is empty.</EmptyState> : null}
    </section>
  );
};
