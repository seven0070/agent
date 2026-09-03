import React, { useEffect, useState } from "react";
import { EmptyState, ErrorState, StatusBadge, Timeline } from "../components/ui";
import { useSession } from "../state/SessionContext";
import type { PlanRecord } from "../lib/types";

export const TasksPage: React.FC = () => {
  const session = useSession();
  const [selected, setSelected] = useState<PlanRecord | null>(null);

  useEffect(() => {
    void session.refresh();
  }, [session.refresh]);

  useEffect(() => {
    if (!selected && session.plan) setSelected(session.plan);
  }, [selected, session.plan]);

  const plan = selected ?? session.plan;

  return (
    <section className="page page--wide">
      <p className="eyebrow">Orchestration</p>
      <h1>Tasks</h1>
      <p className="muted">Plans and task graphs returned by the planner after a goal runs. There is no separate task-create API.</p>
      {session.error ? <ErrorState>{session.error}</ErrorState> : null}
      <div className="split">
        <article className="panel">
          <h2>Plans</h2>
          {session.plans.length === 0 && !session.plan ? (
            <EmptyState>No plans yet. Run a goal from Agent.</EmptyState>
          ) : (
            <ul className="plain-list">
              {(session.plans.length ? session.plans : session.plan ? [session.plan] : []).map((item) => (
                <li key={item.plan_id}>
                  <button className="linkish" onClick={() => setSelected(item)}>
                    <span className="mono">{item.plan_id}</span> <StatusBadge value={item.status} />
                  </button>
                  {item.goal ? <div className="muted">{item.goal}</div> : null}
                </li>
              ))}
            </ul>
          )}
        </article>
        <article className="panel">
          <h2>Plan detail</h2>
          {!plan ? (
            <EmptyState>Select a plan.</EmptyState>
          ) : (
            <>
              <div className="mono subtle">{plan.plan_id} · {plan.version ?? "unversioned"}</div>
              <StatusBadge value={plan.status} />
              {plan.goal ? <p>{plan.goal}</p> : null}
              <h2>Tasks</h2>
              {plan.tasks.length === 0 ? (
                <EmptyState>This plan has no task records.</EmptyState>
              ) : (
                <ul className="plain-list">
                  {plan.tasks.map((task) => (
                    <li key={task.id} className="task-card">
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
                        <pre className="code-block">{typeof task.outputs === "string" ? task.outputs : JSON.stringify(task.outputs, null, 2)}</pre>
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
                  time: event.timestamp,
                }))}
              />
            </>
          )}
        </article>
      </div>
    </section>
  );
};
