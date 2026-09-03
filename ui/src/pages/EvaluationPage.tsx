import React, { useEffect, useState } from "react";
import { json } from "../lib/api";
import { EmptyState, IssueBanner, LoadingState, OfflineState, PageHeader, StatusBadge } from "../components/ui";
import { asString } from "../lib/types";
import { prettyJson, summarizePayload } from "../lib/format";
import { useHealth } from "../state/HealthContext";
import { useSession } from "../state/SessionContext";

export const EvaluationPage: React.FC = () => {
  const { health } = useHealth();
  const session = useSession();
  const [rows, setRows] = useState<Array<Record<string, unknown>> | null>(null);
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
        setRows(await json<Array<Record<string, unknown>>>("/api/evaluations/reports"));
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Evaluation reports unavailable");
        setRows(null);
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, [online, session.workspaceEpoch]);

  const live = session.events.filter((event) => event.event_type === "EVALUATION_COMPLETED").slice(-3);

  return (
    <section className="page">
      <PageHeader eyebrow="Verification" title="Evaluation">
        Reports from `/api/evaluations/reports` (evolution evaluation records). Live pipeline scores are shown only when
        the current session emitted them. No scores are invented.
      </PageHeader>
      {!online ? <OfflineState /> : null}
      {loading ? <LoadingState /> : null}
      <IssueBanner message={error} />
      {live.length > 0 ? (
        <article className="panel">
          <h2>Latest live evaluations</h2>
          <ul className="plain-list">
            {live.map((event, index) => (
              <li key={`${event.timestamp}-${index}`} className="task-card">
                <div className="row-between">
                  <span className="mono">{asString(event.payload?.case_id, "live")}</span>
                  <StatusBadge value={event.payload?.passed === true ? "passed" : event.payload?.passed === false ? "failed" : "recorded"} />
                </div>
                <div className="muted">{summarizePayload(event.payload)}</div>
              </li>
            ))}
          </ul>
        </article>
      ) : null}
      {rows && rows.length === 0 ? (
        <EmptyState title="No evolution reports yet">
          Run a governed evolution cycle after real goals. This list stays empty until the control plane records a report.
        </EmptyState>
      ) : null}
      {rows && rows.length > 0 ? (
        <ul className="plain-list">
          {rows.map((row, index) => (
            <li key={asString(row.report_id ?? row.id, `eval-${index}`)} className="panel">
              <div className="row-between">
                <strong className="mono">{asString(row.report_id ?? row.id, `eval-${index}`)}</strong>
                <StatusBadge value={asString(row.recommendation ?? row.passed, "recorded")} />
              </div>
              <dl className="meta-list">
                {"safety_passed" in row ? (
                  <div>
                    <dt>Safety passed</dt>
                    <dd>{String(row.safety_passed)}</dd>
                  </div>
                ) : null}
                {"correctness" in row ? (
                  <div>
                    <dt>Correctness</dt>
                    <dd>{String(row.correctness)}</dd>
                  </div>
                ) : null}
                {"safety" in row ? (
                  <div>
                    <dt>Safety</dt>
                    <dd>{String(row.safety)}</dd>
                  </div>
                ) : null}
              </dl>
              <pre className="code-block">{prettyJson(row)}</pre>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
};
