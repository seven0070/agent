import React, { useEffect, useState } from "react";
import { json } from "../lib/api";
import { EmptyState, IssueBanner, LoadingState, OfflineState, PageHeader } from "../components/ui";
import { formatBytes } from "../lib/format";
import { useHealth } from "../state/HealthContext";
import { useSession } from "../state/SessionContext";
import type { WorkspaceListing } from "../lib/types";

export const WorkspacePage: React.FC = () => {
  const { health } = useHealth();
  const { workspaceEpoch } = useSession();
  const [data, setData] = useState<WorkspaceListing | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const online = health.connection === "online";

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
    if (!online) {
      setLoading(false);
      return;
    }
    void load();
  }, [online, workspaceEpoch]);

  return (
    <section className="page">
      <PageHeader
        eyebrow="Sandbox"
        title="Workspace"
        actions={
          <button className="btn" disabled={!online || loading} onClick={() => void load()}>
            Refresh
          </button>
        }
      >
        Governed Agent workspace only. The host filesystem is not exposed.
      </PageHeader>
      {!online ? <OfflineState /> : null}
      {online && loading ? <LoadingState label="Reading workspace listing…" /> : null}
      <IssueBanner message={error} />
      {data ? (
        <article className="panel">
          <h2>Root</h2>
          <div className="mono">{data.workspace_root}</div>
          <p className="muted">
            {data.files.length} file{data.files.length === 1 ? "" : "s"} under the sandbox
            {data.files.length > 0
              ? ` · ${formatBytes(data.files.reduce((sum, file) => sum + file.size_bytes, 0))} total`
              : ""}
            .
          </p>
        </article>
      ) : null}
      {data && data.files.length === 0 ? (
        <EmptyState title="Workspace is empty">Files appear here after governed write or coding operations.</EmptyState>
      ) : null}
    </section>
  );
};
