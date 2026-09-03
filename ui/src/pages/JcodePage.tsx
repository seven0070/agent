import React, { useEffect, useState } from "react";
import { json } from "../lib/api";
import {
  EmptyState,
  FileTree,
  IssueBanner,
  LoadingState,
  OfflineState,
  PageHeader,
  StatusBadge,
  Timeline,
} from "../components/ui";
import { summarizePayload } from "../lib/format";
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
  const [loading, setLoading] = useState(true);
  const online = health.connection === "online";

  const load = async () => {
    setLoading(true);
    try {
      const [codingWs, listing] = await Promise.all([
        json<CodingWorkspace>("/api/coding/workspace"),
        json<WorkspaceListing>("/api/workspace/files"),
      ]);
      setCoding(codingWs);
      setFiles(listing);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Jcode status unavailable");
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
  }, [online, session.workspaceEpoch]);

  const codingEvents = session.events.filter((event) => /jcode|coding|tool/i.test(event.event_type));
  const test = coding?.last_test_run;
  const testTone = test?.failed ? "failed" : test?.status ?? "idle";

  return (
    <section className="page page--wide page--fill">
      <PageHeader eyebrow="Coding engine" title="Jcode">
        Jcode runs as `coding-engine-v1` through the existing chat pipeline. There is no separate IDE backend.
      </PageHeader>
      {!online ? <OfflineState /> : null}
      <IssueBanner message={error} />
      <div className="split page--fill">
        <div className="stack">
          <article className="panel">
            <h2>Request</h2>
            <form
              className="stack"
              onSubmit={(event) => {
                event.preventDefault();
                const text = draft;
                setDraft("");
                void session.sendPrompt(text);
              }}
            >
              <textarea
                className="textarea"
                rows={4}
                value={draft}
                disabled={!online || session.busy}
                placeholder="Describe a coding outcome…"
                aria-label="Coding goal"
                onChange={(event) => setDraft(event.target.value)}
              />
              <button className="btn btn--primary" type="submit" disabled={!online || session.busy || !draft.trim()}>
                {session.busy ? session.streamHint ?? "Running" : "Run through pipeline"}
              </button>
            </form>
          </article>
          <article className="panel">
            <h2>Last coding workspace status</h2>
            {loading && !coding ? <LoadingState /> : null}
            {coding ? (
              <dl className="meta-list">
                <div>
                  <dt>Status</dt>
                  <dd>
                    <StatusBadge value={coding.status} />
                  </dd>
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
                    <StatusBadge value={testTone} /> passed {test?.passed ?? 0} · failed {test?.failed ?? 0}
                  </dd>
                </div>
              </dl>
            ) : null}
            {coding && coding.changed_files.length > 0 ? (
              <>
                <h2>Changed files</h2>
                <ul className="plain-list">
                  {coding.changed_files.map((file) => (
                    <li key={file} className="mono">
                      {file}
                    </li>
                  ))}
                </ul>
              </>
            ) : null}
          </article>
        </div>
        <div className="stack">
          <article className="panel panel--fill">
            <h2>Workspace files</h2>
            {!files || files.files.length === 0 ? (
              <EmptyState title="No sandbox files yet">Generated programs land in the governed workspace.</EmptyState>
            ) : (
              <FileTree files={files.files} />
            )}
          </article>
          <article className="panel">
            <h2>Pipeline</h2>
            {session.plan ? <StatusBadge value={session.plan.status} /> : null}
            <Timeline
              items={codingEvents.map((event, index) => ({
                id: `${event.event_type}-${index}`,
                title: event.event_type,
                detail: summarizePayload(event.payload),
                time: event.timestamp,
                status: event.event_type,
              }))}
            />
          </article>
        </div>
      </div>
    </section>
  );
};
