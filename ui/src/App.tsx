import React, { useEffect, useMemo, useState } from "react";
import { json, streamGoal } from "./lib/api";

type View = "workspace" | "activity" | "evolution" | "trust" | "settings";

type Message = { id: string; role: "user" | "agent"; content: string };
type EventFrame = { event_type: string; payload?: Record<string, unknown> };

export const App: React.FC = () => {
  const [view, setView] = useState<View>("workspace");
  const [runtime, setRuntime] = useState("connecting");
  const [generation, setGeneration] = useState("agent-v1");
  const [goal, setGoal] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [events, setEvents] = useState<EventFrame[]>([]);
  const [plan, setPlan] = useState<Record<string, unknown> | null>(null);
  const [evolution, setEvolution] = useState<Record<string, unknown> | null>(null);
  const [approvals, setApprovals] = useState<Array<Record<string, unknown>>>([]);
  const [constitution, setConstitution] = useState<Record<string, unknown> | null>(null);
  const [settings, setSettings] = useState<Record<string, unknown> | null>(null);
  const [tools, setTools] = useState<Array<Record<string, unknown>>>([]);

  const refresh = async () => {
    try {
      const health = await json<Record<string, unknown>>("/health");
      const evo = await json<Record<string, unknown>>("/api/evolution/status");
      const pending = await json<Array<Record<string, unknown>>>("/api/approvals");
      const trust = await json<Record<string, unknown>>("/api/trust/constitution");
      const conf = await json<Record<string, unknown>>("/api/settings");
      const toolList = await json<Array<Record<string, unknown>>>("/api/tools");
      setRuntime("ready");
      setGeneration(String(health.active_generation || evo.active_generation || "agent-v1"));
      setEvolution(evo);
      setApprovals(pending);
      setConstitution(trust);
      setSettings(conf);
      setTools(toolList);
      setError(null);
    } catch (err) {
      setRuntime("offline");
      setError(err instanceof Error ? err.message : "Runtime unreachable");
    }
  };

  useEffect(() => {
    void refresh();
    const id = window.setInterval(() => void refresh(), 8000);
    return () => window.clearInterval(id);
  }, []);

  const submit = async () => {
    const prompt = goal.trim();
    if (!prompt || busy) return;
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
      setMessages((m) => [...m, { id: `u-${Date.now()}`, role: "user", content: prompt }]);
      setGoal("");
      setEvents([]);
      let finalText = "";
      await streamGoal(sid, prompt, (event) => {
        if (event.event_type === "PLAN_CREATED") setPlan(event.payload || null);
        if (event.event_type === "MESSAGE_COMPLETED") finalText = String(event.payload?.content || "");
        if (event.event_type === "SYSTEM_ERROR") finalText = String(event.payload?.error || "error");
        setEvents((prev) => [...prev, event].slice(-80));
      });
      setMessages((m) => [...m, { id: `a-${Date.now()}`, role: "agent", content: finalText || "Completed." }]);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Goal failed");
    } finally {
      setBusy(false);
    }
  };

  const nav: { id: View; label: string }[] = useMemo(
    () => [
      { id: "workspace", label: "Workspace" },
      { id: "activity", label: "Activity" },
      { id: "evolution", label: "Evolution" },
      { id: "trust", label: "Trust" },
      { id: "settings", label: "Settings" },
    ],
    [],
  );

  return (
    <div style={{ display: "flex", minHeight: "100%", background: "var(--bg)", color: "var(--fg)" }}>
      <aside
        style={{
          width: 220,
          borderRight: "1px solid var(--border)",
          background: "var(--bg-elevated)",
          display: "flex",
          flexDirection: "column",
        }}
      >
        <div style={{ padding: "24px 20px", fontWeight: 600, letterSpacing: "-0.03em" }}>AGENT</div>
        <nav style={{ display: "flex", flexDirection: "column", gap: 4, padding: "0 12px", flex: 1 }}>
          {nav.map((item) => (
            <button
              key={item.id}
              onClick={() => setView(item.id)}
              style={{
                height: 44,
                textAlign: "left",
                border: 0,
                borderRadius: 8,
                padding: "0 12px",
                background: view === item.id ? "var(--bg-subtle)" : "transparent",
                color: view === item.id ? "var(--fg)" : "var(--fg-muted)",
              }}
            >
              {item.label}
            </button>
          ))}
        </nav>
        <div style={{ padding: 20, fontSize: 11, color: "var(--fg-subtle)", borderTop: "1px solid var(--border)" }}>
          <div>{runtime}</div>
          <div style={{ fontFamily: "var(--mono)", marginTop: 4 }}>{generation}</div>
        </div>
      </aside>
      <main style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column" }}>
        <header style={{ height: 56, borderBottom: "1px solid var(--border)", display: "flex", alignItems: "center", padding: "0 24px", color: "var(--fg-muted)", fontSize: 14 }}>
          Governed self-evolution. Isolated candidates. Human approval.
        </header>
        {error ? <div style={{ padding: "8px 24px", background: "rgba(196,137,137,0.12)", color: "var(--danger)", fontSize: 13 }}>{error}</div> : null}
        <div style={{ flex: 1, overflow: "auto", padding: 24 }}>
          {view === "workspace" && (
            <Workspace
              goal={goal}
              setGoal={setGoal}
              submit={submit}
              busy={busy}
              runtime={runtime}
              messages={messages}
              events={events}
              plan={plan}
            />
          )}
          {view === "activity" && <Activity events={events} messages={messages} />}
          {view === "evolution" && (
            <Evolution
              evolution={evolution}
              approvals={approvals}
              generation={generation}
              busy={busy}
              onCycle={async () => {
                setBusy(true);
                try {
                  await json("/api/evolution/cycle?dry_run=false&demo=true", { method: "POST", body: JSON.stringify({ demo: true }) });
                  await refresh();
                  setView("evolution");
                } catch (err) {
                  setError(err instanceof Error ? err.message : "cycle failed");
                } finally {
                  setBusy(false);
                }
              }}
              onApprove={async (id, approved) => {
                setBusy(true);
                try {
                  await json(`/api/approvals/${id}?approved=${approved}`, { method: "POST" });
                  await refresh();
                } finally {
                  setBusy(false);
                }
              }}
              onRollback={async (id) => {
                setBusy(true);
                try {
                  await json("/api/evolution/rollback", { method: "POST", body: JSON.stringify({ mutation_id: id, reason: "operator rollback" }) });
                  await refresh();
                } finally {
                  setBusy(false);
                }
              }}
            />
          )}
          {view === "trust" && <Trust constitution={constitution} />}
          {view === "settings" && <Settings settings={settings} tools={tools} />}
        </div>
      </main>
    </div>
  );
};

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section style={{ border: "1px solid var(--border)", background: "var(--bg-elevated)", borderRadius: 24, padding: 20 }}>
      <h2 style={{ margin: "0 0 12px", fontSize: 11, letterSpacing: "0.16em", textTransform: "uppercase", color: "var(--fg-subtle)" }}>{title}</h2>
      {children}
    </section>
  );
}

