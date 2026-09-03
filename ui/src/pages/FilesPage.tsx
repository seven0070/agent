import React, { useEffect, useState } from "react";
import { json } from "../lib/api";
import { EmptyState, ErrorState, LoadingState, UnavailableState } from "../components/ui";
import type { WorkspaceFile, WorkspaceListing } from "../lib/types";

export const FilesPage: React.FC = () => {
  const [data, setData] = useState<WorkspaceListing | null>(null);
  const [selected, setSelected] = useState<WorkspaceFile | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

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
    void load();
  }, []);

  return (
    <section className="page page--wide">
      <p className="eyebrow">Sandbox</p>
      <h1>Files</h1>
      <p className="muted">Workspace-relative files from `/api/workspace/files`. There is no unrestricted disk browser.</p>
      <button className="btn" onClick={() => void load()}>Refresh</button>
      {loading ? <LoadingState /> : null}
      {error ? <ErrorState>{error}</ErrorState> : null}
      <div className="split">
        <article className="panel">
          <h2>Tree</h2>
          {!data || data.files.length === 0 ? (
            <EmptyState>No files in the sandbox.</EmptyState>
          ) : (
            <ul className="plain-list">
              {data.files.map((file) => (
                <li key={file.id}>
                  <button className="linkish mono" onClick={() => setSelected(file)}>
                    {file.path}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </article>
        <article className="panel">
          <h2>Metadata</h2>
          {!selected ? (
            <EmptyState>Select a file.</EmptyState>
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
                <dd>{selected.size_bytes} bytes</dd>
              </div>
              <div>
                <dt>Modified</dt>
                <dd>{selected.modified_at}</dd>
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
