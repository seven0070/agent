import React from "react";
import { displayValue } from "../lib/health";
import { useHealth } from "../state/HealthContext";

export const StatusBar: React.FC = () => {
  const { health } = useHealth();
  const runtime =
    health.connection === "loading" ? "connecting" : health.connection === "online" ? "ready" : "offline";
  const backend =
    health.connection === "online" ? displayValue(health.backendStatus, "connected") : "disconnected";
  const security =
    health.connection !== "online"
      ? "unavailable"
      : health.constitutionActive === true
        ? "constitution active"
        : health.constitutionActive === false
          ? "not confirmed"
          : "unavailable";
  const version = health.connection === "online" ? displayValue(health.version) : "unavailable";

  return (
    <footer className="status-bar" aria-label="Application status">
      <div className="status-bar__cell">
        <span className="status-bar__label">Runtime</span>
        <span>{runtime}</span>
      </div>
      <div className="status-bar__cell">
        <span className="status-bar__label">Backend</span>
        <span>{backend}</span>
      </div>
      <div className="status-bar__cell">
        <span className="status-bar__label">Security</span>
        <span>{security}</span>
      </div>
      <div className="status-bar__cell">
        <span className="status-bar__label">Version</span>
        <span className="status-bar__mono">{version}</span>
      </div>
    </footer>
  );
};
