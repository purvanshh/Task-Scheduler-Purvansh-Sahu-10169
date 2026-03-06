#!/usr/bin/env python3
"""
Generate large-scale stress test inputs for the scheduler.

Usage:
    python3 tests/stress/generate_stress.py
    make stress
"""

import os
import random

STRESS_DIR = os.path.dirname(os.path.abspath(__file__))


def write_test(name, lines):
    path = os.path.join(STRESS_DIR, f"{name}_input.txt")
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")


def gen_wide_dag():
    """1000 independent tasks — pure parallel throughput."""
    lines = []
    for i in range(1000):
        lines.append(f"TASK t{i:04d} 1")
    lines.append("RUN")
    lines.append("END")
    write_test("01_wide_1000", lines)


def gen_deep_chain():
    """500-task linear chain — deep sequential dependency."""
    lines = []
    for i in range(500):
        lines.append(f"TASK t{i:04d} 1")
    for i in range(1, 500):
        lines.append(f"DEPEND t{i:04d} t{i-1:04d}")
    lines.append("RUN")
    lines.append("END")
    write_test("02_deep_chain_500", lines)


def gen_diamond_layers():
    """10 layers of diamond DAGs — 200 tasks, heavy fan-in/fan-out."""
    lines = []
    tid = 0
    prev_layer = []
    for layer in range(10):
        width = 20
        current_layer = []
        for w in range(width):
            name = f"t{tid:04d}"
            lines.append(f"TASK {name} 1")
            current_layer.append(name)
            for dep in prev_layer:
                lines.append(f"DEPEND {name} {dep}")
            tid += 1
        prev_layer = current_layer
    lines.append("RUN")
    lines.append("END")
    write_test("03_diamond_200", lines)


def gen_resource_contention():
    """100 tasks competing for 3 resources with capacity 5."""
    lines = []
    rng = random.Random(99)
    res_names = ["cpu", "mem", "gpu"]
    for r in res_names:
        lines.append(f"RESOURCE {r} 5")
    for i in range(100):
        dur = rng.randint(1, 5)
        pri = rng.choice([0, 0, 0, 1, 5, 10])
        lines.append(f"TASK t{i:04d} {dur} {pri}")
        r = rng.choice(res_names)
        amt = rng.randint(1, 3)
        lines.append(f"REQUIRE t{i:04d} {r} {amt}")
    lines.append("RUN")
    lines.append("END")
    write_test("04_resource_100", lines)


def gen_heavy_retry():
    """50 tasks, 20 marked FAIL with varying retries + dependencies."""
    lines = []
    rng = random.Random(77)
    task_ids = [f"t{i:04d}" for i in range(50)]
    for tid in task_ids:
        lines.append(f"TASK {tid} {rng.randint(1, 3)}")
    order = list(task_ids)
    rng.shuffle(order)
    pos = {t: i for i, t in enumerate(order)}
    for _ in range(30):
        a = rng.choice(task_ids)
        b = rng.choice(task_ids)
        if a != b and pos[b] < pos[a]:
            lines.append(f"DEPEND {a} {b}")
    fail_targets = rng.sample(task_ids, 20)
    for tid in fail_targets:
        lines.append(f"FAIL {tid}")
        lines.append(f"RETRY {tid} {rng.randint(0, 2)}")
    lines.append("RUN")
    lines.append("END")
    write_test("05_heavy_retry_50", lines)


def gen_cascade_storm():
    """Tree of depth 8, branching factor 3 — one root failure cascades 3280 tasks."""
    lines = []
    tid = 0
    queue = []
    root = f"t{tid:05d}"
    lines.append(f"TASK {root} 1")
    queue.append(root)
    tid += 1
    for depth in range(8):
        next_queue = []
        for parent in queue:
            for _ in range(3):
                if tid >= 4000:
                    break
                name = f"t{tid:05d}"
                lines.append(f"TASK {name} 1")
                lines.append(f"DEPEND {name} {parent}")
                next_queue.append(name)
                tid += 1
        queue = next_queue
    lines.append(f"FAIL {root}")
    lines.append("RUN")
    lines.append("END")
    write_test("06_cascade_storm", lines)


def gen_multi_batch():
    """10 consecutive RUN batches, 50 tasks each."""
    lines = []
    for batch in range(10):
        for i in range(50):
            lines.append(f"TASK b{batch}t{i:03d} 1")
        if batch % 3 == 1:
            for i in range(1, 50):
                lines.append(f"DEPEND b{batch}t{i:03d} b{batch}t{i-1:03d}")
        lines.append("RUN")
    lines.append("END")
    write_test("07_multi_batch_500", lines)


def main():
    gen_wide_dag()
    gen_deep_chain()
    gen_diamond_layers()
    gen_resource_contention()
    gen_heavy_retry()
    gen_cascade_storm()
    gen_multi_batch()
    print(f"Generated 7 stress tests in {STRESS_DIR}/")


if __name__ == "__main__":
    main()
