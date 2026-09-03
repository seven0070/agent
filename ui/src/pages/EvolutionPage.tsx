import React, { useCallback, useEffect, useMemo, useState } from "react";
import { json, postJson } from "../lib/api";
import {
  ConfirmDialog,
  EmptyState,
  IssueBanner,
  LifecycleRail,
  LoadingState,
  MetricList,
  OfflineState,
  PageHeader,
  StatusBadge,
} from "../components/ui";
import { asString } from "../lib/types";
import { prettyJson } from "../lib/format";
import { useHealth } from "../state/HealthContext";
import type { EvolutionCandidate, EvolutionStatus } from "../lib/types";

const STAGES = [
  { id: "proposal", label: "Proposal" },
  { id: "candidate", label: "Candidate" },
  { id: "experiment", label: "Experiment" },
  { id: "evaluation", label: "Evaluation" },
  { id: "gate", label: "Gate" },
  { id: "approval", label: "Approval / Canary" },
  { id: "promote", label: "Promote / Rollback" },
];

function activeStage(status: EvolutionStatus): string {
  const candidates = status.candidates ?? [];
  if (candidates.some((item) => item.status === "promoted" || item.status === "rolled_back")) return "promote";
  if (candidates.some((item) => item.status === "canary" || item.status === "review")) return "approval";
  if (status.gate && asString(status.gate.decision) && asString(status.gate.decision) !== "IDLE") return "gate";
  if ((status.evaluations?.length ?? 0) > 0 || candidates.some((item) => item.status === "evaluating")) return "evaluation";
  if (candidates.some((item) => item.status === "proposed" || item.status === "evaluating")) return "experiment";
  if (candidates.length > 0) return "candidate";
  if (status.proposals.length > 0) return "proposal";
  return "proposal";
}

