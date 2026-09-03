import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import {
  DEFAULT_SECTION,
  parseSectionHash,
  sectionHref,
  type SectionId,
} from "../lib/navigation";

type NavigationContextValue = {
  section: SectionId;
  navigate: (id: SectionId) => void;
};

const NavigationContext = createContext<NavigationContextValue | null>(null);

export const NavigationProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [section, setSection] = useState<SectionId>(() => parseSectionHash(window.location.hash));

  useEffect(() => {
    const sync = () => setSection(parseSectionHash(window.location.hash));
    if (!window.location.hash) {
      window.location.replace(sectionHref(DEFAULT_SECTION));
    }
    window.addEventListener("hashchange", sync);
    return () => window.removeEventListener("hashchange", sync);
  }, []);

  const navigate = useCallback((id: SectionId) => {
    const next = sectionHref(id);
    if (window.location.hash !== next) {
      window.location.hash = next;
    }
    setSection(id);
  }, []);

  const value = useMemo(() => ({ section, navigate }), [section, navigate]);
  return <NavigationContext.Provider value={value}>{children}</NavigationContext.Provider>;
};

export function useNavigation(): NavigationContextValue {
  const ctx = useContext(NavigationContext);
  if (!ctx) throw new Error("useNavigation must be used within NavigationProvider");
  return ctx;
}
