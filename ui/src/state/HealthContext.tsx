import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { json } from "../lib/api";
import { INITIAL_HEALTH, type HealthSnapshot } from "../lib/health";

type HealthContextValue = {
  health: HealthSnapshot;
  refresh: () => Promise<void>;
};

const HealthContext = createContext<HealthContextValue | null>(null);

export const HealthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [health, setHealth] = useState<HealthSnapshot>(INITIAL_HEALTH);

  const refresh = useCallback(async () => {
    try {
      const payload = await json<Record<string, unknown>>("/health");
      let constitutionActive: boolean | null = null;
      try {
        const trust = await json<Record<string, unknown>>("/api/trust/constitution");
        constitutionActive = trust.protected === true;
      } catch {
        constitutionActive = null;
      }
      setHealth({
        connection: "online",
        version: typeof payload.version === "string" ? payload.version : null,
        generation: typeof payload.active_generation === "string" ? payload.active_generation : null,
        backendStatus: typeof payload.status === "string" ? payload.status : null,
        constitutionActive,
        error: null,
        fetchedAt: typeof payload.timestamp === "string" ? payload.timestamp : new Date().toISOString(),
      });
    } catch (err) {
      setHealth((prev) => ({
        ...prev,
        connection: "offline",
        backendStatus: null,
        constitutionActive: null,
        error: err instanceof Error ? err.message : "Backend unreachable",
        fetchedAt: new Date().toISOString(),
      }));
    }
  }, []);

  useEffect(() => {
    void refresh();
    const id = window.setInterval(() => void refresh(), 8000);
    return () => window.clearInterval(id);
  }, [refresh]);

  const value = useMemo(() => ({ health, refresh }), [health, refresh]);
  return <HealthContext.Provider value={value}>{children}</HealthContext.Provider>;
};

export function useHealth(): HealthContextValue {
  const ctx = useContext(HealthContext);
  if (!ctx) throw new Error("useHealth must be used within HealthProvider");
  return ctx;
}
