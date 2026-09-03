import React from "react";
import { sectionLabel } from "../lib/navigation";
import { useHealth } from "../state/HealthContext";
import { useNavigation } from "../state/NavigationContext";
import { StatusIndicator } from "./StatusIndicator";

export const Header: React.FC = () => {
  const { section } = useNavigation();
  const { health } = useHealth();
  return (
    <header className="app-header">
      <div className="app-header__identity">
        <span className="app-header__brand">Agent</span>
        <span className="app-header__divider" aria-hidden="true" />
        <span className="app-header__section">{sectionLabel(section)}</span>
      </div>
      <div className="app-header__status">
        {health.connection === "online" && health.generation ? (
          <span className="mono subtle">{health.generation}</span>
        ) : null}
        <StatusIndicator state={health.connection} />
      </div>
    </header>
  );
};