function Workspace(props: {
  goal: string;
  setGoal: (v: string) => void;
  submit: () => void;
  busy: boolean;
  runtime: string;
  messages: Message[];
  events: EventFrame[];
  plan: Record<string, unknown> | null;
}) {
  return (
    <div style={{ display: "grid", gap: 16, gridTemplateColumns: "minmax(0,1fr) 320px", maxWidth: 1100, margin: "0 auto" }}>
      <section style={{ border: "1px solid var(--border)", background: "var(--bg-elevated)", borderRadius: 24, padding: 20, minHeight: "70vh", display: "flex", flexDirection: "column" }}>
        <h1 style={{ margin: 0, fontSize: 24, fontWeight: 500 }}>Issue a goal</h1>
        <p style={{ color: "var(--fg-muted)", fontSize: 14, maxWidth: "62ch" }}>
          Agent plans, uses tools, writes code in a sandbox, evaluates the result, and records observations for evolution.
        </p>
        <div style={{ flex: 1, overflow: "auto" }}>
          {props.messages.length === 0 ? (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 8 }}>
              {["Calculate 37 * 42", "Create python module and test", "Calculate 10 + 20 and save to calc_result.txt"].map((h) => (
                <button key={h} onClick={() => props.setGoal(h)} style={{ border: "1px solid var(--border)", background: "var(--bg)", color: "var(--fg-muted)", borderRadius: 16, padding: 16, textAlign: "left" }}>
                  {h}
                </button>
              ))}
            </div>
          ) : (
            props.messages.map((m) => (
              <article key={m.id} style={{ marginBottom: 12, padding: 14, borderRadius: 12, background: m.role === "user" ? "var(--bg-subtle)" : "transparent", border: m.role === "agent" ? "1px solid var(--border)" : 0 }}>
                <div style={{ fontSize: 11, color: "var(--fg-subtle)", textTransform: "uppercase", letterSpacing: "0.14em" }}>{m.role}</div>
                <pre style={{ whiteSpace: "pre-wrap", fontFamily: "var(--font)", fontSize: 14 }}>{m.content}</pre>
              </article>
            ))
          )}
        </div>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            props.submit();
          }}
          style={{ display: "flex", gap: 8, border: "1px solid var(--border)", borderRadius: 16, padding: 8, background: "var(--bg)" }}
        >
          <input
            value={props.goal}
            onChange={(e) => props.setGoal(e.target.value)}
            placeholder={props.runtime === "ready" ? "Calculate 37 * 42" : "Waiting for runtime…"}
            style={{ flex: 1, height: 44, border: 0, background: "transparent", color: "var(--fg)", padding: "0 12px", outline: "none" }}
          />
          <button
            disabled={props.busy || props.runtime !== "ready"}
            style={{ height: 44, padding: "0 16px", border: 0, borderRadius: 8, background: "var(--accent)", color: "var(--accent-fg)", fontWeight: 600 }}
          >
            Run
          </button>
        </form>
      </section>
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <Panel title="Current plan">
          {props.plan ? (
            <div>
              <div style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--fg-subtle)" }}>{String(props.plan.plan_id || "")}</div>
              <div>{String(props.plan.status)}</div>
            </div>
          ) : (
            <div style={{ color: "var(--fg-muted)", fontSize: 14 }}>No plan yet.</div>
          )}
        </Panel>
        <Panel title="Live activity">
          {props.events.length === 0 ? (
            <div style={{ color: "var(--fg-muted)", fontSize: 14 }}>Pipeline events appear here.</div>
          ) : (
            props.events.slice(-12).map((e, i) => (
              <div key={`${e.event_type}-${i}`} style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--fg-muted)" }}>
                {e.event_type}
              </div>
            ))
          )}
        </Panel>
      </div>
    </div>
  );
}

