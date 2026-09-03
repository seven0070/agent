import React, { useCallback, useEffect, useState } from "react";
import { json, postJson } from "../lib/api";
import { EmptyState, ErrorState, LoadingState, StatusBadge } from "../components/ui";
import type { EvolutionCandidate, EvolutionStatus } from "../lib/types";
import { asString } from "../lib/types";

export const EvolutionPage: React.FC = () => {
  const [status, setStatus] = useState<EvolutionStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

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
    void load();
  }, [load]);

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
    if (!window.confirm(`Roll back mutation ${id}?`)) return;
    setBusy(true);
    try {
      await postJson("/api/evolution/rollback", { mutation_id: id, reason: "operator rollback" });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Rollback failed");
    } finally {
      setBusy(false);
    }
  };

  const candidates: EvolutionCandidate[] = status?.candidates ?? [];

  return (
    <section className="page page--wide">
      <p className="eyebrow">Control plane</p>
      <h1>Evolution</h1>
      <p className="muted">
        Governed observe → propose → candidate → evaluate → gate → approve/canary → promote/rollback. Constitution
        targets cannot be mutated from this UI.
      </p>
      {error ? <ErrorState>{error}</ErrorState> : null}
      {!status && !error ? <LoadingState /> : null}
      {status ? (
        <div className="stack">
          <article className="panel">
            <h2>State</h2>
            <dl className="meta-list">
              <div>
                <dt>Mode</dt>
                <dd>{status.mode}</dd>
              </div>
              <div>
                <dt>Active generation</dt>
                <dd>{status.active_generation}</dd>
              </div>
              <div>
                <dt>Pending mutations</dt>
                <dd>{String(status.pending_mutations)}</dd>
              </div>
            </dl>
            <button className="btn" disabled={busy} onClick={() => void runLive()}>
              Run cycle from live observations
            </button>
          </article>
          <article className="panel">
            <h2>Gate</h2>
            {status.gate ? <pre className="code-block">{JSON.stringify(status.gate, null, 2)}</pre> : <EmptyState>No gate result yet.</EmptyState>}
          </article>
          <article className="panel">
            <h2>Candidates</h2>
            {candidates.length === 0 ? (
              <EmptyState>No candidates.</EmptyState>
            ) : (
              candidates.map((candidate) => (
                <div key={candidate.mutationId} className="task-card">
                  <div className="row-between">
                    <strong className="mono">{candidate.candidateVersion ?? candidate.id}</strong>
                    <StatusBadge value={candidate.status} />
                  </div>
                  <div className="muted">{candidate.target} · {candidate.rationale ?? ""}</div>
                  {candidate.status === "promoted" ? (
                    <button className="btn btn--small" disabled={busy} onClick={() => void rollback(candidate.mutationId)}>
                      Rollback
                    </button>
                  ) : null}
                  {candidate.requires_human_approval && candidate.status === "review" ? (
                    <div className="row">
                      <button className="btn btn--small" disabled={busy} onClick={() => void approve(candidate.mutationId, true)}>
                        Approve
                      </button>
                      <button className="btn btn--small" disabled={busy} onClick={() => void approve(candidate.mutationId, false)}>
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
              <EmptyState>No proposals.</EmptyState>
            ) : (
              status.proposals.map((proposal, index) => (
                <div key={asString(proposal.proposal_id, `p-${index}`)}>
                  {asString(proposal.detected_problem, "proposal")} — {asString(proposal.status)}
                </div>
              ))
            )}
          </article>
          <article className="panel">
            <h2>Lineage</h2>
            {status.lineage.length === 0 ? (
              <EmptyState>No lineage rows.</EmptyState>
            ) : (
              status.lineage.map((row, index) => (
                <div key={asString(row.version, `v-${index}`)} className="mono">
                  {asString(row.version, JSON.stringify(row))}
                </div>
              ))
            )}
          </article>
        </div>
      ) : null}
    </section>
  );
};
