import React, { useEffect, useState } from "react";
import { json } from "../lib/api";
import { EmptyState, ErrorState, LoadingState } from "../components/ui";
import { useSession } from "../state/SessionContext";
import type { MemoryHit } from "../lib/types";

export const MemoryPage: React.FC = () => {
  const session = useSession();
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<MemoryHit[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const search = async (next: string, sessionId?: string | null) => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.set("query", next);
      if (sessionId) params.set("session_id", sessionId);
      const path = `/api/memory/search?${params.toString()}`;
      setHits(await json<MemoryHit[]>(path));
      setError(null);
    } catch (err) {
      setHits(null);
      setError(err instanceof Error ? err.message : "Memory search unavailable");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void session.refresh();
  }, [session.refresh]);

  return (
    <section className="page">
      <p className="eyebrow">Knowledge</p>
      <h1>Memory</h1>
      <p className="muted">Search uses `/api/memory/search`. Session history is returned when a session id is supplied.</p>
      <form
        className="composer"
        onSubmit={(event) => {
          event.preventDefault();
          void search(query);
        }}
      >
        <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search stored turns…" aria-label="Memory query" />
        <button type="submit">Search</button>
      </form>
      <div className="row" style={{ marginTop: 12 }}>
        <button className="btn btn--small" disabled={!session.currentId} onClick={() => void search("", session.currentId)}>
          Current session history
        </button>
      </div>
      {loading ? <LoadingState /> : null}
      {error ? <ErrorState>{error}</ErrorState> : null}
      {hits && hits.length === 0 ? <EmptyState>No matching memory records.</EmptyState> : null}
      {hits && hits.length > 0 ? (
        <ul className="plain-list">
          {hits.map((hit, index) => (
            <li key={hit.id ?? `${hit.session_id ?? "hit"}-${index}`} className="panel">
              <div className="mono subtle">
                {hit.type ?? hit.role ?? "record"} {hit.source ? `· ${hit.source}` : ""} {hit.session_id ?? ""}
              </div>
              <pre>{hit.content ?? ""}</pre>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
};
