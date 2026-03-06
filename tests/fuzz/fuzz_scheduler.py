#!/usr/bin/env python3
"""
Property-based fuzz tester for the DAG task scheduler.

Generates random valid scheduler programs and verifies structural invariants
on the output, without needing pre-computed expected outputs.

Usage:
    python3 tests/fuzz/fuzz_scheduler.py [--runs N] [--seed S] [--verbose]
"""

import argparse
import os
import random
import re
import subprocess
import sys
import time

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SOLUTION = os.path.join(PROJECT_DIR, "src", "scheduler.py")
if not os.path.exists(SOLUTION):
    SOLUTION = os.path.join(PROJECT_DIR, "starter", "python", "solution.py")

# ── Program generator ─────────────────────────────────────────────────────

def generate_program(rng, *, allow_cycles=False):
    """Generate a random scheduler program. Returns (program_text, metadata)."""
    num_tasks = rng.randint(1, 50)
    task_ids = [f"t{i:03d}" for i in range(num_tasks)]
    rng.shuffle(task_ids)

    tasks = {}
    for tid in task_ids:
        dur = rng.randint(1, 10)
        pri = rng.choice([0, 0, 0, 1, 5, 10, 20])
        tasks[tid] = {"duration": dur, "priority": pri}

    topo_order = list(task_ids)
    rng.shuffle(topo_order)
    position = {tid: i for i, tid in enumerate(topo_order)}

    deps = {}
    num_deps = rng.randint(0, min(num_tasks * 2, 100))
    for _ in range(num_deps):
        a = rng.choice(task_ids)
        b = rng.choice(task_ids)
        if a == b:
            continue
        if allow_cycles or position[b] < position[a]:
            deps.setdefault(a, set()).add(b)

    num_resources = rng.randint(0, 5)
    resources = {}
    for i in range(num_resources):
        rname = f"r{i}"
        resources[rname] = rng.randint(1, 10)

    reqs = {}
    if resources:
        for tid in task_ids:
            if rng.random() < 0.4:
                rname = rng.choice(list(resources.keys()))
                amt = rng.randint(1, resources[rname])
                reqs.setdefault(tid, {})[rname] = amt

    fail_set = set()
    retry_map = {}
    for tid in task_ids:
        if rng.random() < 0.15:
            fail_set.add(tid)
            if rng.random() < 0.6:
                retry_map[tid] = rng.randint(0, 3)

    lines = []
    for tid, info in tasks.items():
        if info["priority"] != 0:
            lines.append(f"TASK {tid} {info['duration']} {info['priority']}")
        else:
            lines.append(f"TASK {tid} {info['duration']}")
    for rname, cap in resources.items():
        lines.append(f"RESOURCE {rname} {cap}")
    for tid, dep_set in deps.items():
        for d in dep_set:
            lines.append(f"DEPEND {tid} {d}")
    for tid, req_map in reqs.items():
        for rname, amt in req_map.items():
            lines.append(f"REQUIRE {tid} {rname} {amt}")
    for tid in fail_set:
        lines.append(f"FAIL {tid}")
    for tid, cnt in retry_map.items():
        lines.append(f"RETRY {tid} {cnt}")
    lines.append("RUN")
    lines.append("END")

    meta = {
        "tasks": tasks,
        "deps": deps,
        "resources": resources,
        "reqs": reqs,
        "fail_set": fail_set,
        "retry_map": retry_map,
    }
    return "\n".join(lines) + "\n", meta


# ── Output parser ─────────────────────────────────────────────────────────

def parse_output(output):
    """Parse scheduler output into structured events."""
    events = []
    for line in output.strip().split("\n"):
        if not line:
            continue
        if line.startswith("CYCLE DETECTED"):
            events.append({"type": "CYCLE", "raw": line})
            continue
        parts = line.split()
        if len(parts) >= 3 and parts[0] == "STARTED":
            events.append({"type": "STARTED", "task": parts[1], "tick": int(parts[2])})
        elif len(parts) >= 3 and parts[0] == "COMPLETED":
            events.append({"type": "COMPLETED", "task": parts[1], "tick": int(parts[2])})
        elif len(parts) >= 4 and parts[0] == "FAILED":
            events.append({"type": "FAILED", "task": parts[1], "tick": int(parts[2]), "reason": parts[3]})
        else:
            events.append({"type": "UNKNOWN", "raw": line})
    return events


