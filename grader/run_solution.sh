#!/usr/bin/env bash
# Run the Python solution with a 10-second timeout.
# Reads from stdin, writes to stdout.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
SOLUTION="$PROJECT_DIR/src/scheduler.py"
[ -f "$SOLUTION" ] || SOLUTION="$PROJECT_DIR/starter/python/solution.py"

if command -v gtimeout &>/dev/null; then
    gtimeout 10 python3 "$SOLUTION"
elif command -v timeout &>/dev/null; then
    timeout 10 python3 "$SOLUTION"
else
    python3 "$SOLUTION"
fi
