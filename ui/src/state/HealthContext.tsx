import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { json } from "../lib/api";
import { INITIAL_HEALTH, type HealthSnapshot } from "../lib/health";

type HealthContextValue = {
  health: HealthSnapshot;
  refresh: () => Promise<void>;
};

const HealthContext = createContext<HealthContextValue | null>(null);

export const HealthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [health, setHealth] = useState<HealthSnapshot>(INITIAL_HEALTH);
  const constitutionTick = useRef(0);
  const constitutionKnown = useRef<boolean | null>(null);

  const refresh = useCallback(async () => {
    try {
      const payload = await json<Record<string, unknown>>("/health");
      constitutionTick.current += 1;
      let constitutionActive = constitutionKnown.current;
      if (constitutionTick.current === 1 || constitutionTick.current % 4 === 0 || constitutionActive == null) {
        try {
          const trust = await json<Record<string, unknown>>("/api/trust/constitution");
          constitutionActive = trust.protected === true;
          constitutionKnown.current = constitutionActive;
        } catch {
          constitutionActive = null;
          constitutionKnown.current = null;
        }
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
      constitutionKnown.current = null;
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
    const id = window.setInterval(() => void refresh(), 12000);
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
