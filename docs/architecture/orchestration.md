# Layer 5 — Planning & Orchestration System Specification

## Overview
Layer 5 provides structured goal decomposition, task dependency graph management, capability execution through Layer 4 `CapabilityBroker`, deterministic failure recovery, plan versioning (`plan-v1` -> `plan-v2`), and structured event emissions.

## AgentScope 2.0.7.post1 Orchestration API Analysis

### Verified Modules in AgentScope
- `agentscope.pipeline.GoalPipeline`: Evaluates goal execution with executor agent and verifier agent.
- `agentscope.pipeline.PipelineProtocol`: Pipeline interface for streaming and execution protocols.

## Planning & Orchestration Architecture

```text
                           USER GOAL
                               │
                               ▼
                   PLANNER (`RuleBasedPlanner`)
                               │
                               ▼
                     PLAN DAG (`Plan`)
             (tasks, dependencies, versioning)
                               │
                               ▼
             ORCHESTRATOR (`PlanOrchestrator`)
                               │
       ┌───────────────────────┼───────────────────────┐
       ▼                       ▼                       ▼
 READY TASKS              RETRY ENGINE             REPLANNER
(unlocked by DAG)     (max retries = 2)       (plan-v1 -> plan-v2)
       │                       │                       │
       └───────────────────────┼───────────────────────┘
                               │
                               ▼
                   CAPABILITY BROKER (`CapabilityBroker`)
                   (Layer 4 Permission Policy)
```

## Task State Machine
Tasks (`PlanTask`) transition through strictly validated states:
- `PENDING`: Initial state upon plan creation
- `READY`: All prerequisite dependencies have `SUCCEEDED`
- `RUNNING`: Currently executing via `CapabilityBroker`
- `BLOCKED`: Dependency failed or requires human authorization
- `SUCCEEDED`: Task executed successfully
- `FAILED`: Task failed permanently after retries
- `CANCELLED`: Cancelled due to upstream failure or policy override

Attempting an invalid state transition (e.g. `PENDING` -> `SUCCEEDED` directly) raises `ValueError`.

## Dependency Resolution & DAG Validation
- Tasks explicitly specify dependency task IDs (`dependencies: ["task_a", "task_b"]`).
- `PlanOrchestrator` performs cycle detection using Depth-First Search (DFS) upon plan submission. Plans with cyclic dependencies (e.g. A -> B -> A) are rejected.

## Failure Recovery & Replanning Policy
1. **Task Retries**: When a task execution fails, the orchestrator checks `task.retry_count < task.max_retries`. If eligible, the task is retried.
2. **Permanent Failure & Replanning**: If retries are exhausted, the task is marked `FAILED`. The orchestrator triggers replanning, creating a new versioned plan (`plan-v2`) with repair tasks and metadata documenting the failure rationale.

## Security Boundary
The planner and orchestrator execute ALL task capabilities through `CapabilityBroker.execute_tool()`. Direct execution of arbitrary Python functions or shell commands is strictly prohibited.

## Multi-Agent & Human Approval Preparation
- Hooks for future subagent delegation (`SubagentHook`) and approval suspension (`REQUIRES_APPROVAL` state) are defined without prematurely introducing complex multi-agent runtimes or desktop UI elements.
