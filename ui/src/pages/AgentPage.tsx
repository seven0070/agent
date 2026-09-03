import React, { useEffect, useRef, useState } from "react";
import {
  EmptyState,
  IssueBanner,
  LoadingState,
  OfflineState,
  PageHeader,
  StatusBadge,
  Timeline,
} from "../components/ui";
import { formatTime, shortId, summarizePayload } from "../lib/format";
import { useHealth } from "../state/HealthContext";
import { useSession } from "../state/SessionContext";

export const AgentPage: React.FC = () => {
  const { health } = useHealth();
  const session = useSession();
  const [draft, setDraft] = useState("");
  const logRef = useRef<HTMLDivElement>(null);
  const online = health.connection === "online";

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight });
  }, [session.messages, session.busy, session.events.length]);

  const onComposerKey = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      const text = draft;
      if (!text.trim() || !online || session.busy) return;
      setDraft("");
      void session.sendPrompt(text);
    }
  };

  return (
    <section className="page page--wide page--fill">
      <PageHeader
        eyebrow="Workspace"
        title="Agent"
        actions={
          session.currentId ? (
            <button className="btn btn--small btn--ghost" disabled={!online || session.busy} onClick={() => void session.deleteCurrent()}>
              Delete session
            </button>
          ) : null
        }
      >
        Natural-language goals run through the local pipeline. Replies and tool activity are streamed from the backend.
      </PageHeader>
      {!online ? <OfflineState>Backend disconnected. Chat is unavailable.</OfflineState> : null}
      <IssueBanner message={session.error} />
      <div className="workspace-grid">
        <aside className="panel panel--fill">
          <div className="row-between">
            <h2>Sessions</h2>
            <button className="btn btn--small" disabled={!online || session.busy} onClick={() => void session.newSession()}>
              New
            </button>
          </div>
          {session.sessions.length === 0 ? (
            <EmptyState title="No sessions">Create a session or send a goal to start.</EmptyState>
          ) : (
            <ul className="session-list">
              {session.sessions.map((item) => (
                <li key={item.session_id}>
                  <button
                    type="button"
                    className={`session-list__item${item.session_id === session.currentId ? " is-active" : ""}`}
                    aria-current={item.session_id === session.currentId ? "true" : undefined}
                    onClick={() => void session.selectSession(item.session_id)}
                  >
                    <span>{item.title || "Untitled"}</span>
                    <span className="mono subtle">
                      {shortId(item.session_id)} · {item.message_count} msg
                    </span>
                    <span className="subtle">{formatTime(item.updated_at)}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </aside>
        <div className="panel panel--fill agent-transcript">
          <h2>Conversation</h2>
          <div className="agent-transcript__log" ref={logRef} aria-live="polite">
            {session.messages.length === 0 && !session.busy ? (
              <EmptyState title="Empty conversation">Describe an outcome. The pipeline streams plan, tools, and the result here.</EmptyState>
            ) : (
              session.messages.map((message) => {
                const streaming = session.busy && message === session.messages[session.messages.length - 1] && message.role !== "user";
                return (
                  <article
                    key={message.id}
                    className={`bubble bubble--${message.role}${streaming ? " bubble--stream" : ""}`}
                  >
                    <div className="eyebrow">{message.role}</div>
                    <pre>
                      {message.content || (streaming ? session.streamHint ?? "Working…" : "")}
                      {streaming ? <span className="stream-caret" aria-hidden="true" /> : null}
                    </pre>
                  </article>
                );
              })
            )}
          </div>
          <form
            className="composer"
            onSubmit={(event) => {
              event.preventDefault();
              const text = draft;
              setDraft("");
              void session.sendPrompt(text);
            }}
          >
            <textarea
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              onKeyDown={onComposerKey}
              placeholder={online ? "Describe the outcome you want… (Enter to run, Shift+Enter for a new line)" : "Waiting for backend…"}
              disabled={!online || session.busy}
              aria-label="Goal"
              rows={2}
            />
            <button type="submit" disabled={!online || session.busy || !draft.trim()}>
              {session.busy ? "Running" : "Run"}
            </button>
          </form>
        </div>
        <aside className="stack">
          <article className="panel">
            <h2>Live execution</h2>
            {session.busy ? <LoadingState label={session.streamHint ?? "Executing…"} /> : null}
            {session.plan ? (
              <div className="stack">
                <div className="row-between">
                  <span className="mono subtle">{shortId(session.plan.plan_id)}</span>
                  <StatusBadge value={session.plan.status} />
                </div>
                {session.plan.goal ? <p className="muted">{session.plan.goal}</p> : null}
                <p className="subtle">{session.plan.tasks.length} task{session.plan.tasks.length === 1 ? "" : "s"}</p>
              </div>
            ) : (
              <EmptyState title="No plan yet">A plan appears after the pipeline classifies a goal that needs tools.</EmptyState>
            )}
          </article>
          <article className="panel panel--fill">
            <h2>Activity</h2>
            <div className="scroll-y">
              <Timeline
                items={session.events.slice(-12).map((event, index) => ({
                  id: `${event.event_type}-${event.timestamp ?? index}`,
                  title: event.event_type,
                  detail: summarizePayload(event.payload),
                  time: event.timestamp,
                  status: asEventStatus(event.event_type),
                }))}
              />
            </div>
          </article>
        </aside>
      </div>
    </section>
  );
};

function asEventStatus(eventType: string): string {
  const key = eventType.toLowerCase();
  if (key.includes("fail") || key.includes("error")) return "failed";
  if (key.includes("completed") || key.includes("success")) return "completed";
  if (key.includes("start") || key.includes("created") || key.includes("executed")) return "running";
  return eventType;
}
