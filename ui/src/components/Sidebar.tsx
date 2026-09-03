import React from "react";
import { Navigation } from "./Navigation";

export const Sidebar: React.FC = () => {
  return (
    <aside className="app-sidebar">
      <Navigation />
    </aside>
  );
};