export const EvolutionPage: React.FC = () => {
  const { health } = useHealth();
  const [status, setStatus] = useState<EvolutionStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [confirmId, setConfirmId] = useState<string | null>(null);
  const online = health.connection === "online";

  const load = useCallback(async () => {
    try {
      setStatus(await json<EvolutionStatus>("/api/evolution/status"));
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Evolution status unavailable");
      setStatus(null);
    }
  }, []);

  useEffect(() => {
    if (!online) return;
    void load();
  }, [load, online]);

  const runLive = async () => {
    setBusy(true);
    try {
      await postJson("/api/evolution/cycle?dry_run=false", { use_live_observations: true });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Cycle failed");
    } finally {
      setBusy(false);
    }
  };

  const approve = async (id: string, approved: boolean) => {
    setBusy(true);
    try {
      await postJson(`/api/evolution/mutations/${encodeURIComponent(id)}/approve?approved=${approved}`, {});
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Approval failed");
    } finally {
      setBusy(false);
    }
  };

  const rollback = async (id: string) => {
    setBusy(true);
    try {
      await postJson("/api/evolution/rollback", { mutation_id: id, reason: "operator rollback" });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Rollback failed");
    } finally {
      setBusy(false);
      setConfirmId(null);
    }
  };

  const candidates: EvolutionCandidate[] = status?.candidates ?? [];
  const stage = status ? activeStage(status) : "proposal";
  const gateDecision = status?.gate ? asString(status.gate.decision, "IDLE") : "IDLE";

  const modeNote = useMemo(
    () =>
      status
        ? `${status.mode} — mutations stay behind the Promotion Gate. Constitution targets cannot be mutated from this UI.`
        : "Governed observe → propose → candidate → evaluate → gate → approve/canary → promote/rollback.",
    [status],
  );

  return (
    <section className="page page--wide">
      <PageHeader
        eyebrow="Control plane"
        title="Evolution"
        actions={
          <button className="btn" disabled={!online || busy} onClick={() => void runLive()}>
            {busy ? "Working…" : "Run cycle from live observations"}
          </button>
        }
      >
        {modeNote}
      </PageHeader>
      {!online ? <OfflineState /> : null}
      <IssueBanner message={error} />
      {!status && !error && online ? <LoadingState /> : null}
      {status ? (
        <div className="stack">
          <article className="panel">
            <h2>Lifecycle</h2>
            <LifecycleRail stages={STAGES} activeId={stage} />
            <p className="subtle">Highlighted stage is derived from real controller state, not a simulated progress bar.</p>
          </article>
          <article className="panel">
            <h2>State</h2>
            <MetricList
              items={[
                { label: "Mode", value: status.mode },
                { label: "Active generation", value: status.active_generation },
                { label: "Pending mutations", value: String(status.pending_mutations) },
                { label: "Canaries", value: String(status.canary_deployments.length) },
              ]}
            />
          </article>
          <article className="panel">
            <h2>Gate</h2>
            {gateDecision === "IDLE" && !status.gate?.status ? (
              <EmptyState title="Gate idle">No promotion decision yet. The gate stays fail-closed.</EmptyState>
            ) : (
              <MetricList
                items={[
                  { label: "Enforced", value: String(status.gate?.enforced ?? true) },
                  { label: "Decision", value: <StatusBadge value={gateDecision} /> },
                  { label: "Status", value: asString(status.gate?.status, "n/a") },
                  {
                    label: "Reasons",
                    value: Array.isArray(status.gate?.reasons)
                      ? status.gate.reasons.map((item) => asString(item)).join("; ") || "none"
                      : "none",
                  },
                ]}
              />
            )}
          </article>
          <article className="panel">
            <h2>Candidates</h2>
            {candidates.length === 0 ? (
              <EmptyState title="No candidates">Live observations must exist before a cycle can propose a mutation.</EmptyState>
            ) : (
              candidates.map((candidate) => (
                <div key={candidate.mutationId} className="task-card">
                  <div className="row-between">
                    <strong className="mono">{candidate.candidateVersion ?? candidate.id}</strong>
                    <StatusBadge value={candidate.status} />
                  </div>
                  <div className="muted">
                    {candidate.target} · {candidate.rationale ?? ""}
                  </div>
                  {candidate.canary_status ? (
                    <div className="subtle">canary {candidate.canary_status}</div>
                  ) : null}
                  {candidate.status === "promoted" ? (
                    <button className="btn btn--small btn--danger" disabled={busy} onClick={() => setConfirmId(candidate.mutationId)}>
                      Rollback
                    </button>
                  ) : null}
                  {candidate.requires_human_approval && candidate.status === "review" ? (
                    <div className="row">
                      <button className="btn btn--small btn--primary" disabled={busy} onClick={() => void approve(candidate.mutationId, true)}>
                        Approve
                      </button>
                      <button className="btn btn--small btn--danger" disabled={busy} onClick={() => void approve(candidate.mutationId, false)}>
                        Reject
                      </button>
                    </div>
                  ) : null}
                </div>
              ))
            )}
          </article>
          <article className="panel">
            <h2>Proposals</h2>
            {status.proposals.length === 0 ? (
              <EmptyState title="No proposals">The observer has not opened a proposal.</EmptyState>
            ) : (
              status.proposals.map((proposal, index) => (
                <div key={asString(proposal.proposal_id, `p-${index}`)} className="task-card">
                  <div className="row-between">
                    <span>{asString(proposal.detected_problem, "proposal")}</span>
                    <StatusBadge value={asString(proposal.status)} />
                  </div>
                </div>
              ))
            )}
          </article>
          <article className="panel">
            <h2>Lineage</h2>
            {status.lineage.length === 0 ? (
              <EmptyState title="No lineage rows">Generations appear after a promotion.</EmptyState>
            ) : (
              <ul className="plain-list">
                {status.lineage.map((row, index) => (
                  <li key={asString(row.version, `v-${index}`)} className="mono">
                    {asString(row.version, prettyJson(row, 400))}
                  </li>
                ))}
              </ul>
            )}
          </article>
        </div>
      ) : null}
      <ConfirmDialog
        open={confirmId != null}
        title="Roll back mutation"
        body={`Roll back mutation ${confirmId ?? ""}? This uses the governed rollback API. It does not bypass the Constitution.`}
        confirmLabel="Rollback"
        danger
        onCancel={() => setConfirmId(null)}
        onConfirm={() => {
          if (confirmId) void rollback(confirmId);
        }}
      />
    </section>
  );
};
