import sys
import json
from collections import defaultdict, deque
import heapq

sys.setrecursionlimit(100000)

TRACE_ENABLED = "--trace" in sys.argv
METRICS_ENABLED = "--metrics" in sys.argv


def main():
    tasks = {}
    dependencies = defaultdict(set)
    resources = {}
    requirements = defaultdict(dict)
    fail_tasks = set()
    retry_counts = {}

    last_results = {}
    last_order = None
    last_cycle = None

    all_trace_events = []
    all_metrics = []

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        parts = line.split()
        command = parts[0]

        if command == "TASK":
            tid = parts[1]
            duration = int(parts[2])
            priority = int(parts[3]) if len(parts) > 3 else 0
            tasks[tid] = {"duration": duration, "priority": priority}

        elif command == "DEPEND":
            dependencies[parts[1]].add(parts[2])

        elif command == "RESOURCE":
            resources[parts[1]] = int(parts[2])

        elif command == "REQUIRE":
            requirements[parts[1]][parts[2]] = int(parts[3])

        elif command == "RUN":
            last_results, last_order, last_cycle, trace, metrics = run_batch(
                tasks, dependencies, resources, requirements, fail_tasks, retry_counts
            )
            all_trace_events.extend(trace)
            all_metrics.append(metrics)
            tasks = {}
            dependencies = defaultdict(set)
            resources = {}
            requirements = defaultdict(dict)
            fail_tasks = set()
            retry_counts = {}

        elif command == "STATUS":
            tid = parts[1]
            if tid not in last_results:
                print("UNKNOWN TASK")
            else:
                info = last_results[tid]
                if info["status"] == "COMPLETED":
                    print(f"{tid}: COMPLETED {info['start']} {info['end']}")
                elif info["status"] == "FAILED":
                    print(f"{tid}: FAILED {info['reason']}")
                else:
                    print(f"{tid}: PENDING")

        elif command == "ORDER":
            if last_cycle:
                print("CYCLE DETECTED")
            elif last_order is not None and last_order:
                print("ORDER: " + " ".join(last_order))

        elif command == "FAIL":
            fail_tasks.add(parts[1])

        elif command == "RETRY":
            retry_counts[parts[1]] = int(parts[2])

        elif command == "END":
            break

    if TRACE_ENABLED:
        trace_out = {"events": all_trace_events}
        with open("trace.json", "w") as f:
            json.dump(trace_out, f, indent=2)

    if METRICS_ENABLED:
        with open("metrics.json", "w") as f:
            json.dump(all_metrics, f, indent=2)


# Cycle detection

def _has_cycle(all_nodes, graph, node_set):
    """Iterative DFS cycle detection."""
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {n: WHITE for n in all_nodes}

    for start in all_nodes:
        if color[start] != WHITE:
            continue
        stack = [(start, False)]
        while stack:
            node, returning = stack.pop()
            if returning:
                color[node] = BLACK
                continue
            if color[node] == GRAY:
                continue
            color[node] = GRAY
            stack.append((node, True))
            for nb in graph.get(node, []):
                if nb not in node_set:
                    continue
                if color[nb] == GRAY:
                    return True
                if color[nb] == WHITE:
                    stack.append((nb, False))
    return False


def _find_cycle_nodes_tarjan(all_nodes, graph, node_set):
    """Iterative Tarjan's SCC — return nodes in SCCs of size > 1, or
    single-node SCCs that have a self-loop."""
    idx_counter = 0
    index = {}
    low = {}
    on_stack = set()
    stack = []
    result = set()

    self_loops = set()
    for v in all_nodes:
        if v in graph.get(v, set()):
            self_loops.add(v)

    ENTER, PROCESS_CHILD, FINISH = 0, 1, 2

    for root in all_nodes:
        if root in index:
            continue
        call_stack = [(ENTER, root, None, iter(sorted(graph.get(root, []))))]

        while call_stack:
            action, v, child, children = call_stack[-1]

            if action == ENTER:
                index[v] = low[v] = idx_counter
                idx_counter += 1
                stack.append(v)
                on_stack.add(v)
                call_stack[-1] = (PROCESS_CHILD, v, None, children)

            elif action == PROCESS_CHILD:
                if child is not None:
                    low[v] = min(low[v], low[child])

                found_next = False
                for w in children:
                    if w not in node_set:
                        continue
                    if w not in index:
                        call_stack[-1] = (PROCESS_CHILD, v, w, children)
                        call_stack.append((ENTER, w, None, iter(sorted(graph.get(w, [])))))
                        found_next = True
                        break
                    elif w in on_stack:
                        low[v] = min(low[v], index[w])

                if not found_next:
                    call_stack[-1] = (FINISH, v, None, None)

            elif action == FINISH:
                if low[v] == index[v]:
                    scc = []
                    while True:
                        w = stack.pop()
                        on_stack.discard(w)
                        scc.append(w)
                        if w == v:
                            break
                    if len(scc) > 1:
                        result.update(scc)
                    elif len(scc) == 1 and scc[0] in self_loops:
                        result.add(scc[0])
                call_stack.pop()

    return result


