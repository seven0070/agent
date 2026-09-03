import React, { useEffect, useState } from "react";
import { EmptyState, ErrorState, IssueBanner, PageHeader, StatusBadge, Timeline } from "../components/ui";
import { prettyJson, shortId, summarizePayload } from "../lib/format";
import { useSession } from "../state/SessionContext";
import type { PlanRecord } from "../lib/types";

export const TasksPage: React.FC = () => {
  const session = useSession();
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedId && session.plan) setSelectedId(session.plan.plan_id);
  }, [selectedId, session.plan]);

  const listed = session.plans.length ? session.plans : session.plan ? [session.plan] : [];
  const plan: PlanRecord | null =
    listed.find((item) => item.plan_id === selectedId) ?? session.plan ?? listed[0] ?? null;

  return (
    <section className="page page--wide page--fill">
      <PageHeader eyebrow="Orchestration" title="Tasks">
        Plans and task graphs returned by the planner after a goal runs. There is no separate task-create API.
      </PageHeader>
      <IssueBanner message={session.error} />
      <div className="split split--uneven page--fill">
        <article className="panel panel--fill">
          <h2>Plans</h2>
          {listed.length === 0 ? (
            <EmptyState title="No plans yet">Run a goal from Agent. Plans appear here from the live session.</EmptyState>
          ) : (
            <ul className="plain-list scroll-y">
              {listed.map((item) => (
                <li key={item.plan_id}>
                  <button
                    type="button"
                    className={`selectable${item.plan_id === plan?.plan_id ? " is-active" : ""}`}
                    aria-current={item.plan_id === plan?.plan_id ? "true" : undefined}
                    onClick={() => setSelectedId(item.plan_id)}
                  >
                    <span className="row-between">
                      <span className="mono">{shortId(item.plan_id, 12)}</span>
                      <StatusBadge value={item.status} />
                    </span>
                    {item.goal ? <div className="muted">{item.goal}</div> : null}
                    <div className="subtle">{item.tasks.length} tasks</div>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </article>
        <article className="panel panel--fill">
          <h2>Plan detail</h2>
          {!plan ? (
            <EmptyState title="Select a plan">Choose a plan to inspect tasks and live events.</EmptyState>
          ) : (
            <div className="stack scroll-y">
              <div className="row-between">
                <div>
                  <div className="mono">{plan.plan_id}</div>
                  <div className="subtle">{plan.version ?? "unversioned"}</div>
                </div>
                <StatusBadge value={plan.status} />
              </div>
              {plan.goal ? <p>{plan.goal}</p> : null}
              <h2>Tasks</h2>
              {plan.tasks.length === 0 ? (
                <EmptyState title="No task records">This plan has no task graph.</EmptyState>
              ) : (
                <ul className="plain-list">
                  {plan.tasks.map((task) => (
                    <li key={task.id} className={`task-card task-card--${toneFor(task.status)}`}>
                      <div className="row-between">
                        <strong className="mono">{task.id}</strong>
                        <StatusBadge value={task.status} />
                      </div>
                      <div>{task.description}</div>
                      <div className="mono subtle">
                        tool: {task.required_tool_id ?? "none"} · retries {task.retry_count}/{task.max_retries}
                      </div>
                      {task.error ? <ErrorState>{task.error}</ErrorState> : null}
                      {task.outputs != null ? (
                        <pre className="code-block">{typeof task.outputs === "string" ? task.outputs : prettyJson(task.outputs)}</pre>
                      ) : null}
                    </li>
                  ))}
                </ul>
              )}
              <h2>Live events</h2>
              <Timeline
                items={session.events.map((event, index) => ({
                  id: `${event.timestamp ?? "t"}-${index}`,
                  title: event.event_type,
                  detail: summarizePayload(event.payload),
                  time: event.timestamp,
                  status: event.event_type,
                }))}
              />
            </div>
          )}
        </article>
      </div>
    </section>
  );
};

function toneFor(status: string): string {
  const key = status.toLowerCase();
  if (key.includes("fail") || key.includes("error")) return "danger";
  if (key.includes("success") || key.includes("complete") || key.includes("succeed")) return "ok";
  if (key.includes("run") || key.includes("pend") || key.includes("active")) return "warn";
  return "muted";
}
