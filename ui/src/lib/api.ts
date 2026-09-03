export type StreamEvent = {
  event_type: string;
  session_id?: string;
  payload?: Record<string, unknown>;
  timestamp?: string;
};

function apiRoot(): string {
  if (typeof window === "undefined") return "";
  const w = window as Window & { __TAURI_INTERNALS__?: unknown; __TAURI__?: unknown };
  if (w.__TAURI_INTERNALS__ || w.__TAURI__) return "http://127.0.0.1:8000";
  const { protocol, hostname } = window.location;
  if (protocol === "tauri:" || hostname === "tauri.localhost") return "http://127.0.0.1:8000";
  return "";
}

export async function json<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${apiRoot()}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
  });
  if (!res.ok) {
    let detail: unknown = res.statusText;
    try {
      const body = await res.json();
      detail = (body && (body.detail || body.reason)) || body;
    } catch {
      /* ignore */
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return res.json() as Promise<T>;
}

export async function streamGoal(
  sessionId: string,
  prompt: string,
  onEvent: (event: StreamEvent) => void,
): Promise<void> {
  const res = await fetch(`${apiRoot()}/api/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, prompt }),
  });
  if (!res.ok || !res.body) {
    throw new Error(`Agent stream failed (${res.status})`);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() ?? "";
    for (const chunk of chunks) {
      const line = chunk.split("\n").find((item) => item.startsWith("data:"));
      if (!line) continue;
      const raw = line.replace(/^data:\s?/, "").trim();
      if (!raw) continue;
      try {
        onEvent(JSON.parse(raw) as StreamEvent);
      } catch {
        /* ignore partial frames */
      }
    }
  }
}
