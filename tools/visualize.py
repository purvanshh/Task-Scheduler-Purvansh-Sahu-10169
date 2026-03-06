#!/usr/bin/env python3
"""
Scheduler visualization tools.

Generates three types of visualizations from a scheduler input file:
  1. Dependency graph (Graphviz DOT → PNG)
  2. Execution timeline (ASCII + optional matplotlib)
  3. Resource usage over time (ASCII + optional matplotlib)

Usage:
    python3 tools/visualize.py <input_file> [--format ascii|png]

Requires:
    - graphviz (pip install graphviz) for PNG dependency graph
    - matplotlib (pip install matplotlib) for PNG timeline/resource charts
    Both are optional; ASCII output works with stdlib only.
"""

import argparse
import json
import os
import subprocess
import sys
from collections import defaultdict

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOLUTION = os.path.join(PROJECT_DIR, "src", "scheduler.py")
if not os.path.exists(SOLUTION):
    SOLUTION = os.path.join(PROJECT_DIR, "starter", "python", "solution.py")


def parse_input(path):
    """Parse a scheduler input file into structured data."""
    tasks = {}
    deps = defaultdict(set)
    resources = {}
    reqs = defaultdict(dict)
    fail_set = set()
    retry_map = {}

    with open(path) as f:
        for line in f:
            parts = line.strip().split()
            if not parts:
                continue
            cmd = parts[0]
            if cmd == "TASK":
                tid = parts[1]
                dur = int(parts[2])
                pri = int(parts[3]) if len(parts) > 3 else 0
                tasks[tid] = {"duration": dur, "priority": pri}
            elif cmd == "DEPEND":
                deps[parts[1]].add(parts[2])
            elif cmd == "RESOURCE":
                resources[parts[1]] = int(parts[2])
            elif cmd == "REQUIRE":
                reqs[parts[1]][parts[2]] = int(parts[3])
            elif cmd == "FAIL":
                fail_set.add(parts[1])
            elif cmd == "RETRY":
                retry_map[parts[1]] = int(parts[2])
            elif cmd == "RUN":
                break

    return tasks, deps, resources, reqs, fail_set, retry_map


def run_scheduler(path):
    """Run the scheduler with --trace and return trace events."""
    with open(path) as f:
        input_text = f.read()
    result = subprocess.run(
        [sys.executable, SOLUTION, "--trace", "--metrics"],
        input=input_text,
        capture_output=True,
        text=True,
        timeout=10,
    )
    trace_path = os.path.join(os.getcwd(), "trace.json")
    metrics_path = os.path.join(os.getcwd(), "metrics.json")

    events = []
    metrics = []
    if os.path.exists(trace_path):
        with open(trace_path) as f:
            events = json.load(f)["events"]
    if os.path.exists(metrics_path):
        with open(metrics_path) as f:
            metrics = json.load(f)

    return events, metrics, result.stdout


# ── Dependency graph ──────────────────────────────────────────────────────

def generate_dependency_graph_dot(tasks, deps, fail_set):
    """Generate Graphviz DOT source."""
    lines = ["digraph scheduler {", "    rankdir=TB;", '    node [shape=box, style=filled, fillcolor="#e8f4f8"];']

    for tid, info in sorted(tasks.items()):
        label = f"{tid}\\nd={info['duration']} p={info['priority']}"
        color = "#ffcccc" if tid in fail_set else "#e8f4f8"
        lines.append(f'    "{tid}" [label="{label}", fillcolor="{color}"];')

    for tid, dep_set in sorted(deps.items()):
        for d in sorted(dep_set):
            if d in tasks and tid in tasks:
                lines.append(f'    "{d}" -> "{tid}";')

    lines.append("}")
    return "\n".join(lines)


def render_dependency_graph(tasks, deps, fail_set, output_format):
    dot = generate_dependency_graph_dot(tasks, deps, fail_set)
    dot_path = "dependency_graph.dot"
    with open(dot_path, "w") as f:
        f.write(dot)

    if output_format == "png":
        try:
            subprocess.run(["dot", "-Tpng", dot_path, "-o", "dependency_graph.png"],
                           check=True, capture_output=True)
            print(f"  dependency_graph.png generated")
        except (FileNotFoundError, subprocess.CalledProcessError):
            print(f"  dependency_graph.dot generated (install graphviz for PNG: brew install graphviz)")
    else:
        print(f"  dependency_graph.dot generated")
        print()
        print(dot)


# ── Execution timeline ────────────────────────────────────────────────────

