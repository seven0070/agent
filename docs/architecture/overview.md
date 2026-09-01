# Architecture Overview

This document describes the high-level architecture of the self-evolving local-first AI agent system.

## System Objective
The goal is to build a Windows desktop AI agent framework capable of controlled metamorphosis. The system can safely update its internal capabilities, planning strategies, skill definitions, memory routing, and agent compositions through an empirical, test-driven evolution pipeline while preserving strict constitutional boundaries.

## Key Architectural Principles

1. **Layered Construction**: Built sequentially layer by layer.
2. **Layer -1 Constitution**: Immutable constraints and safety boundaries that cannot be altered autonomously.
3. **Evolution Controller Control Plane**: An external governance control plane sitting beside the agent execution plane.
4. **AgentScope Foundation**: Built on top of AgentScope as the core agent and multi-agent infrastructure.
5. **Jcode Subsystem**: Specialized coding engine for inspecting, editing, and verifying repository code.
6. **Explicit Versioning**: All candidate mutations are versioned assets (`v1`, `v2`) subject to sandboxed testing and baseline evaluation before promotion.

## Target Architecture

```text
                 EVOLUTION CONTROLLER (Layer 9 Control Plane)
                         │
             observes / evaluates / governs
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│                      AGENT SYSTEM                      │
├────────────────────────────────────────────────────────┤
│ LAYER 10 — UI / DESKTOP (PLANNED)                      │
│ LAYER 8  — EVALUATION / VERIFICATION (PLANNED)        │
│ LAYER 7  — RUNTIME / SANDBOX (PLANNED)                 │
│ LAYER 6  — JCODE CODING ENGINE (PLANNED)               │
│ LAYER 5  — PLANNING / ORCHESTRATION (PLANNED)          │
│ LAYER 4  — TOOLS / SKILLS / MCP (PLANNED)              │
│ LAYER 3  — MEMORY / RAG (PLANNED)                      │
│ LAYER 2  — INTELLIGENCE / MODELS (PLANNED)             │
│ LAYER 1  — AGENT CORE (PLANNED)                        │
│ LAYER 0  — FOUNDATION (CURRENT IMPLEMENTATION)         │
│ LAYER -1 — CONSTITUTION (IMMUTABLE BOUNDARIES)         │
└────────────────────────────────────────────────────────┘
```
