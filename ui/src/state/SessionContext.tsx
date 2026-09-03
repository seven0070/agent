import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { deleteJson, json, postJson, streamGoal, type StreamEvent } from "../lib/api";
import type { ActivityEvent, ChatMessage, PlanRecord, PlanTask, SessionRecord } from "../lib/types";
import { asRecord, asString } from "../lib/types";

function toPlan(raw: Record<string, unknown>): PlanRecord {
  const tasksRaw = Array.isArray(raw.tasks) ? raw.tasks : [];
  const tasks: PlanTask[] = tasksRaw.map((item) => {
    const row = asRecord(item);
    return {
      id: asString(row.id),
      description: asString(row.description),
      dependencies: Array.isArray(row.dependencies) ? row.dependencies.map((d) => asString(d)) : [],
      status: asString(row.status, "UNKNOWN"),
      required_tool_id: row.required_tool_id == null ? null : asString(row.required_tool_id),
      inputs: asRecord(row.inputs),
      outputs: row.outputs ?? null,
      retry_count: typeof row.retry_count === "number" ? row.retry_count : 0,
      max_retries: typeof row.max_retries === "number" ? row.max_retries : 0,
      error: row.error == null ? null : asString(row.error),
      metadata: asRecord(row.metadata),
    };
  });
  return {
    plan_id: asString(raw.plan_id ?? raw.id),
    status: asString(raw.status),
    goal: raw.goal == null ? undefined : asString(raw.goal),
    version: raw.version == null ? undefined : asString(raw.version),
    tasks,
  };
}

function tasksFromPayload(payload: Record<string, unknown>): PlanTask[] {
  const tasks = Array.isArray(payload.tasks) ? payload.tasks : [];
  return tasks.map((item) => {
    const row = asRecord(item);
    return {
      id: asString(row.id),
      description: asString(row.description),
      dependencies: Array.isArray(row.dependencies) ? row.dependencies.map((d) => asString(d)) : [],
      status: asString(row.status, "UNKNOWN"),
      required_tool_id: row.required_tool_id == null ? null : asString(row.required_tool_id),
      inputs: asRecord(row.inputs),
      outputs: row.outputs ?? null,
      retry_count: typeof row.retry_count === "number" ? row.retry_count : 0,
      max_retries: typeof row.max_retries === "number" ? row.max_retries : 0,
      error: row.error == null ? null : asString(row.error),
      metadata: asRecord(row.metadata),
    };
  });
}

type SessionContextValue = {
  sessions: SessionRecord[];
  currentId: string | null;
  messages: ChatMessage[];
  events: ActivityEvent[];
  plan: PlanRecord | null;
  plans: PlanRecord[];
  busy: boolean;
  error: string | null;
  streamHint: string | null;
  workspaceEpoch: number;
  refresh: () => Promise<void>;
  selectSession: (id: string) => Promise<void>;
  newSession: () => Promise<string | null>;
  deleteCurrent: () => Promise<void>;
  sendPrompt: (prompt: string) => Promise<void>;
};

const SessionContext = createContext<SessionContextValue | null>(null);