def render_timeline_ascii(events):
    """Render an ASCII execution timeline."""
    task_intervals = {}
    task_failures = {}

    for e in events:
        tid = e["task"]
        tick = e["tick"]
        if e["type"] == "STARTED":
            task_intervals.setdefault(tid, []).append({"start": tick, "end": None})
        elif e["type"] == "COMPLETED":
            for interval in reversed(task_intervals.get(tid, [])):
                if interval["end"] is None:
                    interval["end"] = tick
                    break
        elif e["type"] == "FAILED":
            task_failures[tid] = e.get("reason", "failed")

    all_tasks = sorted(set(e["task"] for e in events))
    max_tick = max((e["tick"] for e in events), default=0) + 1

    if max_tick > 80:
        scale = 80 / max_tick
    else:
        scale = 1.0

    width = int(max_tick * scale) + 1
    print(f"  {'Task':<12s} | Timeline (ticks 0..{max_tick-1})")
    print(f"  {'-'*12}-+-{'-'*width}")

    for tid in all_tasks:
        row = [" "] * width
        for interval in task_intervals.get(tid, []):
            s = int(interval["start"] * scale)
            e = int((interval["end"] or interval["start"]) * scale)
            for i in range(s, min(e + 1, width)):
                row[i] = "#"
        if tid in task_failures:
            marker_tick = 0
            for ev in events:
                if ev["task"] == tid and ev["type"] == "FAILED":
                    marker_tick = ev["tick"]
                    break
            pos = int(marker_tick * scale)
            if pos < width:
                row[pos] = "X"

        suffix = ""
        if tid in task_failures:
            suffix = f"  [{task_failures[tid]}]"
        print(f"  {tid:<12s} | {''.join(row)}{suffix}")

    print(f"  {'-'*12}-+-{'-'*width}")


