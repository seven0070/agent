import type { JsonValue } from "./types";

export function shortId(id: string, keep = 8): string {
  if (!id) return "—";
  return id.length <= keep + 1 ? id : `${id.slice(0, keep)}…`;
}

export function formatBytes(n: number): string {
  if (!Number.isFinite(n) || n < 0) return "—";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

export function formatTime(iso?: string | null): string {
  if (!iso) return "";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString();
}

export function truncate(text: string, max = 8000): string {
  if (text.length <= max) return text;
  return `${text.slice(0, max)}\n… truncated (${text.length.toLocaleString()} characters)`;
}

export function prettyJson(value: unknown, max = 8000): string {
  try {
    return truncate(JSON.stringify(value, null, 2), max);
  } catch {
    return String(value);
  }
}

export function summarizePayload(payload?: Record<string, JsonValue>): string {
  if (!payload) return "";
  const keys = ["tool_id", "status", "task_id", "plan_id", "error", "content", "kind"];
  const parts: string[] = [];
  for (const key of keys) {
    const value = payload[key];
    if (value == null || value === "") continue;
    const text = typeof value === "string" ? value : JSON.stringify(value);
    parts.push(`${key} ${text.slice(0, 72)}`);
    if (parts.length >= 3) break;
  }
  return parts.join(" · ");
}

export function isDeniedMessage(message: string): boolean {
  const lower = message.toLowerCase();
  return (
    lower.includes("403") ||
    lower.includes("denied") ||
    lower.includes("constitutional") ||
    lower.includes("not permitted")
  );
}
