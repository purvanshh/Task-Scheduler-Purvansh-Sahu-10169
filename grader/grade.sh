#!/usr/bin/env bash
# Grade the Python solution against test cases.
# Usage: ./grade.sh <test_directory>
# Example: ./grade.sh tests/public

set -euo pipefail

TEST_DIR="$1"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ ! -d "$TEST_DIR" ]; then
    echo "Test directory not found: $TEST_DIR" >&2
    exit 1
fi

PASS=0
FAIL=0
TOTAL=0

for input_file in "$TEST_DIR"/*_input.txt; do
    [ -f "$input_file" ] || continue

    base="$(basename "$input_file" _input.txt)"
    expected_file="$TEST_DIR/${base}_expected_output.txt"

    if [ ! -f "$expected_file" ]; then
        echo "SKIP $base (no expected output file)"
        continue
    fi

    TOTAL=$((TOTAL + 1))

    # Run solution and capture output
    actual=$("$SCRIPT_DIR/run_solution.sh" < "$input_file" 2>/dev/null || true)

    # Normalize: trim trailing whitespace per line
    expected_norm=$(sed 's/[[:space:]]*$//' < "$expected_file")
    actual_norm=$(printf '%s' "$actual" | sed 's/[[:space:]]*$//')

    if [ "$expected_norm" = "$actual_norm" ]; then
        echo "PASS $base"
        PASS=$((PASS + 1))
    else
        echo "FAIL $base"
        FAIL=$((FAIL + 1))
        diff <(printf '%s\n' "$expected_norm") <(printf '%s\n' "$actual_norm") | head -20 || true
    fi
done

echo ""
echo "Score: $PASS/$TOTAL"

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
exit 0