def render_timeline_png(events):
    """Generate matplotlib timeline chart."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.patches as patches
    except ImportError:
        print("  (install matplotlib for PNG: pip install matplotlib)")
        return

    task_intervals = {}
    task_failures = {}

    for e in events:
        tid = e["task"]
        tick = e["tick"]
        if e["type"] == "STARTED":
            task_intervals.setdefault(tid, []).append({"start": tick, "end": None})
        elif e["type"] == "COMPLETED":
            for interval in reversed(task_intervals.get(tid, [])):
                if interval["end"] is None:
                    interval["end"] = tick
                    break
        elif e["type"] == "FAILED":
            task_failures[tid] = tick

    all_tasks = sorted(set(e["task"] for e in events))
    max_tick = max((e["tick"] for e in events), default=0) + 1

    fig, ax = plt.subplots(figsize=(max(12, max_tick * 0.3), max(4, len(all_tasks) * 0.4)))

    for i, tid in enumerate(all_tasks):
        for interval in task_intervals.get(tid, []):
            start = interval["start"]
            end = interval["end"] or start + 1
            color = "#e74c3c" if tid in task_failures else "#3498db"
            rect = patches.FancyBboxPatch((start, i - 0.3), end - start, 0.6,
                                          boxstyle="round,pad=0.05",
                                          facecolor=color, edgecolor="black", linewidth=0.5)
            ax.add_patch(rect)
        if tid in task_failures:
            ax.plot(task_failures[tid], i, "rx", markersize=10, markeredgewidth=2)

    ax.set_yticks(range(len(all_tasks)))
    ax.set_yticklabels(all_tasks, fontsize=8)
    ax.set_xlabel("Tick")
    ax.set_title("Execution Timeline")
    ax.set_xlim(-0.5, max_tick + 0.5)
    ax.set_ylim(-0.5, len(all_tasks) - 0.5)
    ax.invert_yaxis()
    ax.grid(axis="x", alpha=0.3)
    plt.tight_layout()
    plt.savefig("timeline_chart.png", dpi=150)
    print("  timeline_chart.png generated")


# ── Resource usage ────────────────────────────────────────────────────────

def compute_resource_usage(events, resources, reqs):
    """Compute per-tick resource usage."""
    task_intervals = {}

    for e in events:
        tid = e["task"]
        tick = e["tick"]
        if e["type"] == "STARTED":
            task_intervals.setdefault(tid, []).append({"start": tick, "end": None})
        elif e["type"] == "COMPLETED":
            for interval in reversed(task_intervals.get(tid, [])):
                if interval["end"] is None:
                    interval["end"] = tick
                    break

    max_tick = max((e["tick"] for e in events), default=0) + 1
    usage = {r: [0] * max_tick for r in resources}

    for tid, intervals in task_intervals.items():
        for interval in intervals:
            s = interval["start"]
            e = interval["end"]
            if e is None:
                continue
            for rname, amt in reqs.get(tid, {}).items():
                if rname in resources:
                    for t in range(s, e):
                        if t < max_tick:
                            usage[rname][t] += amt

    return usage, max_tick


def render_resource_ascii(events, resources, reqs):
    if not resources:
        print("  (no resources defined)")
        return

    usage, max_tick = compute_resource_usage(events, resources, reqs)
    if max_tick > 80:
        scale = 80 / max_tick
    else:
        scale = 1.0

    width = int(max_tick * scale) + 1
    print(f"  {'Resource':<12s} | Usage over time (ticks 0..{max_tick-1})")
    print(f"  {'-'*12}-+-{'-'*width}")

    for rname in sorted(resources.keys()):
        cap = resources[rname]
        row = []
        for t in range(width):
            orig_t = int(t / scale) if scale != 0 else t
            if orig_t < max_tick:
                u = usage[rname][orig_t]
                if u == 0:
                    row.append(".")
                elif u >= cap:
                    row.append("!")
                else:
                    row.append(str(min(u, 9)))
            else:
                row.append(".")
        print(f"  {rname:<12s} | {''.join(row)}  (cap={cap})")


def render_resource_png(events, resources, reqs):
    if not resources:
        return

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("  (install matplotlib for PNG: pip install matplotlib)")
        return

    usage, max_tick = compute_resource_usage(events, resources, reqs)

    fig, axes = plt.subplots(len(resources), 1, figsize=(12, 3 * len(resources)), squeeze=False)

    for idx, rname in enumerate(sorted(resources.keys())):
        ax = axes[idx][0]
        cap = resources[rname]
        ticks = list(range(max_tick))
        values = usage[rname][:max_tick]

        ax.bar(ticks, values, color="#3498db", alpha=0.7, width=0.9)
        ax.axhline(y=cap, color="#e74c3c", linestyle="--", label=f"Capacity ({cap})")
        ax.set_ylabel(f"{rname}")
        ax.set_xlabel("Tick")
        ax.legend()
        ax.set_xlim(-0.5, max_tick - 0.5)
        ax.set_ylim(0, cap + 1)
        ax.grid(axis="y", alpha=0.3)

    fig.suptitle("Resource Usage Over Time", fontsize=14)
    plt.tight_layout()
    plt.savefig("resource_usage_chart.png", dpi=150)
    print("  resource_usage_chart.png generated")


# ── Metrics summary ──────────────────────────────────────────────────────

def print_metrics(metrics):
    if not metrics:
        return
    m = metrics[0] if isinstance(metrics, list) else metrics
    print(f"  Total ticks:          {m.get('total_ticks', 'N/A')}")
    print(f"  Tasks completed:      {m.get('tasks_completed', 0)}")
    print(f"  Tasks failed:         {m.get('tasks_failed', 0)}")
    print(f"  Retry attempts:       {m.get('retry_attempts', 0)}")
    print(f"  Scheduler decisions:  {m.get('scheduler_decisions', 0)}")
    peak = m.get("peak_resource_usage", {})
    if peak:
        for r, v in sorted(peak.items()):
            print(f"  Peak {r}:  {v}")


# ── Main ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Visualize scheduler execution")
    parser.add_argument("input_file", help="Scheduler input file")
    parser.add_argument("--format", choices=["ascii", "png"], default="ascii",
                        help="Output format (default: ascii)")
    args = parser.parse_args()

    tasks, deps, resources, reqs, fail_set, retry_map = parse_input(args.input_file)

    print("Running scheduler...")
    events, metrics, stdout = run_scheduler(args.input_file)

    print()
    print("=== Dependency Graph ===")
    render_dependency_graph(tasks, deps, fail_set, args.format)

    print()
    print("=== Execution Timeline ===")
    if events:
        render_timeline_ascii(events)
        if args.format == "png":
            render_timeline_png(events)
    else:
        print("  (no events)")

    print()
    print("=== Resource Usage ===")
    if events:
        render_resource_ascii(events, resources, reqs)
        if args.format == "png":
            render_resource_png(events, resources, reqs)
    else:
        print("  (no resources)")

    print()
    print("=== Metrics ===")
    print_metrics(metrics)

    for f in ["trace.json", "metrics.json"]:
        if os.path.exists(f):
            os.remove(f)


if __name__ == "__main__":
    main()