# ── Invariant checkers ────────────────────────────────────────────────────

def check_invariants(events, meta):
    """Check all invariants. Returns list of violation strings (empty = pass)."""
    violations = []
    tasks = meta["tasks"]
    deps = meta["deps"]
    resources = meta["resources"]
    reqs = meta["reqs"]
    fail_set = meta["fail_set"]
    retry_map = meta["retry_map"]

    if any(e["type"] == "CYCLE" for e in events):
        return violations

    completed_at = {}
    failed_tasks = {}
    started_tasks = {}
    start_events = []

    for e in events:
        tid = e.get("task")
        if e["type"] == "STARTED":
            started_tasks[tid] = e["tick"]
            start_events.append(e)
        elif e["type"] == "COMPLETED":
            completed_at[tid] = e["tick"]
        elif e["type"] == "FAILED":
            if e["reason"] == "failed":
                failed_tasks[tid] = "failed"
            elif e["reason"] == "dependency_failed":
                failed_tasks[tid] = "dependency_failed"

    # INV-1: No task is both COMPLETED and permanently FAILED
    for tid in completed_at:
        if tid in failed_tasks and failed_tasks[tid] != "failed":
            violations.append(f"INV-1: {tid} is both COMPLETED and permanently FAILED")
    # (A task with FAIL+RETRY can appear in both started/failed then completed — that's a retry)

    # INV-2: Task never starts before all dependencies complete
    for e in start_events:
        tid = e["task"]
        tick = e["tick"]
        for dep in deps.get(tid, set()):
            if dep in tasks:
                if dep not in completed_at:
                    if dep not in failed_tasks:
                        pass  # dep might still be pending
                elif completed_at[dep] > tick:
                    violations.append(
                        f"INV-2: {tid} started at tick {tick} before dep {dep} "
                        f"completed at {completed_at[dep]}"
                    )

    # INV-3: Resource capacity never exceeded
    if resources:
        usage_timeline = {}
        task_intervals = {}
        for e in events:
            tid = e.get("task")
            tick = e.get("tick")
            if e["type"] == "STARTED" and tid in completed_at:
                task_intervals[tid] = (tick, completed_at[tid])

        max_tick = max((t for _, t in task_intervals.values()), default=0)
        for tick in range(max_tick + 1):
            usage = {r: 0 for r in resources}
            for tid, (s, e_tick) in task_intervals.items():
                if s <= tick < e_tick:
                    for rname, amt in reqs.get(tid, {}).items():
                        if rname in resources:
                            usage[rname] += amt
            for rname, used in usage.items():
                if used > resources[rname]:
                    violations.append(
                        f"INV-3: Resource {rname} exceeded at tick {tick}: "
                        f"{used}/{resources[rname]}"
                    )

    # INV-4: Retries never exceed limit
    start_counts = {}
    for e in events:
        if e["type"] == "STARTED":
            tid = e["task"]
            start_counts[tid] = start_counts.get(tid, 0) + 1
    for tid, count in start_counts.items():
        max_starts = 1 + retry_map.get(tid, 0) if tid in fail_set else 1
        if count > max_starts:
            violations.append(
                f"INV-4: {tid} started {count} times, max allowed {max_starts}"
            )

    # INV-5: Cascade only affects dependents of failed tasks
    all_failed_sources = set()
    for tid, reason in failed_tasks.items():
        if reason == "failed":
            all_failed_sources.add(tid)

    def transitive_dependents(sources, dep_graph, all_tasks):
        reachable = set()
        queue = list(sources)
        forward = {}
        for t, d_set in dep_graph.items():
            for d in d_set:
                forward.setdefault(d, set()).add(t)
        while queue:
            n = queue.pop()
            for child in forward.get(n, set()):
                if child in all_tasks and child not in reachable:
                    reachable.add(child)
                    queue.append(child)
        return reachable

    if all_failed_sources:
        allowed_cascade = transitive_dependents(all_failed_sources, deps, set(tasks.keys()))
        for tid, reason in failed_tasks.items():
            if reason == "dependency_failed" and tid not in allowed_cascade:
                violations.append(
                    f"INV-5: {tid} dependency_failed but is not a transitive "
                    f"dependent of any failed task"
                )

    # INV-6: Deterministic ordering — COMPLETED events at same tick are alphabetical
    tick_completed = {}
    for e in events:
        if e["type"] == "COMPLETED":
            tick_completed.setdefault(e["tick"], []).append(e["task"])
    for tick, tids in tick_completed.items():
        if tids != sorted(tids):
            violations.append(
                f"INV-6: COMPLETED events at tick {tick} not alphabetical: {tids}"
            )

    # INV-7: Cascade FAILED events at same tick are alphabetical
    tick_cascade = {}
    for e in events:
        if e["type"] == "FAILED" and e.get("reason") == "dependency_failed":
            tick_cascade.setdefault(e["tick"], []).append(e["task"])
    for tick, tids in tick_cascade.items():
        if tids != sorted(tids):
            violations.append(
                f"INV-7: Cascade FAILED events at tick {tick} not alphabetical: {tids}"
            )

    return violations