function Activity({ events, messages }: { events: EventFrame[]; messages: Message[] }) {
  return (
    <div style={{ maxWidth: 900, margin: "0 auto" }}>
      <Panel title="Pipeline">
        {events.length === 0 ? <p style={{ color: "var(--fg-muted)" }}>Run a goal to see the execution path.</p> : events.map((e, i) => <div key={i} style={{ fontFamily: "var(--mono)", fontSize: 12 }}>{e.event_type}</div>)}
      </Panel>
      <div style={{ height: 16 }} />
      <Panel title="Session">{messages.map((m) => <div key={m.id} style={{ fontSize: 13, color: "var(--fg-muted)" }}>{m.role}: {m.content.slice(0, 160)}</div>)}</Panel>
    </div>
  );
}

function Evolution(props: {
  evolution: Record<string, unknown> | null;
  approvals: Array<Record<string, unknown>>;
  generation: string;
  busy: boolean;
  onCycle: () => void;
  onApprove: (id: string, approved: boolean) => void;
  onRollback: (id: string) => void;
}) {
  const candidates = Array.isArray(props.evolution?.candidates) ? (props.evolution?.candidates as Array<Record<string, unknown>>) : [];
  const proposals = Array.isArray(props.evolution?.proposals) ? (props.evolution?.proposals as Array<Record<string, unknown>>) : [];
  const lineage = Array.isArray(props.evolution?.lineage) ? (props.evolution?.lineage as Array<Record<string, unknown>>) : [];
  return (
    <div style={{ maxWidth: 1100, margin: "0 auto", display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "end" }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 24, fontWeight: 500 }}>Evolution control plane</h1>
          <p style={{ color: "var(--fg-muted)", fontSize: 14 }}>Observe → candidate → Jcode → sandbox → evaluate → approve → promote / rollback.</p>
        </div>
        <button onClick={props.onCycle} disabled={props.busy} style={{ height: 40, padding: "0 16px", border: 0, borderRadius: 8, background: "var(--accent)", color: "var(--accent-fg)", fontWeight: 600 }}>
          Run demonstration cycle
        </button>
      </div>
      <Panel title="Active generation"><div style={{ fontFamily: "var(--mono)" }}>{props.generation}</div></Panel>
      {props.approvals.map((card) => (
        <Panel key={String(card.approval_id)} title="Human approval required">
          <div>{String(card.reason || card.action)}</div>
          <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
            <button onClick={() => props.onApprove(String(card.approval_id), true)} style={{ height: 36, padding: "0 12px", border: 0, borderRadius: 8, background: "var(--accent)", color: "var(--accent-fg)" }}>Approve and promote</button>
            <button onClick={() => props.onApprove(String(card.approval_id), false)} style={{ height: 36, padding: "0 12px", border: "1px solid var(--border)", borderRadius: 8, background: "transparent", color: "var(--fg)" }}>Reject</button>
          </div>
        </Panel>
      ))}
      <Panel title="Candidates">
        {candidates.length === 0 ? <p style={{ color: "var(--fg-muted)" }}>No candidates yet.</p> : candidates.slice().reverse().map((c) => (
          <article key={String(c.id || c.mutationId)} style={{ border: "1px solid var(--border)", borderRadius: 16, padding: 16, marginBottom: 8 }}>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <strong style={{ fontFamily: "var(--mono)", fontSize: 12 }}>{String(c.candidateVersion)}</strong>
              <span>{String(c.status)}</span>
            </div>
            <div style={{ color: "var(--fg-muted)", fontSize: 13 }}>{String(c.target)}</div>
            {String(c.status) === "promoted" ? (
              <button
                onClick={() => {
                  if (window.confirm(`Roll back ${String(c.candidateVersion)} to the previous known-good generation?`)) {
                    props.onRollback(String(c.mutationId));
                  }
                }}
                style={{ marginTop: 10, height: 32, padding: "0 10px", border: "1px solid var(--border)", borderRadius: 8, background: "transparent", color: "var(--fg)" }}
              >
                Roll back
              </button>
            ) : null}
          </article>
        ))}
      </Panel>
      <Panel title="Proposals">
        {proposals.length === 0 ? <p style={{ color: "var(--fg-muted)" }}>Observer has not armed a proposal.</p> : proposals.slice().reverse().map((p) => (
          <div key={String(p.proposal_id)}>{String(p.detected_problem)} — {String(p.status)}</div>
        ))}
      </Panel>
      <Panel title="Lineage">
        {lineage.map((row) => <div key={String(row.version)} style={{ fontFamily: "var(--mono)", fontSize: 12 }}>{String(row.version)}</div>)}
      </Panel>
    </div>
  );
}

