#!/usr/bin/env python3
"""
Determinism validator for the scheduler.

Runs the same input through the scheduler N times and verifies all outputs
are byte-identical.

Usage:
    python3 tools/check_determinism.py [--runs N] [--input FILE] [--all]
"""

import argparse
import glob
import hashlib
import os
import subprocess
import sys

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOLUTION = os.path.join(PROJECT_DIR, "src", "scheduler.py")
if not os.path.exists(SOLUTION):
    SOLUTION = os.path.join(PROJECT_DIR, "starter", "python", "solution.py")


def run_once(input_text):
    result = subprocess.run(
        [sys.executable, SOLUTION],
        input=input_text,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return result.stdout


def check_determinism(input_path, num_runs):
    with open(input_path) as f:
        input_text = f.read()

    hashes = set()
    outputs = []
    for i in range(num_runs):
        out = run_once(input_text)
        h = hashlib.sha256(out.encode()).hexdigest()
        hashes.add(h)
        outputs.append(out)

    return len(hashes) == 1, hashes, outputs


def main():
    parser = argparse.ArgumentParser(description="Check scheduler determinism")
    parser.add_argument("--runs", type=int, default=100,
                        help="Number of runs per test (default: 100)")
    parser.add_argument("--input", type=str, help="Single input file to check")
    parser.add_argument("--all", action="store_true",
                        help="Check all test inputs")
    args = parser.parse_args()

    if args.input:
        files = [args.input]
    elif args.all:
        files = sorted(glob.glob(os.path.join(PROJECT_DIR, "tests", "*", "*_input.txt")))
    else:
        files = sorted(glob.glob(os.path.join(PROJECT_DIR, "tests", "public", "*_input.txt")))

    total = len(files)
    passed = 0
    failed_list = []

    for i, path in enumerate(files):
        name = os.path.relpath(path, PROJECT_DIR)
        ok, hashes, _ = check_determinism(path, args.runs)
        if ok:
            passed += 1
            status = "DETERMINISTIC"
        else:
            status = f"NONDETERMINISTIC ({len(hashes)} distinct outputs)"
            failed_list.append(name)

        print(f"{status:35s} {name} ({args.runs} runs)")

    print()
    print(f"Results: {passed}/{total} deterministic")
    if failed_list:
        print("Nondeterministic tests:")
        for f in failed_list:
            print(f"  {f}")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