export const SessionProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [sessions, setSessions] = useState<SessionRecord[]>([]);
  const [currentId, setCurrentId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [events, setEvents] = useState<ActivityEvent[]>([]);
  const [plan, setPlan] = useState<PlanRecord | null>(null);
  const [plans, setPlans] = useState<PlanRecord[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [streamHint, setStreamHint] = useState<string | null>(null);
  const [workspaceEpoch, setWorkspaceEpoch] = useState(0);
  const currentIdRef = useRef<string | null>(null);
  const busyRef = useRef(false);
  const refreshGen = useRef(0);
  const eventBuffer = useRef<ActivityEvent[]>([]);
  const flushTimer = useRef<number | null>(null);

  currentIdRef.current = currentId;
  busyRef.current = busy;

  const loadMessages = async (sessionId: string): Promise<ChatMessage[]> => {
    const hits = await json<Array<Record<string, unknown>>>(
      `/api/memory/search?query=&session_id=${encodeURIComponent(sessionId)}`,
    );
    return hits.map((hit, index) => ({
      id: asString(hit.id, `mem-${index}`),
      role: asString(hit.source, "agent"),
      content: asString(hit.content),
    }));
  };

  const loadEvents = async (sessionId: string): Promise<ActivityEvent[]> => {
    const rows = await json<Array<Record<string, unknown>>>(
      `/api/activity?session_id=${encodeURIComponent(sessionId)}&limit=80`,
    );
    return rows.map((row) => ({
      event_type: asString(row.event_type),
      session_id: row.session_id == null ? undefined : asString(row.session_id),
      payload: asRecord(row.payload),
      timestamp: row.timestamp == null ? undefined : asString(row.timestamp),
    }));
  };

  const loadPlan = async (planId: string | null): Promise<PlanRecord | null> => {
    if (!planId) return null;
    try {
      const raw = await json<Record<string, unknown>>(`/api/plans/${encodeURIComponent(planId)}`);
      return toPlan(raw);
    } catch {
      return null;
    }
  };

  const flushEvents = useCallback(() => {
    if (eventBuffer.current.length === 0) return;
    const batch = eventBuffer.current;
    eventBuffer.current = [];
    setEvents((prev) => [...prev, ...batch].slice(-80));
  }, []);

  const queueEvent = useCallback(
    (event: ActivityEvent) => {
      eventBuffer.current.push(event);
      if (flushTimer.current != null) return;
      flushTimer.current = window.setTimeout(() => {
        flushTimer.current = null;
        flushEvents();
      }, 50);
    },
    [flushEvents],
  );

  const refresh = useCallback(async () => {
    const gen = ++refreshGen.current;
    try {
      const list = await json<SessionRecord[]>("/api/sessions");
      const planIds = [...new Set(list.map((session) => session.active_plan_id).filter((id): id is string => Boolean(id)))];
      if (!planIds.includes("plan-001")) planIds.push("plan-001");
      const loaded = await Promise.all(planIds.map((id) => loadPlan(id)));
      const collected = loaded.filter((item): item is PlanRecord => item != null);
      const unique = collected.filter(
        (item, index) => collected.findIndex((other) => other.plan_id === item.plan_id) === index,
      );
      if (gen !== refreshGen.current) return;
      setSessions(list);
      setPlans(unique);
      const sid = currentIdRef.current;
      if (sid) {
        const [msgs, evs] = await Promise.all([loadMessages(sid), loadEvents(sid)]);
        if (gen !== refreshGen.current) return;
        setMessages(msgs);
        setEvents(evs);
        const current = list.find((item) => item.session_id === sid);
        setPlan(await loadPlan(current?.active_plan_id ?? null));
      }
      setError(null);
    } catch (err) {
      if (gen !== refreshGen.current) return;
      setError(err instanceof Error ? err.message : "Session API unavailable");
    }
  }, []);

  useEffect(() => {
    void refresh();
    return () => {
      if (flushTimer.current != null) window.clearTimeout(flushTimer.current);
    };
  }, [refresh]);

  const selectSession = useCallback(async (id: string) => {
    setCurrentId(id);
    currentIdRef.current = id;
    try {
      const [msgs, evs, session] = await Promise.all([
        loadMessages(id),
        loadEvents(id),
        json<SessionRecord>(`/api/sessions/${encodeURIComponent(id)}`),
      ]);
      setMessages(msgs);
      setEvents(evs);
      setPlan(await loadPlan(session.active_plan_id));
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load session");
    }
  }, []);

  const newSession = useCallback(async () => {
    try {
      const created = await postJson<SessionRecord>("/api/sessions", { title: "New chat" });
      setCurrentId(created.session_id);
      currentIdRef.current = created.session_id;
      setMessages([]);
      setEvents([]);
      setPlan(null);
      setStreamHint(null);
      await refresh();
      return created.session_id;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create session");
      return null;
    }
  }, [refresh]);

  const deleteCurrent = useCallback(async () => {
    if (!currentIdRef.current) return;
    await deleteJson(`/api/sessions/${encodeURIComponent(currentIdRef.current)}`);
    setCurrentId(null);
    currentIdRef.current = null;
    setMessages([]);
    setEvents([]);
    setPlan(null);
    await refresh();
  }, [refresh]);

  const sendPrompt = useCallback(
    async (prompt: string) => {
      const text = prompt.trim();
      if (!text || busyRef.current) return;
      setBusy(true);
      busyRef.current = true;
      setError(null);
      setStreamHint("Starting…");
      try {
        let sid = currentIdRef.current;
        if (!sid) {
          sid = await newSession();
          if (!sid) return;
        }
        const userId = `u-${Date.now()}`;
        const streamId = `stream-${Date.now()}`;
        setMessages((prev) => [
          ...prev,
          { id: userId, role: "user", content: text },
          { id: streamId, role: "assistant", content: "" },
        ]);
        let finalText = "";
        await streamGoal(sid, text, (event: StreamEvent) => {
          const payload = event.payload ?? {};
          if (event.event_type === "MESSAGE_STARTED") {
            setStreamHint("Processing goal…");
          } else if (event.event_type === "PLAN_CREATED") {
            setStreamHint("Plan created");
            setPlan({
              plan_id: asString(payload.plan_id),
              status: asString(payload.status),
              version: payload.version == null ? undefined : asString(payload.version),
              tasks: tasksFromPayload(payload),
            });
          } else if (event.event_type === "TOOL_EXECUTED") {
            setStreamHint(`Tool ${asString(payload.tool_id, "running")}`);
          } else if (event.event_type === "JCODE_COMPLETED") {
            setStreamHint("Jcode finished");
          } else if (event.event_type === "MESSAGE_DELTA") {
            const delta = asString(payload.content ?? payload.delta);
            if (delta) {
              finalText += delta;
              setMessages((prev) =>
                prev.map((msg) => (msg.id === streamId ? { ...msg, content: finalText } : msg)),
              );
            }
          } else if (event.event_type === "MESSAGE_COMPLETED") {
            finalText = asString(payload.content, finalText);
            setStreamHint("Completing…");
            setMessages((prev) =>
              prev.map((msg) => (msg.id === streamId ? { ...msg, content: finalText || "Completed." } : msg)),
            );
          } else if (event.event_type === "SYSTEM_ERROR") {
            finalText = asString(payload.error, "error");
            setError(finalText);
            setMessages((prev) =>
              prev.map((msg) => (msg.id === streamId ? { ...msg, content: finalText } : msg)),
            );
          } else {
            setStreamHint(event.event_type.replace(/_/g, " ").toLowerCase());
          }
          queueEvent({
            event_type: event.event_type,
            session_id: event.session_id,
            payload: event.payload,
            timestamp: event.timestamp,
          });
        });
        flushEvents();
        setMessages((prev) => {
          const hasFinal = prev.some((msg) => msg.id === streamId && msg.content);
          if (hasFinal) return prev;
          return prev.map((msg) =>
            msg.id === streamId ? { ...msg, content: finalText || "Completed." } : msg,
          );
        });
        setWorkspaceEpoch((n) => n + 1);
        await refresh();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Goal failed");
      } finally {
        setBusy(false);
        busyRef.current = false;
        setStreamHint(null);
      }
    },
    [flushEvents, newSession, queueEvent, refresh],
  );

  const value = useMemo(
    () => ({
      sessions,
      currentId,
      messages,
      events,
      plan,
      plans,
      busy,
      error,
      streamHint,
      workspaceEpoch,
      refresh,
      selectSession,
      newSession,
      deleteCurrent,
      sendPrompt,
    }),
    [
      sessions,
      currentId,
      messages,
      events,
      plan,
      plans,
      busy,
      error,
      streamHint,
      workspaceEpoch,
      refresh,
      selectSession,
      newSession,
      deleteCurrent,
      sendPrompt,
    ],
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
};

export function useSession(): SessionContextValue {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error("useSession must be used within SessionProvider");
  return ctx;
}
