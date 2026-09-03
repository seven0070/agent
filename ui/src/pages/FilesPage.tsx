import React, { useEffect, useMemo, useState } from "react";
import { json } from "../lib/api";
import {
  EmptyState,
  FileTree,
  IssueBanner,
  LoadingState,
  OfflineState,
  PageHeader,
  UnavailableState,
} from "../components/ui";
import { formatBytes, formatTime } from "../lib/format";
import { useHealth } from "../state/HealthContext";
import { useSession } from "../state/SessionContext";
import type { WorkspaceFile, WorkspaceListing } from "../lib/types";

export const FilesPage: React.FC = () => {
  const { health } = useHealth();
  const { workspaceEpoch } = useSession();
  const [data, setData] = useState<WorkspaceListing | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
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
      setError(err instanceof Error ? err.message : "File listing unavailable");
      setData(null);
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

  const selected: WorkspaceFile | null = useMemo(
    () => data?.files.find((file) => file.id === selectedId) ?? null,
    [data, selectedId],
  );

  return (
    <section className="page page--wide page--fill">
      <PageHeader
        eyebrow="Sandbox"
        title="Files"
        actions={
          <button className="btn" disabled={!online || loading} onClick={() => void load()}>
            Refresh
          </button>
        }
      >
        Workspace-relative files from `/api/workspace/files`. There is no unrestricted disk browser.
      </PageHeader>
      {!online ? <OfflineState /> : null}
      <IssueBanner message={error} />
      <div className="split page--fill">
        <article className="panel panel--fill">
          <h2>Tree</h2>
          {loading ? <LoadingState label="Listing sandbox files…" /> : null}
          {!loading && (!data || data.files.length === 0) ? (
            <EmptyState title="No files in the sandbox">Run a goal that writes a file, then refresh.</EmptyState>
          ) : null}
          {data && data.files.length > 0 ? (
            <FileTree files={data.files} selectedId={selectedId} onSelect={setSelectedId} />
          ) : null}
        </article>
        <article className="panel panel--fill">
          <h2>Metadata</h2>
          {!selected ? (
            <EmptyState title="Select a file">Choose a path to inspect name, size, and modified time.</EmptyState>
          ) : (
            <dl className="meta-list">
              <div>
                <dt>Name</dt>
                <dd>{selected.name}</dd>
              </div>
              <div>
                <dt>Path</dt>
                <dd>{selected.path}</dd>
              </div>
              <div>
                <dt>Size</dt>
                <dd>{formatBytes(selected.size_bytes)}</dd>
              </div>
              <div>
                <dt>Modified</dt>
                <dd>{formatTime(selected.modified_at)}</dd>
              </div>
            </dl>
          )}
          <UnavailableState title="Content preview NOT EXPOSED">
            The backend lists workspace files and metadata. It does not expose a raw file-read HTTP endpoint. Use the
            Agent page to request a governed `read_file-v1` operation.
          </UnavailableState>
        </article>
      </div>
    </section>
  );
};
