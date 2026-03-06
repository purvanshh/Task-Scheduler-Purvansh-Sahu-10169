# Design Decisions

## 1. Iterative vs Recursive Algorithms

**Decision**: All graph algorithms (DFS cycle check, Tarjan's SCC, lex-cycle DFS) are iterative.

**Rationale**: Python's default recursion limit is 1000. Deep dependency chains (500+ tasks) would cause `RecursionError`. While `sys.setrecursionlimit` can be increased, iterative implementations are more robust and avoid stack overflow entirely.

## 2. Atomic Resource Acquisition

**Decision**: A task's resources are checked and acquired atomically (all-or-nothing).

**Rationale**: Partial acquisition (taking some resources then blocking on others) would create deadlocks in the general case. By requiring all resources to be simultaneously available, we guarantee that any running task will eventually complete and release its resources.

## 3. FAIL Semantics — Instant Failure on First Attempt

**Decision**: A FAIL-flagged task emits `STARTED` and `FAILED` events in the same tick without consuming resources for the failed attempt.

**Rationale**: The specification defines FAIL as marking a task to fail on its "first execution attempt." The failed attempt is instantaneous — it does not hold resources. Only the retry (if any) acquires resources and runs for the task's duration.

## 4. Deferred Retry When Resources Unavailable

**Decision**: If a FAIL task has retries remaining but cannot acquire resources for the retry, it is deferred (not marked as permanently failed). It will be reconsidered in subsequent ticks when resources may become available.

**Rationale**: Immediately failing a task because resources happen to be busy at the retry moment would violate the retry contract. The task is logically "waiting to retry" and should get another chance when resources free up.

## 5. Deterministic Event Ordering

**Decision**: Strict ordering within each tick:
1. COMPLETED events (alphabetical)
2. STARTED/FAILED events from scheduling (priority order, with inline FAIL events)
3. Cascade FAILED events (alphabetical)

**Rationale**: The specification requires deterministic, reproducible output. Without a defined ordering for events at the same tick, different implementations could produce different (but semantically equivalent) outputs, making automated grading impossible.

## 6. Batch Isolation

**Decision**: Each `RUN` command processes only definitions accumulated since the last `RUN`. All batch state is cleared afterward.

**Rationale**: This matches the specification's batch semantics and prevents state leakage between independent simulation runs within the same session.

## 7. Ignoring Invalid References

**Decision**: Dependencies on undefined tasks and requirements for undefined resources are silently ignored.

**Rationale**: The specification does not define error behavior for these cases. Silently ignoring them is the most forgiving approach and matches the expected test outputs.

## 8. Duplicate Task Replacement

**Decision**: If `TASK a` is defined twice, the second definition replaces the first.

**Rationale**: The specification does not explicitly forbid duplicate definitions. Replacement semantics are simple, predictable, and consistent with the expected test outputs.

## 9. Termination on No Running Tasks

**Decision**: The simulation breaks when `running` is empty after scheduling.

**Rationale**: If no tasks are running and none could be scheduled (due to resource impossibility or all tasks being done/failed), no future tick can change the state. This prevents infinite loops when tasks require more resources than exist.

## 10. Optional Trace and Metrics via CLI Flags

**Decision**: `--trace` and `--metrics` are opt-in flags that write to `trace.json` and `metrics.json` respectively, without affecting stdout.

**Rationale**: The primary output format is strictly defined by the specification. Trace and metrics are diagnostic tools that should not interfere with correctness testing.
