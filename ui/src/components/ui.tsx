import React, { useEffect, useId, useMemo, useRef } from "react";
import { isDeniedMessage, prettyJson, truncate } from "../lib/format";

export const PageHeader: React.FC<{
  eyebrow: string;
  title: string;
  children?: React.ReactNode;
  actions?: React.ReactNode;
}> = ({ eyebrow, title, children, actions }) => (
  <header className="page-header">
    <div className="page-header__text">
      <p className="eyebrow">{eyebrow}</p>
      <h1>{title}</h1>
      {children ? <p className="lede">{children}</p> : null}
    </div>
    {actions ? <div className="page-header__actions">{actions}</div> : null}
  </header>
);

export const LoadingState: React.FC<{ label?: string }> = ({ label = "Loading…" }) => (
  <p className="state state--loading" role="status" aria-live="polite">
    <span className="state__spinner" aria-hidden="true" />
    {label}
  </p>
);

export const EmptyState: React.FC<{ title?: string; children: React.ReactNode }> = ({
  title = "Nothing here yet",
  children,
}) => (
  <div className="state state--empty">
    <strong>{title}</strong>
    <p className="muted">{children}</p>
  </div>
);

export const ErrorState: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div className="banner banner--danger" role="alert">
    {children}
  </div>
);

export const OfflineState: React.FC<{ children?: React.ReactNode }> = ({
  children = "Backend disconnected. This view is unavailable until the sidecar is online.",
}) => (
  <div className="banner banner--warn" role="status">
    {children}
  </div>
);

export const DeniedState: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div className="banner banner--danger" role="alert">
    <strong>Denied. </strong>
    {children}
  </div>
);

export const IssueBanner: React.FC<{ message: string | null | undefined }> = ({ message }) => {
  if (!message) return null;
  return isDeniedMessage(message) ? <DeniedState>{message}</DeniedState> : <ErrorState>{message}</ErrorState>;
};

export const UnavailableState: React.FC<{ title?: string; children: React.ReactNode }> = ({
  title = "NOT EXPOSED",
  children,
}) => (
  <article className="panel panel--muted">
    <h2>{title}</h2>
    <p className="muted">{children}</p>
  </article>
);

function badgeTone(value: string): string {
  const key = value.toLowerCase();
  if (
    key.includes("success") ||
    key.includes("completed") ||
    key.includes("succeeded") ||
    key.includes("allow") ||
    key.includes("online") ||
    key.includes("promoted") ||
    key.includes("pass") ||
    key.includes("protected") ||
    key.includes("locked") ||
    key.includes("ok")
  ) {
    return "ok";
  }
  if (
    key.includes("fail") ||
    key.includes("denied") ||
    key.includes("error") ||
    key.includes("reject") ||
    key.includes("rolled") ||
    key.includes("offline") ||
    key.includes("violation")
  ) {
    return "danger";
  }
  if (
    key.includes("pending") ||
    key.includes("running") ||
    key.includes("review") ||
    key.includes("approval") ||
    key.includes("canary") ||
    key.includes("evaluat") ||
    key.includes("proposed") ||
    key.includes("processing")
  ) {
    return "warn";
  }
  return "muted";
}

export const StatusBadge: React.FC<{ value: string }> = React.memo(({ value }) => {
  if (!value) return null;
  return <span className={`badge badge--${badgeTone(value)}`}>{value}</span>;
});
StatusBadge.displayName = "StatusBadge";

export const Timeline: React.FC<{
  items: Array<{ id: string; title: string; detail?: string; time?: string; status?: string }>;
}> = React.memo(({ items }) => {
  if (items.length === 0) return <EmptyState title="No activity">Events will appear here when the pipeline runs.</EmptyState>;
  return (
    <ol className="timeline">
      {items.map((item) => (
        <li key={item.id} className={`timeline__item timeline__item--${badgeTone(item.status ?? item.title)}`}>
          <div className="timeline__title">{item.title}</div>
          {item.detail ? <div className="muted">{item.detail}</div> : null}
          {item.time ? <div className="mono subtle">{item.time}</div> : null}
        </li>
      ))}
    </ol>
  );
});
Timeline.displayName = "Timeline";

export const CodeBlock: React.FC<{ value: string; label?: string }> = ({ value, label }) => (
  <pre className="code-block" tabIndex={0} aria-label={label ?? "Code"}>
    {truncate(value)}
  </pre>
);

export const JsonBlock: React.FC<{ value: unknown; label?: string }> = ({ value, label }) => (
  <CodeBlock value={prettyJson(value)} label={label ?? "JSON"} />
);

