import React from "react";

export const LoadingState: React.FC<{ label?: string }> = ({ label = "Loading…" }) => (
  <p className="muted">{label}</p>
);

export const EmptyState: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <p className="muted">{children}</p>
);

export const ErrorState: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div className="banner banner--danger">{children}</div>
);

export const UnavailableState: React.FC<{ title?: string; children: React.ReactNode }> = ({
  title = "NOT EXPOSED",
  children,
}) => (
  <article className="panel">
    <h2>{title}</h2>
    <p className="muted">{children}</p>
  </article>
);

export const StatusBadge: React.FC<{ value: string }> = ({ value }) => {
  const key = value.toLowerCase();
  const tone =
    key.includes("success") || key.includes("completed") || key.includes("allow") || key.includes("online") || key.includes("promoted")
      ? "ok"
      : key.includes("fail") || key.includes("denied") || key.includes("error") || key.includes("reject")
        ? "danger"
        : key.includes("pending") || key.includes("running") || key.includes("review") || key.includes("approval")
          ? "warn"
          : "muted";
  return <span className={`badge badge--${tone}`}>{value}</span>;
};

export const Timeline: React.FC<{
  items: Array<{ id: string; title: string; detail?: string; time?: string }>;
}> = ({ items }) => {
  if (items.length === 0) return <EmptyState>No events.</EmptyState>;
  return (
    <ol className="timeline">
      {items.map((item) => (
        <li key={item.id}>
          <div className="timeline__title">{item.title}</div>
          {item.detail ? <div className="muted">{item.detail}</div> : null}
          {item.time ? <div className="mono subtle">{item.time}</div> : null}
        </li>
      ))}
    </ol>
  );
};

export const CodeBlock: React.FC<{ value: string }> = ({ value }) => (
  <pre className="code-block">{value}</pre>
);
