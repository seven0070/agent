import React from "react";
import { useHealth } from "../state/HealthContext";
import { ContentContainer } from "./ContentContainer";
import { Header } from "./Header";
import { Sidebar } from "./Sidebar";
import { StatusBar } from "./StatusBar";

export const AppShell: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { health } = useHealth();
  return (
    <div className={`app-shell app-shell--${health.connection}`}>
      <Header />
      <Sidebar />
      <ContentContainer>{children}</ContentContainer>
      <StatusBar />
    </div>
  );
};
