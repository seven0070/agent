import React, { useEffect, useState } from "react";
import { json } from "../lib/api";
import { EmptyState, ErrorState, LoadingState, StatusBadge, UnavailableState } from "../components/ui";
import type { ToolRecord } from "../lib/types";

export const ToolsPage: React.FC = () => {
  const [tools, setTools] = useState<ToolRecord[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        setTools(await json<ToolRecord[]>("/api/tools"));
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Tools API unavailable");
        setTools(null);
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, []);

  return (
    <section className="page">
      <p className="eyebrow">Capabilities</p>
      <h1>Tools</h1>
      <p className="muted">Registered tools and their Capability Broker permissions. Permissions cannot be raised from this UI.</p>
      {loading ? <LoadingState /> : null}
      {error ? <ErrorState>{error}</ErrorState> : null}
      {tools && tools.length === 0 ? <EmptyState>No tools registered.</EmptyState> : null}
      {tools && tools.length > 0 ? (
        <ul className="plain-list">
          {tools.map((tool) => (
            <li key={tool.tool_id} className="panel">
              <div className="row-between">
                <strong className="mono">{tool.tool_id}</strong>
                <StatusBadge value={tool.permission} />
              </div>
              <div className="muted">{tool.description}</div>
              <div className="mono subtle">risk {tool.risk_level}</div>
            </li>
          ))}
        </ul>
      ) : null}
      <UnavailableState title="MCP / skills listing NOT EXPOSED">
        MCP client wrappers exist in the backend, but there is no HTTP endpoint that lists connected MCP servers or
        skills. Those are not invented here.
      </UnavailableState>
    </section>
  );
};
