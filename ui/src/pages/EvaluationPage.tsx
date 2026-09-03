import React, { useEffect, useState } from "react";
import { json } from "../lib/api";
import { EmptyState, ErrorState, LoadingState } from "../components/ui";
import { asString } from "../lib/types";

export const EvaluationPage: React.FC = () => {
  const [rows, setRows] = useState<Array<Record<string, unknown>> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
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
  }, []);

  return (
    <section className="page">
      <p className="eyebrow">Verification</p>
      <h1>Evaluation</h1>
      <p className="muted">Reports from `/api/evaluations/reports` (evolution evaluation records). No scores are invented.</p>
      {loading ? <LoadingState /> : null}
      {error ? <ErrorState>{error}</ErrorState> : null}
      {rows && rows.length === 0 ? (
        <EmptyState>No evaluation reports have been recorded yet. Run a governed evolution cycle after real goals.</EmptyState>
      ) : null}
      {rows && rows.length > 0 ? (
        <ul className="plain-list">
          {rows.map((row, index) => (
            <li key={asString(row.id, `eval-${index}`)} className="panel">
              <pre className="code-block">{JSON.stringify(row, null, 2)}</pre>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
};