def _find_lex_cycle_from(start, graph, cycle_nodes):
    """DFS from start, neighbors in sorted order. Return first cycle back to start."""
    if start in graph.get(start, set()):
        return [start, start]

    stack = [(start, [start])]
    visited = set()

    while stack:
        node, path = stack.pop()
        neighbors = sorted(graph.get(node, []))
        for nb in reversed(neighbors):
            if nb == start and len(path) > 1:
                return path + [start]
            if nb in cycle_nodes and nb not in set(path):
                state = (nb, tuple(path))
                if state not in visited:
                    visited.add(state)
                    stack.append((nb, path + [nb]))
    return None


def find_cycle(tasks, graph):
    """Find the lexicographically smallest cycle in the dependency graph."""
    all_nodes = sorted(tasks.keys())
    node_set = set(all_nodes)

    if not _has_cycle(all_nodes, graph, node_set):
        return None

    cycle_nodes = _find_cycle_nodes_tarjan(all_nodes, graph, node_set)

    for start in sorted(cycle_nodes):
        result = _find_lex_cycle_from(start, graph, cycle_nodes)
        if result is not None:
            return result
    return None


# Topological sort (Kahn's algorithm)

def topological_order(tasks, graph):
    all_tasks = set(tasks.keys())
    forward = defaultdict(set)
    in_degree = {tid: 0 for tid in all_tasks}

    for task_id, deps in graph.items():
        if task_id in all_tasks:
            for dep_id in deps:
                if dep_id in all_tasks:
                    forward[dep_id].add(task_id)
                    in_degree[task_id] += 1

    queue = []
    for tid in all_tasks:
        if in_degree[tid] == 0:
            heapq.heappush(queue, tid)

    order = []
    while queue:
        node = heapq.heappop(queue)
        order.append(node)
        for nb in forward[node]:
            in_degree[nb] -= 1
            if in_degree[nb] == 0:
                heapq.heappush(queue, nb)
    return order


# Simulation

