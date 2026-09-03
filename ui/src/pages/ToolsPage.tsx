import React, { useEffect, useState } from "react";
import { json } from "../lib/api";
import {
  DataTable,
  EmptyState,
  IssueBanner,
  LoadingState,
  OfflineState,
  PageHeader,
  StatusBadge,
  UnavailableState,
} from "../components/ui";
import { useHealth } from "../state/HealthContext";
import type { ToolRecord } from "../lib/types";

export const ToolsPage: React.FC = () => {
  const { health } = useHealth();
  const [tools, setTools] = useState<ToolRecord[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const online = health.connection === "online";

  useEffect(() => {
    if (!online) {
      setLoading(false);
      return;
    }
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
  }, [online]);

  return (
    <section className="page">
      <PageHeader eyebrow="Capabilities" title="Tools">
        Registered tools and their Capability Broker permissions. Permissions cannot be raised from this UI.
      </PageHeader>
      {!online ? <OfflineState /> : null}
      {loading ? <LoadingState /> : null}
      <IssueBanner message={error} />
      {tools ? (
        <DataTable
          columns={[
            { key: "id", label: "Tool", mono: true },
            { key: "permission", label: "Permission" },
            { key: "risk", label: "Risk" },
            { key: "description", label: "Description" },
          ]}
          rows={tools.map((tool) => ({
            id: tool.tool_id,
            permission: <StatusBadge value={tool.permission} />,
            risk: tool.risk_level,
            description: tool.description,
          }))}
          empty={<EmptyState title="No tools registered">The broker returned an empty registry.</EmptyState>}
        />
      ) : null}
      <UnavailableState title="MCP / skills listing NOT EXPOSED">
        MCP client wrappers exist in the backend, but there is no HTTP endpoint that lists connected MCP servers or
        skills. Those are not invented here.
      </UnavailableState>
    </section>
  );
};
