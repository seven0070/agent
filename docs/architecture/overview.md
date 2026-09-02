# Architecture Overview

This document describes the high-level architecture of the self-evolving local-first AI agent system.

## System Objective
The goal is a local-first AI agent framework capable of controlled metamorphosis. The system can safely update its internal capabilities, planning strategies, skill definitions, memory routing, and agent compositions through an empirical, test-driven evolution pipeline while preserving strict constitutional boundaries.

## Key Architectural Principles

1. **Layered Construction**: Built sequentially layer by layer. Final architecture is Layers -1 through 10.
2. **Layer -1 Constitution**: Immutable constraints and safety boundaries that cannot be altered autonomously.
3. **Evolution Controller Control Plane**: An external governance control plane sitting beside the agent execution plane.
4. **AgentScope Foundation**: Built on top of AgentScope as the core agent and multi-agent infrastructure.
5. **Jcode Subsystem**: Specialized coding engine for inspecting, editing, and verifying workspace artifacts.
6. **Explicit Versioning**: All candidate mutations are versioned assets subject to sandboxed testing and baseline evaluation before promotion.

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
│ LAYER 10 — UI / DESKTOP (IMPLEMENTED)                  │
│ LAYER 9  — EVOLUTION CONTROL PLANE (IMPLEMENTED)       │
│ LAYER 8  — EVALUATION / VERIFICATION (IMPLEMENTED)     │
│ LAYER 7  — RUNTIME / SANDBOX (IMPLEMENTED)             │
│ LAYER 6  — JCODE CODING ENGINE (IMPLEMENTED)           │
│ LAYER 5  — PLANNING / ORCHESTRATION (IMPLEMENTED)      │
│ LAYER 4  — TOOLS / SKILLS / MCP (IMPLEMENTED)          │
│ LAYER 3  — MEMORY / RAG (IMPLEMENTED)                  │
│ LAYER 2  — INTELLIGENCE / MODELS (IMPLEMENTED)         │
│ LAYER 1  — AGENT CORE (IMPLEMENTED)                    │
│ LAYER 0  — FOUNDATION (IMPLEMENTED)                    │
│ LAYER -1 — CONSTITUTION (IMMUTABLE BOUNDARIES)         │
└────────────────────────────────────────────────────────┘
```