export const DataTable: React.FC<{
  columns: Array<{ key: string; label: string; mono?: boolean }>;
  rows: Array<Record<string, React.ReactNode>>;
  empty?: React.ReactNode;
}> = ({ columns, rows, empty }) => {
  if (rows.length === 0) return <>{empty ?? <EmptyState>No rows.</EmptyState>}</>;
  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            {columns.map((col) => (
              <th key={col.key} scope="col">
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={String(row.id ?? index)}>
              {columns.map((col) => (
                <td key={col.key} className={col.mono ? "mono" : undefined}>
                  {row[col.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export const LifecycleRail: React.FC<{
  stages: Array<{ id: string; label: string }>;
  activeId: string;
}> = ({ stages, activeId }) => {
  const activeIndex = Math.max(
    0,
    stages.findIndex((stage) => stage.id === activeId),
  );
  return (
    <ol className="lifecycle" aria-label="Evolution lifecycle">
      {stages.map((stage, index) => {
        const state = index < activeIndex ? "done" : index === activeIndex ? "active" : "idle";
        return (
          <li key={stage.id} className={`lifecycle__step lifecycle__step--${state}`}>
            <span className="lifecycle__dot" aria-hidden="true" />
            <span>{stage.label}</span>
          </li>
        );
      })}
    </ol>
  );
};

export const MetricList: React.FC<{ items: Array<{ label: string; value: React.ReactNode }> }> = ({
  items,
}) => (
  <dl className="meta-list">
    {items.map((item) => (
      <div key={item.label}>
        <dt>{item.label}</dt>
        <dd>{item.value}</dd>
      </div>
    ))}
  </dl>
);

export const ConfirmDialog: React.FC<{
  open: boolean;
  title: string;
  body: string;
  confirmLabel?: string;
  danger?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}> = ({ open, title, body, confirmLabel = "Confirm", danger, onConfirm, onCancel }) => {
  const titleId = useId();
  const dialogRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const previous = document.activeElement as HTMLElement | null;
    dialogRef.current?.querySelector<HTMLButtonElement>("button[data-confirm]")?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onCancel();
    };
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("keydown", onKey);
      previous?.focus();
    };
  }, [open, onCancel]);

  if (!open) return null;
  return (
    <div className="dialog-backdrop" onClick={onCancel}>
      <div
        ref={dialogRef}
        className="dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        onClick={(event) => event.stopPropagation()}
      >
        <h2 id={titleId}>{title}</h2>
        <p className="muted">{body}</p>
        <div className="dialog__actions">
          <button type="button" className="btn" onClick={onCancel}>
            Cancel
          </button>
          <button
            type="button"
            className={`btn ${danger ? "btn--danger" : "btn--primary"}`}
            data-confirm="true"
            onClick={onConfirm}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
};

export const FileTree: React.FC<{
  files: Array<{ id: string; path: string; name: string }>;
  selectedId?: string | null;
  onSelect?: (id: string) => void;
}> = ({ files, selectedId, onSelect }) => {
  const grouped = useMemo(() => {
    const buckets = new Map<string, typeof files>();
    for (const file of files) {
      const slash = file.path.replace(/\\/g, "/").lastIndexOf("/");
      const folder = slash === -1 ? "(root)" : file.path.slice(0, slash);
      const list = buckets.get(folder) ?? [];
      list.push(file);
      buckets.set(folder, list);
    }
    return [...buckets.entries()];
  }, [files]);

  if (files.length === 0) return <EmptyState title="Empty workspace">No files in the sandbox.</EmptyState>;

  return (
    <ul className="file-tree">
      {grouped.map(([folder, items]) => (
        <li key={folder}>
          <div className="file-tree__folder">{folder}</div>
          <ul>
            {items.map((file) => (
              <li key={file.id}>
                {onSelect ? (
                  <button
                    type="button"
                    className={`file-tree__item${file.id === selectedId ? " is-active" : ""}`}
                    onClick={() => onSelect(file.id)}
                    aria-current={file.id === selectedId ? "true" : undefined}
                  >
                    <span className="mono">{file.name}</span>
                    <span className="subtle file-tree__path">{file.path}</span>
                  </button>
                ) : (
                  <div className="file-tree__item">
                    <span className="mono">{file.name}</span>
                    <span className="subtle file-tree__path">{file.path}</span>
                  </div>
                )}
              </li>
            ))}
          </ul>
        </li>
      ))}
    </ul>
  );
};
