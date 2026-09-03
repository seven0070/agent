import React from "react";
import type { ConnectionState } from "../lib/health";

const LABELS: Record<ConnectionState, string> = {
  loading: "Connecting",
  online: "Online",
  offline: "Disconnected",
};

export const StatusIndicator: React.FC<{
  state: ConnectionState;
  label?: string;
}> = ({ state, label }) => {
  return (
    <span className={`status-indicator status-indicator--${state}`} role="status">
      <span className="status-indicator__dot" aria-hidden="true" />
      <span>{label ?? LABELS[state]}</span>
    </span>
  );
};
