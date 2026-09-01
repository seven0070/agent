# Layer 9: Evolution Model & Component Versioning

## Overview
Metamorphosis is governed by an out-of-band **Evolution Controller** (Layer 9). The agent does not mutate its live source code in-place during task execution.

## Evolution Pipeline

```text
    ┌──────────┐
    │   RUN    │  Agent executes user tasks using current active version
    └────┬─────┘
         │
         ▼
    ┌──────────┐
    │ OBSERVE  │  Log traces, performance metrics, and failures recorded
    └────┬─────┘
         │
         ▼
┌────────┴─────────┐
│ COLLECT EVIDENCE │  Identify weaknesses or performance bottlenecks
└────────┬─────────┘
         │
         ▼
┌────────┴─────────┐
│ PROPOSE MUTATION │  Formulate targeted candidate improvement
└────────┬─────────┘
         │
         ▼
┌────────┴─────────┐
│ CREATE CANDIDATE │  Instantiate candidate component version (e.g. planner-v2)
└────────┬─────────┘
         │
         ▼
    ┌──────────┐
    │ SANDBOX  │  Deploy candidate in isolated evaluation environment
    └────┬─────┘
         │
         ▼
    ┌──────────┐
    │   TEST   │  Run automated test suite and regression benchmarks
    └────┬─────┘
         │
         ▼
┌────────┴─────────┐
│    EVALUATE      │  Compare metrics against baseline performance
└────────┬─────────┘
         │
         ▼
┌────────┴─────────┐
│  PROMOTION GATE  ├── REJECT ──────► Discard candidate
│                  ├── HUMAN APPROVAL
│                  └── CANARY
└────────┬─────────┘
         │
         ▼
    ┌──────────┐
    │ MONITOR  ├── REGRESSION ──► Automatic Rollback
    └────┬─────┘
         │ (Success)
         ▼
┌────────┴─────────┐
│ PROMOTE CANDIDATE│ Set new component version as standard active target
└──────────────────┘
```

## Initial Evolvable Components
- Planner strategies
- Agent routing tables
- Tool selection policies
- Skill definitions
- Memory indexing and retrieval strategies
- Model routing rules
