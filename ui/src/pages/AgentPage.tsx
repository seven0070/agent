import React, { useEffect, useState } from "react";
import { EmptyState, ErrorState, LoadingState, StatusBadge, Timeline } from "../components/ui";
import { useHealth } from "../state/HealthContext";
import { useSession } from "../state/SessionContext";

export const AgentPage: React.FC = () => {
  const { health } = useHealth();
  const session = useSession();
  const [draft, setDraft] = useState("");
  const online = health.connection === "online";

  useEffect(() => {
    void session.refresh();
  }, [session.refresh]);

  return (
    <section className="page page--wide">
      <p className="eyebrow">Workspace</p>
      <h1>Agent</h1>
      <p className="muted">Natural-language goals run through the local pipeline. Replies and tool activity are streamed from the backend.</p>
      {!online ? <ErrorState>Backend disconnected. Chat is unavailable.</ErrorState> : null}
      {session.error ? <ErrorState>{session.error}</ErrorState> : null}
      <div className="workspace-grid">
        <aside className="panel">
          <div className="row-between">
            <h2>Sessions</h2>
            <button className="btn btn--small" disabled={!online || session.busy} onClick={() => void session.newSession()}>
              New
            </button>
          </div>
          {session.sessions.length === 0 ? (
            <EmptyState>No sessions yet.</EmptyState>
          ) : (
            <ul className="session-list">
              {session.sessions.map((item) => (
                <li key={item.session_id}>
                  <button
                    className={`session-list__item${item.session_id === session.currentId ? " is-active" : ""}`}
                    onClick={() => void session.selectSession(item.session_id)}
                  >
                    <span>{item.title}</span>
                    <span className="mono subtle">{item.session_id}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </aside>
        <div className="panel agent-transcript">
          <h2>Conversation</h2>
          <div className="agent-transcript__log">
            {session.messages.length === 0 ? (
              <EmptyState>No messages in this session.</EmptyState>
            ) : (
              session.messages.map((message) => (
                <article key={message.id} className={`bubble bubble--${message.role}`}>
                  <div className="eyebrow">{message.role}</div>
                  <pre>{message.content}</pre>
                </article>
              ))
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
            <input
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              placeholder={online ? "Describe the outcome you want…" : "Waiting for backend…"}
              disabled={!online || session.busy}
              aria-label="Goal"
            />
            <button type="submit" disabled={!online || session.busy || !draft.trim()}>
              {session.busy ? "Running" : "Run"}
            </button>
          </form>
        </div>
        <aside className="stack">
          <article className="panel">
            <h2>Live execution</h2>
            {session.busy ? <LoadingState label="Executing…" /> : null}
            {session.plan ? (
              <div>
                <div className="mono subtle">{session.plan.plan_id}</div>
                <StatusBadge value={session.plan.status} />
              </div>
            ) : (
              <EmptyState>No plan yet.</EmptyState>
            )}
          </article>
          <article className="panel">
            <h2>Activity</h2>
            <Timeline
              items={session.events.slice(-12).map((event, index) => ({
                id: `${event.event_type}-${index}`,
                title: event.event_type,
                time: event.timestamp,
              }))}
            />
          </article>
        </aside>
      </div>
    </section>
  );
};
