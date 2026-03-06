#!/usr/bin/env python3
"""
Run stress tests and verify performance + determinism.

For each stress test:
  1. Run the scheduler
  2. Measure wall-clock time
  3. Verify the output is deterministic (run twice, compare)
  4. Report pass/fail and timing

Usage:
    python3 tests/stress/run_stress.py
"""

import glob
import os
import subprocess
import sys
import time

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SOLUTION = os.path.join(PROJECT_DIR, "src", "scheduler.py")
if not os.path.exists(SOLUTION):
    SOLUTION = os.path.join(PROJECT_DIR, "starter", "python", "solution.py")
STRESS_DIR = os.path.dirname(os.path.abspath(__file__))

TIME_LIMIT = 10.0


def run_once(input_path):
    with open(input_path) as f:
        input_text = f.read()
    t0 = time.time()
    result = subprocess.run(
        [sys.executable, SOLUTION],
        input=input_text,
        capture_output=True,
        text=True,
        timeout=TIME_LIMIT + 5,
    )
    elapsed = time.time() - t0
    return result.stdout, elapsed


def main():
    inputs = sorted(glob.glob(os.path.join(STRESS_DIR, "*_input.txt")))
    inputs = [p for p in inputs if os.path.basename(p) != "generate_stress.py"]

    if not inputs:
        print("No stress tests found. Run generate_stress.py first.")
        sys.exit(1)

    total = len(inputs)
    passed = 0
    results = []

    for path in inputs:
        name = os.path.basename(path).replace("_input.txt", "")
        with open(path) as f:
            num_lines = sum(1 for _ in f)

        try:
            out1, t1 = run_once(path)
            out2, t2 = run_once(path)
        except subprocess.TimeoutExpired:
            print(f"TIMEOUT  {name} (>{TIME_LIMIT}s)")
            results.append((name, "TIMEOUT", 0, 0))
            continue

        deterministic = out1 == out2
        within_limit = max(t1, t2) <= TIME_LIMIT
        output_lines = len(out1.strip().split("\n")) if out1.strip() else 0

        ok = deterministic and within_limit
        if ok:
            passed += 1
            status = "PASS"
        elif not deterministic:
            status = "NONDETERMINISTIC"
        else:
            status = "SLOW"

        print(f"{status:17s} {name:30s}  {t1:.2f}s / {t2:.2f}s  "
              f"({num_lines} input lines, {output_lines} output lines)")
        results.append((name, status, t1, t2))

    print()
    print(f"Stress results: {passed}/{total} passed")
    for name, status, t1, t2 in results:
        if status != "PASS":
            print(f"  {status}: {name}")

    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
