import React, { useState } from "react";
import { json } from "../lib/api";
import { EmptyState, IssueBanner, LoadingState, OfflineState, PageHeader } from "../components/ui";
import { useHealth } from "../state/HealthContext";
import { useSession } from "../state/SessionContext";
import type { MemoryHit } from "../lib/types";

export const MemoryPage: React.FC = () => {
  const { health } = useHealth();
  const session = useSession();
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<MemoryHit[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const online = health.connection === "online";

  const search = async (next: string, sessionId?: string | null) => {
    if (!online) return;
    setLoading(true);
    setSearched(true);
    try {
      const params = new URLSearchParams();
      params.set("query", next);
      if (sessionId) params.set("session_id", sessionId);
      setHits(await json<MemoryHit[]>(`/api/memory/search?${params.toString()}`));
      setError(null);
    } catch (err) {
      setHits(null);
      setError(err instanceof Error ? err.message : "Memory search unavailable");
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="page">
      <PageHeader eyebrow="Knowledge" title="Memory">
        Search uses `/api/memory/search`. Session history is returned when a session id is supplied.
      </PageHeader>
      {!online ? <OfflineState /> : null}
      <form
        className="composer"
        onSubmit={(event) => {
          event.preventDefault();
          void search(query);
        }}
      >
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search stored turns…"
          aria-label="Memory query"
          disabled={!online || loading}
        />
        <button type="submit" disabled={!online || loading}>
          Search
        </button>
      </form>
      <div className="row">
        <button
          className="btn btn--small"
          disabled={!online || !session.currentId || loading}
          onClick={() => void search("", session.currentId)}
        >
          Current session history
        </button>
      </div>
      {loading ? <LoadingState label="Searching memory…" /> : null}
      <IssueBanner message={error} />
      {!searched && !loading ? (
        <EmptyState title="No search yet">Enter a query or load the current session history.</EmptyState>
      ) : null}
      {hits && hits.length === 0 ? <EmptyState title="No matching records">The store returned zero hits for this query.</EmptyState> : null}
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