def run_batch(tasks, dependencies, resources, requirements, fail_tasks, retry_counts):
    trace_events = []
    metrics = {
        "total_ticks": 0,
        "tasks_completed": 0,
        "tasks_failed": 0,
        "retry_attempts": 0,
        "peak_resource_usage": {},
        "scheduler_decisions": 0,
        "total_tasks": len(tasks),
    }

    if not tasks:
        return {}, None, None, trace_events, metrics

    valid_deps = defaultdict(set)
    for tid, deps in dependencies.items():
        if tid in tasks:
            for d in deps:
                if d in tasks:
                    valid_deps[tid].add(d)

    valid_reqs = defaultdict(dict)
    for tid, reqs in requirements.items():
        if tid in tasks:
            for rname, amt in reqs.items():
                if rname in resources:
                    valid_reqs[tid][rname] = amt

    cycle = find_cycle(tasks, valid_deps)
    if cycle is not None:
        print("CYCLE DETECTED: " + " -> ".join(cycle))
        results = {tid: {"status": "PENDING"} for tid in tasks}
        return results, None, True, trace_events, metrics

    topo = topological_order(tasks, valid_deps)

    results = {tid: {"status": "PENDING"} for tid in tasks}
    completed = set()
    failed = set()
    running = {}
    res_avail = dict(resources)
    res_capacity = dict(resources)
    retries_left = {tid: retry_counts.get(tid, 0) for tid in tasks}
    fail_consumed = set()

    peak_usage = {r: 0 for r in resources}

    dependents = defaultdict(set)
    for tid, deps in valid_deps.items():
        for d in deps:
            dependents[d].add(tid)

    tick = 0
    while True:
        output_lines = []

        finishing = sorted(tid for tid, info in running.items() if info["end"] == tick)
        for tid in finishing:
            completed.add(tid)
            results[tid] = {"status": "COMPLETED", "start": running[tid]["start"], "end": tick}
            output_lines.append(f"COMPLETED {tid} {tick}")
            trace_events.append({"tick": tick, "type": "COMPLETED", "task": tid})
            metrics["tasks_completed"] += 1
            for rname, amt in valid_reqs.get(tid, {}).items():
                res_avail[rname] += amt
            del running[tid]

        ready = []
        for tid in tasks:
            if tid in completed or tid in failed or tid in running:
                continue
            if all(d in completed for d in valid_deps.get(tid, set())):
                ready.append(tid)

        ready.sort(key=lambda t: (-tasks[t]["priority"], t))

        cascade_sources = []

        for tid in ready:
            metrics["scheduler_decisions"] += 1
            if tid in fail_tasks and tid not in fail_consumed:
                fail_consumed.add(tid)

                output_lines.append(f"STARTED {tid} {tick}")
                output_lines.append(f"FAILED {tid} {tick} failed")
                trace_events.append({"tick": tick, "type": "STARTED", "task": tid})
                trace_events.append({"tick": tick, "type": "FAILED", "task": tid, "reason": "failed"})

                if retries_left[tid] > 0:
                    retries_left[tid] -= 1
                    metrics["retry_attempts"] += 1
                    if _can_acquire(tid, valid_reqs, res_avail):
                        _acquire(tid, valid_reqs, res_avail)
                        running[tid] = {"start": tick, "end": tick + tasks[tid]["duration"]}
                        output_lines.append(f"STARTED {tid} {tick}")
                        trace_events.append({"tick": tick, "type": "STARTED", "task": tid})
                        _update_peak(peak_usage, res_avail, res_capacity)
                else:
                    failed.add(tid)
                    results[tid] = {"status": "FAILED", "reason": "failed"}
                    metrics["tasks_failed"] += 1
                    cascade_sources.append(tid)
            else:
                if _can_acquire(tid, valid_reqs, res_avail):
                    _acquire(tid, valid_reqs, res_avail)
                    running[tid] = {"start": tick, "end": tick + tasks[tid]["duration"]}
                    output_lines.append(f"STARTED {tid} {tick}")
                    trace_events.append({"tick": tick, "type": "STARTED", "task": tid})
                    _update_peak(peak_usage, res_avail, res_capacity)

        cascade_queue = deque()
        for src in cascade_sources:
            for dep_tid in dependents.get(src, set()):
                if dep_tid not in failed and dep_tid not in completed and dep_tid not in running:
                    cascade_queue.append(dep_tid)

        cascade_failed = []
        while cascade_queue:
            dep_tid = cascade_queue.popleft()
            if dep_tid in failed or dep_tid in completed:
                continue
            failed.add(dep_tid)
            results[dep_tid] = {"status": "FAILED", "reason": "dependency_failed"}
            cascade_failed.append(dep_tid)
            for further in dependents.get(dep_tid, set()):
                if further not in failed and further not in completed and further not in running:
                    cascade_queue.append(further)

        cascade_failed.sort()
        for dep_tid in cascade_failed:
            output_lines.append(f"FAILED {dep_tid} {tick} dependency_failed")
            trace_events.append({"tick": tick, "type": "FAILED", "task": dep_tid, "reason": "dependency_failed"})
            metrics["tasks_failed"] += 1

        for line in output_lines:
            print(line)

        if all(tid in completed or tid in failed for tid in tasks):
            break

        if not running:
            break

        tick += 1

    metrics["total_ticks"] = tick + 1 if (completed or failed) else 0
    metrics["peak_resource_usage"] = peak_usage
    return results, topo, None, trace_events, metrics


def _update_peak(peak_usage, res_avail, res_capacity):
    for rname in res_capacity:
        used = res_capacity[rname] - res_avail[rname]
        if used > peak_usage.get(rname, 0):
            peak_usage[rname] = used


def _can_acquire(tid, valid_reqs, res_avail):
    for rname, amt in valid_reqs.get(tid, {}).items():
        if res_avail.get(rname, 0) < amt:
            return False
    return True


def _acquire(tid, valid_reqs, res_avail):
    for rname, amt in valid_reqs.get(tid, {}).items():
        res_avail[rname] -= amt


if __name__ == "__main__":
    main()
