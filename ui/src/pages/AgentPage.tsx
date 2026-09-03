import React, { useState } from "react";
import { json, streamGoal } from "../lib/api";
import { useHealth } from "../state/HealthContext";

type Message = { id: string; role: "user" | "agent"; content: string };
type EventFrame = { event_type: string; payload?: Record<string, unknown> };

export const AgentPage: React.FC = () => {
  const { health } = useHealth();
  const [goal, setGoal] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [events, setEvents] = useState<EventFrame[]>([]);
  const [plan, setPlan] = useState<Record<string, unknown> | null>(null);
  const online = health.connection === "online";

  const submit = async () => {
    const prompt = goal.trim();
    if (!prompt || busy || !online) return;
    setBusy(true);
    setError(null);
    try {
      let sid = sessionId;
      if (!sid) {
        const session = await json<{ session_id: string }>("/api/sessions", {
          method: "POST",
          body: JSON.stringify({ title: prompt.slice(0, 48) }),
        });
        sid = session.session_id;
        setSessionId(sid);
      }
      setMessages((current) => [...current, { id: `u-${Date.now()}`, role: "user", content: prompt }]);
      setGoal("");
      setEvents([]);
      let finalText = "";
      await streamGoal(sid, prompt, (event) => {
        if (event.event_type === "PLAN_CREATED") setPlan(event.payload || null);
        if (event.event_type === "MESSAGE_COMPLETED") finalText = String(event.payload?.content || "");
        if (event.event_type === "SYSTEM_ERROR") finalText = String(event.payload?.error || "error");
        setEvents((prev) => [...prev, event].slice(-80));
      });
      setMessages((current) => [
        ...current,
        { id: `a-${Date.now()}`, role: "agent", content: finalText || "Completed." },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Goal failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="page page--agent">
      <div className="agent-layout">
        <div className="panel agent-transcript">
          <p className="eyebrow">Goal</p>
          <h1>Agent</h1>
          <p className="muted">
            Submit a goal to the local Agent pipeline. Plans, tools, and results come from the backend, not from
            this shell.
          </p>
          {!online ? <div className="banner banner--danger">Backend disconnected. Goals cannot be submitted.</div> : null}
          {error ? <div className="banner banner--danger">{error}</div> : null}
          <div className="agent-transcript__log">
            {messages.length === 0 ? (
              <p className="muted">No goals in this session yet.</p>
            ) : (
              messages.map((message) => (
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
              void submit();
            }}
          >
            <input
              value={goal}
              onChange={(event) => setGoal(event.target.value)}
              placeholder={online ? "Describe the outcome you want…" : "Waiting for backend…"}
              disabled={!online || busy}
              aria-label="Goal"
            />
            <button type="submit" disabled={busy || !online || !goal.trim()}>
              {busy ? "Running" : "Run"}
            </button>
          </form>
        </div>
        <aside className="agent-aside">
          <article className="panel">
            <h2>Current plan</h2>
            {plan ? (
              <>
                <div className="mono subtle">{String(plan.plan_id || "")}</div>
                <div>{String(plan.status ?? "unavailable")}</div>
              </>
            ) : (
              <p className="muted">No plan yet.</p>
            )}
          </article>
          <article className="panel">
            <h2>Pipeline</h2>
            {events.length === 0 ? (
              <p className="muted">Pipeline events appear after a goal runs.</p>
            ) : (
              events.slice(-12).map((event, index) => (
                <div key={`${event.event_type}-${index}`} className="mono subtle">
                  {event.event_type}
                </div>
              ))
            )}
          </article>
        </aside>
      </div>
    </section>
  );
};
