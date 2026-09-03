export type ConnectionState = "loading" | "online" | "offline";

export type HealthSnapshot = {
  connection: ConnectionState;
  version: string | null;
  generation: string | null;
  backendStatus: string | null;
  constitutionActive: boolean | null;
  error: string | null;
  fetchedAt: string | null;
};

export const INITIAL_HEALTH: HealthSnapshot = {
  connection: "loading",
  version: null,
  generation: null,
  backendStatus: null,
  constitutionActive: null,
  error: null,
  fetchedAt: null,
};

export function displayValue(value: string | null | undefined, fallback = "unavailable"): string {
  if (value == null || value.trim() === "") return fallback;
  return value;
}
