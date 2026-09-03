import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
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

type SessionContextValue = {
  sessions: SessionRecord[];
  currentId: string | null;
  messages: ChatMessage[];
  events: ActivityEvent[];
  plan: PlanRecord | null;
  plans: PlanRecord[];
  busy: boolean;
  error: string | null;
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

  const refresh = useCallback(async () => {
    try {
      const list = await json<SessionRecord[]>("/api/sessions");
      setSessions(list);
      const collected: PlanRecord[] = [];
      for (const session of list) {
        if (!session.active_plan_id) continue;
        const next = await loadPlan(session.active_plan_id);
        if (next) collected.push(next);
      }
      try {
        const latest = await loadPlan("plan-001");
        if (latest && !collected.some((item) => item.plan_id === latest.plan_id)) collected.push(latest);
      } catch {
        /* alias may 404 */
      }
      setPlans(collected);
      if (currentId) {
        setMessages(await loadMessages(currentId));
        setEvents(await loadEvents(currentId));
        const current = list.find((item) => item.session_id === currentId);
        const loaded = await loadPlan(current?.active_plan_id ?? null);
        setPlan(loaded);
      }
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Session API unavailable");
    }
  }, [currentId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const selectSession = useCallback(async (id: string) => {
    setCurrentId(id);
    try {
      setMessages(await loadMessages(id));
      setEvents(await loadEvents(id));
      const session = await json<SessionRecord>(`/api/sessions/${encodeURIComponent(id)}`);
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
      setMessages([]);
      setEvents([]);
      setPlan(null);
      await refresh();
      return created.session_id;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create session");
      return null;
    }
  }, [refresh]);

  const deleteCurrent = useCallback(async () => {
    if (!currentId) return;
    await deleteJson(`/api/sessions/${encodeURIComponent(currentId)}`);
    setCurrentId(null);
    setMessages([]);
    setEvents([]);
    setPlan(null);
    await refresh();
  }, [currentId, refresh]);

  const sendPrompt = useCallback(
    async (prompt: string) => {
      const text = prompt.trim();
      if (!text || busy) return;
      setBusy(true);
      setError(null);
      try {
        let sid = currentId;
        if (!sid) {
          sid = await newSession();
          if (!sid) return;
        }
        setMessages((prev) => [...prev, { id: `u-${Date.now()}`, role: "user", content: text }]);
        let finalText = "";
        await streamGoal(sid, text, (event: StreamEvent) => {
          if (event.event_type === "PLAN_CREATED" && event.payload) {
            const payload = event.payload;
            const tasks = Array.isArray(payload.tasks) ? payload.tasks : [];
            setPlan({
              plan_id: asString(payload.plan_id),
              status: asString(payload.status),
              version: payload.version == null ? undefined : asString(payload.version),
              tasks: tasks.map((item) => {
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
              }),
            });
          }
          if (event.event_type === "MESSAGE_COMPLETED") {
            finalText = asString(event.payload?.content);
          }
          if (event.event_type === "SYSTEM_ERROR") {
            finalText = asString(event.payload?.error, "error");
          }
          setEvents((prev) =>
            [
              ...prev,
              {
                event_type: event.event_type,
                session_id: event.session_id,
                payload: event.payload,
                timestamp: event.timestamp,
              },
            ].slice(-80),
          );
        });
        setMessages((prev) => [...prev, { id: `a-${Date.now()}`, role: "assistant", content: finalText || "Completed." }]);
        await refresh();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Goal failed");
      } finally {
        setBusy(false);
      }
    },
    [busy, currentId, newSession, refresh],
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
