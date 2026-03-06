# Architecture

## System Overview

The scheduler is a deterministic, tick-based simulation engine that executes a DAG of tasks subject to dependency constraints, resource limits, priority ordering, failure injection, and retry logic.

```
stdin ──► Command Parser ──► Batch Accumulator ──► RUN trigger
                                                       │
                                         ┌─────────────┼─────────────┐
                                         ▼             ▼             ▼
                                   Cycle Detector  Topo Sorter  Simulation Engine
                                         │             │             │
                                         ▼             ▼             ▼
                                    CYCLE DETECTED   ORDER      Event Stream
                                                                     │
                                                              ┌──────┼──────┐
                                                              ▼      ▼      ▼
                                                          STARTED COMPLETED FAILED
                                                              │
                                                              ▼
                                                        stdout + trace.json
```

## Module Breakdown

### Command Parser (`main()`)
Reads commands from stdin line-by-line. Accumulates batch state (tasks, dependencies, resources, requirements, FAIL flags, RETRY counts) until a `RUN` command triggers execution.

### Batch Accumulator
State is accumulated per-batch and cleared after each `RUN`. This ensures batch isolation — the second `RUN` cannot see definitions from the first.

### Cycle Detector (`find_cycle`)
Three-phase algorithm:
1. **Quick check**: Iterative DFS with 3-color marking (`_has_cycle`)
2. **SCC extraction**: Iterative Tarjan's algorithm (`_find_cycle_nodes_tarjan`)
3. **Lex-smallest cycle**: DFS from smallest cycle node with sorted neighbors (`_find_lex_cycle_from`)

### Topological Sorter (`topological_order`)
Kahn's algorithm using a min-heap for alphabetical tie-breaking. Produces the deterministic topological ordering returned by `ORDER`.

### Simulation Engine (`run_batch`)
Tick-by-tick simulation with three phases per tick:

1. **Phase 1 — Completions**: Tasks whose end tick matches the current tick are completed. Resources are released. `COMPLETED` events emitted in alphabetical order.

2. **Phase 2 — Scheduling**: Ready tasks (all deps completed, not failed/running) are sorted by `(-priority, name)`. For each:
   - **FAIL tasks**: Emit `STARTED` + `FAILED`. If retries remain, attempt immediate re-acquisition of resources. If unavailable, defer to next tick.
   - **Normal tasks**: Acquire resources if available, emit `STARTED`.

3. **Phase 3 — Cascade**: BFS from permanently-failed tasks through the forward dependency graph. Dependents that are not already completed/running/failed are cascade-failed. `FAILED dependency_failed` events emitted in alphabetical order.

### Resource Manager (`_can_acquire`, `_acquire`, `_update_peak`)
Tracks available resource capacity. Atomic check-and-acquire pattern: a task only starts if **all** its resource requirements can be simultaneously satisfied.

### Termination Conditions
- All tasks completed or failed
- No tasks running and no new tasks were scheduled (deadlock / resource starvation)

## Data Flow

```
Input Commands → Batch State → Validation → Cycle Check → Simulation → Events → stdout
                                                    │                       │
                                                    └── ORDER ──────────────┘
                                                                            │
                                                    STATUS queries ─────────┘
```

## Trace & Metrics (Optional)

When `--trace` is passed, every event is recorded as structured JSON and written to `trace.json` after `END`.

When `--metrics` is passed, per-batch metrics (ticks, completed, failed, retries, peak resource usage, decisions) are written to `metrics.json`.

Both flags are off by default and do not affect stdout output.
