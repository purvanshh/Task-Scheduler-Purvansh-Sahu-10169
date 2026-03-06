# Algorithms

## Cycle Detection

### Problem
Given a directed graph of task dependencies, detect whether a cycle exists. If so, report the lexicographically smallest cycle starting from the lexicographically smallest node.

### Algorithm (3-phase)

**Phase 1 — Quick cycle check**
Iterative DFS with 3-color marking (WHITE → GRAY → BLACK). A back-edge (edge to a GRAY node) indicates a cycle. Time: O(V + E).

**Phase 2 — SCC extraction**
Iterative Tarjan's algorithm identifies all strongly connected components. Nodes in SCCs of size > 1 are cycle participants. Self-loops (SCCs of size 1 with a self-edge) are also included. Time: O(V + E).

**Phase 3 — Lexicographically smallest cycle**
Starting from the smallest node in the cycle-node set, perform DFS with neighbors visited in sorted order. The first path that returns to the start node is the lexicographically smallest cycle. This works because sorted neighbor traversal explores lexicographically smaller extensions first.

### Correctness Argument
- Tarjan's correctly identifies all cycle-participating nodes
- Sorted DFS from the smallest such node explores lex-smaller paths before lex-larger ones
- The first cycle found is therefore the lex-smallest

## Topological Sort

### Problem
Produce a total ordering of tasks consistent with the dependency DAG, breaking ties alphabetically.

### Algorithm — Kahn's with min-heap
1. Compute in-degrees for all nodes
2. Initialize a min-heap with all zero-in-degree nodes
3. Repeatedly extract the minimum (alphabetically first), append to output, decrement in-degrees of successors, push newly zero-in-degree nodes

Time: O(V log V + E). The min-heap ensures alphabetical tie-breaking.

## Priority Scheduling

### Problem
Among ready tasks (all dependencies satisfied, not failed/running), decide execution order.

### Algorithm
Sort ready tasks by `(-priority, task_id)`. Higher priority first; alphabetical tie-breaking among equal priorities. Tasks are considered in this order for resource acquisition.

## Resource Allocation

### Problem
Tasks may require units from shared resource pools. A task can only start if all its requirements are simultaneously satisfiable.

### Algorithm — Atomic check-and-acquire
```
can_acquire(task):
    for each (resource, amount) in requirements[task]:
        if available[resource] < amount: return False
    return True

acquire(task):
    for each (resource, amount) in requirements[task]:
        available[resource] -= amount
```

Resources are released when a task completes. This all-or-nothing approach prevents partial allocation deadlocks.

## Failure Cascade

### Problem
When a task permanently fails, all transitive dependents must also fail.

### Algorithm — BFS cascade
From each permanently-failed task, BFS through the forward dependency graph. Any reachable task that is not already completed, running, or failed is marked as `dependency_failed`. Cascade failures within a single tick are collected and emitted in alphabetical order.

## Deadlock Detection

### Problem
Detect when no further progress is possible (e.g., a task requires more resources than total capacity).

### Algorithm
After all scheduling attempts in a tick, if no tasks are currently running, the simulation terminates. Tasks that could not be scheduled remain PENDING.
