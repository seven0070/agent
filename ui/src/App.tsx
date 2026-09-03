import React from "react";
import { AppShell } from "./components/AppShell";
import { AgentPage } from "./pages/AgentPage";
import { EvaluationPage } from "./pages/EvaluationPage";
import { EvolutionPage } from "./pages/EvolutionPage";
import { FilesPage } from "./pages/FilesPage";
import { JcodePage } from "./pages/JcodePage";
import { MemoryPage } from "./pages/MemoryPage";
import { ModelsPage } from "./pages/ModelsPage";
import { ProjectsPage } from "./pages/ProjectsPage";
import { SecurityPage } from "./pages/SecurityPage";
import { SettingsPage } from "./pages/SettingsPage";
import { TasksPage } from "./pages/TasksPage";
import { ToolsPage } from "./pages/ToolsPage";
import { WorkspacePage } from "./pages/WorkspacePage";
import { HealthProvider } from "./state/HealthContext";
import { NavigationProvider, useNavigation } from "./state/NavigationContext";
import { SessionProvider } from "./state/SessionContext";

const SectionSwitch: React.FC = () => {
  const { section } = useNavigation();
  switch (section) {
    case "agent":
      return <AgentPage />;
    case "workspace":
      return <WorkspacePage />;
    case "tasks":
      return <TasksPage />;
    case "projects":
      return <ProjectsPage />;
    case "files":
      return <FilesPage />;
    case "memory":
      return <MemoryPage />;
    case "tools":
      return <ToolsPage />;
    case "jcode":
      return <JcodePage />;
    case "models":
      return <ModelsPage />;
    case "evaluation":
      return <EvaluationPage />;
    case "evolution":
      return <EvolutionPage />;
    case "security":
      return <SecurityPage />;
    case "settings":
      return <SettingsPage />;
    default:
      return <AgentPage />;
  }
};

export const App: React.FC = () => {
  return (
    <HealthProvider>
      <NavigationProvider>
        <SessionProvider>
          <AppShell>
            <SectionSwitch />
          </AppShell>
        </SessionProvider>
      </NavigationProvider>
    </HealthProvider>
  );
};
