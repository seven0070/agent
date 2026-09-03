import React, { useEffect, useState } from "react";
import { json } from "../lib/api";
import { EmptyState, ErrorState, LoadingState, StatusBadge, Timeline } from "../components/ui";
import { useHealth } from "../state/HealthContext";
import { useSession } from "../state/SessionContext";
import type { CodingWorkspace, WorkspaceListing } from "../lib/types";

export const JcodePage: React.FC = () => {
  const { health } = useHealth();
  const session = useSession();
  const [draft, setDraft] = useState("");
  const [coding, setCoding] = useState<CodingWorkspace | null>(null);
  const [files, setFiles] = useState<WorkspaceListing | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    try {
      setCoding(await json<CodingWorkspace>("/api/coding/workspace"));
      setFiles(await json<WorkspaceListing>("/api/workspace/files"));
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Jcode status unavailable");
    }
  };

  useEffect(() => {
    void load();
    void session.refresh();
  }, [session.refresh]);

  const online = health.connection === "online";
  const codingEvents = session.events.filter((event) =>
    /jcode|coding|tool/i.test(event.event_type),
  );

  return (
    <section className="page page--wide">
      <p className="eyebrow">Coding engine</p>
      <h1>Jcode</h1>
      <p className="muted">
        Jcode runs as `coding-engine-v1` through the existing chat pipeline. There is no separate IDE backend.
      </p>
      {error ? <ErrorState>{error}</ErrorState> : null}
      <div className="split">
        <div className="stack">
          <article className="panel">
            <h2>Request</h2>
            <form
              className="stack"
              onSubmit={(event) => {
                event.preventDefault();
                const text = draft;
                setDraft("");
                void session.sendPrompt(text).then(() => void load());
              }}
            >
              <textarea
                className="textarea"
                rows={4}
                value={draft}
                disabled={!online || session.busy}
                placeholder="Describe a coding outcome…"
                onChange={(event) => setDraft(event.target.value)}
              />
              <button className="btn" type="submit" disabled={!online || session.busy || !draft.trim()}>
                {session.busy ? "Running" : "Run through pipeline"}
              </button>
            </form>
          </article>
          <article className="panel">
            <h2>Last coding workspace status</h2>
            {coding ? (
              <dl className="meta-list">
                <div>
                  <dt>Status</dt>
                  <dd>{coding.status}</dd>
                </div>
                <div>
                  <dt>Active task</dt>
                  <dd>{coding.active_task ?? "none"}</dd>
                </div>
                <div>
                  <dt>Root</dt>
                  <dd>{coding.workspace_root}</dd>
                </div>
                <div>
                  <dt>Last test run</dt>
                  <dd>
                    {coding.last_test_run.status} · passed {coding.last_test_run.passed} · failed{" "}
                    {coding.last_test_run.failed}
                  </dd>
                </div>
              </dl>
            ) : (
              <LoadingState />
            )}
            {coding && coding.changed_files.length > 0 ? (
              <ul className="plain-list">
                {coding.changed_files.map((file) => (
                  <li key={file} className="mono">
                    {file}
                  </li>
                ))}
              </ul>
            ) : null}
          </article>
        </div>
        <div className="stack">
          <article className="panel">
            <h2>Workspace files</h2>
            {!files || files.files.length === 0 ? (
              <EmptyState>No sandbox files yet.</EmptyState>
            ) : (
              <ul className="plain-list">
                {files.files.map((file) => (
                  <li key={file.id} className="mono">
                    {file.path}
                  </li>
                ))}
              </ul>
            )}
          </article>
          <article className="panel">
            <h2>Pipeline</h2>
            {session.plan ? <StatusBadge value={session.plan.status} /> : null}
            <Timeline
              items={codingEvents.map((event, index) => ({
                id: `${event.event_type}-${index}`,
                title: event.event_type,
                time: event.timestamp,
              }))}
            />
          </article>
        </div>
      </div>
    </section>
  );
};