function Trust({ constitution }: { constitution: Record<string, unknown> | null }) {
  const boundaries = Array.isArray(constitution?.protected_boundaries) ? (constitution?.protected_boundaries as string[]) : [];
  const invariants = Array.isArray(constitution?.invariants) ? (constitution?.invariants as Array<{ name: string; description: string }>) : [];
  return (
    <div style={{ maxWidth: 720, margin: "0 auto", display: "flex", flexDirection: "column", gap: 16 }}>
      <h1 style={{ margin: 0, fontSize: 24, fontWeight: 500 }}>Trust and constitution</h1>
      <Panel title="Protected boundaries">
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
          {boundaries.map((b) => <div key={b} style={{ fontFamily: "var(--mono)", fontSize: 12, background: "var(--bg-subtle)", padding: 10, borderRadius: 12 }}>{b}</div>)}
        </div>
      </Panel>
      <Panel title="Invariants">
        {invariants.map((inv) => (
          <div key={inv.name} style={{ marginBottom: 10 }}>
            <div>{inv.name}</div>
            <div style={{ color: "var(--fg-muted)", fontSize: 13 }}>{inv.description}</div>
          </div>
        ))}
      </Panel>
    </div>
  );
}

function Settings({ settings, tools }: { settings: Record<string, unknown> | null; tools: Array<Record<string, unknown>> }) {
  return (
    <div style={{ maxWidth: 720, margin: "0 auto", display: "flex", flexDirection: "column", gap: 16 }}>
      <h1 style={{ margin: 0, fontSize: 24, fontWeight: 500 }}>Settings</h1>
      <Panel title="Runtime">
        <div style={{ fontFamily: "var(--mono)", fontSize: 12 }}>Provider: {String(settings?.model_provider)}</div>
        <div style={{ fontFamily: "var(--mono)", fontSize: 12 }}>Model: {String(settings?.model_name)}</div>
        <div style={{ fontFamily: "var(--mono)", fontSize: 12 }}>Data: {String(settings?.data_dir)}</div>
        <div style={{ marginTop: 8, color: "var(--fg-muted)" }}>Constitution locked. Permission ceiling cannot be raised from this screen.</div>
      </Panel>
      <Panel title="Permissions">
        {tools.map((t) => (
          <div key={String(t.tool_id)} style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
            <span style={{ fontFamily: "var(--mono)" }}>{String(t.tool_id)}</span>
            <span>{String(t.permission)}</span>
          </div>
        ))}
      </Panel>
    </div>
  );
}
