import React from "react";
import { AppShell } from "./components/AppShell";
import { AgentPage } from "./pages/AgentPage";
import { ComingSoonPage } from "./pages/ComingSoonPage";
import { HealthProvider } from "./state/HealthContext";
import { NavigationProvider, useNavigation } from "./state/NavigationContext";

const SectionSwitch: React.FC = () => {
  const { section } = useNavigation();
  if (section === "agent") return <AgentPage />;
  return <ComingSoonPage section={section} />;
};

export const App: React.FC = () => {
  return (
    <HealthProvider>
      <NavigationProvider>
        <AppShell>
          <SectionSwitch />
        </AppShell>
      </NavigationProvider>
    </HealthProvider>
  );
};
