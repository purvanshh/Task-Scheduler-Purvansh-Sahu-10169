#!/usr/bin/env python3
"""
Categorical grader for the Task Scheduler.

Runs every test case in tests/public/ and tests/custom/, compares actual output
to expected output, and groups results into scoring categories.

Usage:
    python3 grader/grader.py          (from project root)
    make grade
"""

import os
import subprocess
import sys

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOLUTION = os.path.join(PROJECT_DIR, "src", "scheduler.py")
if not os.path.exists(SOLUTION):
    SOLUTION = os.path.join(PROJECT_DIR, "starter", "python", "solution.py")

CATEGORIES = {
    "basic_execution": {
        "weight": 10,
        "tests": [
            "tests/custom/01_single_task",
            "tests/custom/09_alpha_tiebreak",
            "tests/custom/22_dup_task",
        ],
    },
    "dependency_chains": {
        "weight": 10,
        "tests": [
            "tests/custom/02_dep_chain",
            "tests/custom/03_multi_dep",
            "tests/public/01",
            "tests/custom/29_large_graph",
        ],
    },
    "cycle_detection": {
        "weight": 15,
        "tests": [
            "tests/custom/04_simple_cycle",
            "tests/custom/05_large_cycle",
            "tests/custom/06_two_disjoint_cycles",
            "tests/custom/07_self_loop",
            "tests/public/04",
        ],
    },
    "scheduling_priority": {
        "weight": 10,
        "tests": [
            "tests/custom/08_priority_scheduling",
            "tests/public/02",
        ],
    },
    "resource_constraints": {
        "weight": 10,
        "tests": [
            "tests/custom/10_resource_contention",
            "tests/custom/26_multi_resource",
            "tests/custom/28_resource_deadlock",
        ],
    },
    "retry_logic": {
        "weight": 15,
        "tests": [
            "tests/custom/12_fail_with_retry",
            "tests/custom/13_retry_resource_contention",
            "tests/custom/20_retry_without_fail",
            "tests/public/03",
        ],
    },
    "failure_cascade": {
        "weight": 15,
        "tests": [
            "tests/custom/11_fail_no_retry",
            "tests/custom/14_deep_cascade",
            "tests/custom/15_diamond_cascade",
            "tests/custom/23_mixed_fail_complete",
            "tests/custom/24_two_fails_shared_dep",
            "tests/custom/27_fail_later_tick",
            "tests/public/05",
        ],
    },
    "status_queries": {
        "weight": 5,
        "tests": [
            "tests/custom/17_unknown_status",
            "tests/custom/19_undefined_resource",
            "tests/custom/18_undefined_dep",
        ],
    },
    "topological_order": {
        "weight": 5,
        "tests": [
            "tests/custom/25_cycle_then_normal",
        ],
    },
    "batch_semantics": {
        "weight": 5,
        "tests": [
            "tests/custom/16_batch_reset",
            "tests/custom/21_empty_run",
            "tests/custom/30_comprehensive",
        ],
    },
}


def normalize(text: str) -> str:
    lines = text.rstrip("\n").split("\n")
    return "\n".join(line.rstrip() for line in lines)


def run_test(test_base: str) -> tuple[bool, str, str]:
    """Run a single test case. Returns (passed, expected, actual)."""
    input_path = os.path.join(PROJECT_DIR, test_base + "_input.txt")
    expected_path = os.path.join(PROJECT_DIR, test_base + "_expected_output.txt")

    if not os.path.isfile(input_path) or not os.path.isfile(expected_path):
        return False, "", f"[MISSING FILE: {test_base}]"

    with open(input_path) as f:
        input_data = f.read()
    with open(expected_path) as f:
        expected = normalize(f.read())

    try:
        result = subprocess.run(
            [sys.executable, SOLUTION],
            input=input_data,
            capture_output=True,
            text=True,
            timeout=10,
        )
        actual = normalize(result.stdout)
    except subprocess.TimeoutExpired:
        return False, expected, "[TIMEOUT]"
    except Exception as e:
        return False, expected, f"[ERROR: {e}]"

    return actual == expected, expected, actual


def main():
    total_score = 0
    total_weight = 0
    all_passed = True

    for category, info in CATEGORIES.items():
        weight = info["weight"]
        tests = info["tests"]
        passed = 0

        for t in tests:
            ok, expected, actual = run_test(t)
            if ok:
                passed += 1
            else:
                all_passed = False

        ratio = passed / len(tests) if tests else 0
        earned = round(ratio * weight, 1)
        total_score += earned
        total_weight += weight

        label = "PASS" if passed == len(tests) else "FAIL"
        print(f"{label} {category} ({passed}/{len(tests)} tests, {earned}/{weight} pts)")

        if passed < len(tests):
            for t in tests:
                ok, expected, actual = run_test(t)
                if not ok:
                    name = os.path.basename(t)
                    print(f"     FAIL {name}")
                    exp_lines = expected.split("\n")
                    act_lines = actual.split("\n")
                    for i, (e, a) in enumerate(
                        zip(exp_lines, act_lines), 1
                    ):
                        if e != a:
                            print(f"       line {i}: expected '{e}'")
                            print(f"       line {i}:   actual '{a}'")
                            break
                    if len(exp_lines) != len(act_lines):
                        print(
                            f"       expected {len(exp_lines)} lines, "
                            f"got {len(act_lines)}"
                        )

    print()
    score = int(total_score) if total_score == int(total_score) else total_score
    print(f"FINAL SCORE: {score} / {total_weight}")


if __name__ == "__main__":
    main()