# ── Runner ────────────────────────────────────────────────────────────────

def run_program(program_text):
    """Run the scheduler on a program and return stdout."""
    result = subprocess.run(
        [sys.executable, SOLUTION],
        input=program_text,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return result.stdout


def run_fuzz(num_runs, seed, verbose):
    rng = random.Random(seed)
    passed = 0
    failed = 0
    errors = 0
    t0 = time.time()

    for i in range(num_runs):
        run_seed = rng.randint(0, 2**32)
        run_rng = random.Random(run_seed)
        try:
            program, meta = generate_program(run_rng)
            output = run_program(program)
            events = parse_output(output)
            violations = check_invariants(events, meta)

            if violations:
                failed += 1
                print(f"FAIL  run {i+1} (seed={run_seed})")
                for v in violations:
                    print(f"  {v}")
                if verbose:
                    print("  --- program ---")
                    for line in program.strip().split("\n"):
                        print(f"    {line}")
                    print("  --- output ---")
                    for line in output.strip().split("\n"):
                        print(f"    {line}")
            else:
                passed += 1
                if verbose:
                    print(f"PASS  run {i+1} (seed={run_seed})")

        except subprocess.TimeoutExpired:
            errors += 1
            print(f"TIMEOUT  run {i+1} (seed={run_seed})")
        except Exception as exc:
            errors += 1
            print(f"ERROR  run {i+1} (seed={run_seed}): {exc}")

        if (i + 1) % 100 == 0 and not verbose:
            elapsed = time.time() - t0
            print(f"  ... {i+1}/{num_runs} ({passed} pass, {failed} fail, "
                  f"{errors} error, {elapsed:.1f}s)")

    elapsed = time.time() - t0
    print()
    print(f"Fuzz results: {passed} passed, {failed} failed, {errors} errors "
          f"out of {num_runs} runs ({elapsed:.1f}s)")
    print(f"Seed: {seed}")
    return failed + errors


def main():
    parser = argparse.ArgumentParser(description="Fuzz test the scheduler")
    parser.add_argument("--runs", type=int, default=1000, help="Number of runs")
    parser.add_argument("--seed", type=int, default=42, help="RNG seed")
    parser.add_argument("--verbose", action="store_true", help="Print every result")
    args = parser.parse_args()

    failures = run_fuzz(args.runs, args.seed, args.verbose)
    sys.exit(1 if failures > 0 else 0)


if __name__ == "__main__":
    main()
