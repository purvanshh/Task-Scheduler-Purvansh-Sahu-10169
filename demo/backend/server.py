"""
FastAPI backend for the scheduler visualization demo.

Receives scheduler commands, runs the scheduler with --trace --metrics,
and returns structured results for the frontend to visualize.
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Scheduler Visualization API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCHEDULER = PROJECT_ROOT / "src" / "scheduler.py"
if not SCHEDULER.exists():
    SCHEDULER = PROJECT_ROOT / "starter" / "python" / "solution.py"


class RunRequest(BaseModel):
    program: str


class RunResponse(BaseModel):
    events: list
    metrics: dict
    stdout: str
    tasks: dict
    dependencies: dict
    resources: dict
    requirements: dict


def parse_program_metadata(program: str):
    """Extract task/dep/resource/requirement metadata from the program text."""
    tasks = {}
    deps = {}
    resources = {}
    requirements = {}

    for line in program.strip().split("\n"):
        parts = line.strip().split()
        if not parts:
            continue
        cmd = parts[0]
        if cmd == "TASK" and len(parts) >= 3:
            tid = parts[1]
            dur = int(parts[2])
            pri = int(parts[3]) if len(parts) > 3 else 0
            tasks[tid] = {"duration": dur, "priority": pri}
        elif cmd == "DEPEND" and len(parts) >= 3:
            deps.setdefault(parts[1], [])
            if parts[2] not in deps[parts[1]]:
                deps[parts[1]].append(parts[2])
        elif cmd == "RESOURCE" and len(parts) >= 3:
            resources[parts[1]] = int(parts[2])
        elif cmd == "REQUIRE" and len(parts) >= 4:
            requirements.setdefault(parts[1], {})
            requirements[parts[1]][parts[2]] = int(parts[3])

    return tasks, deps, resources, requirements


@app.post("/run", response_model=RunResponse)
def run_scheduler(req: RunRequest):
    program = req.program.strip()
    if not program:
        raise HTTPException(status_code=400, detail="Empty program")

    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, "input.txt")
        with open(input_path, "w") as f:
            f.write(program + "\n")

        trace_path = os.path.join(tmpdir, "trace.json")
        metrics_path = os.path.join(tmpdir, "metrics.json")

        try:
            result = subprocess.run(
                [sys.executable, str(SCHEDULER), "--trace", "--metrics"],
                stdin=open(input_path),
                capture_output=True,
                text=True,
                timeout=10,
                cwd=tmpdir,
            )
        except subprocess.TimeoutExpired:
            raise HTTPException(status_code=504, detail="Scheduler timed out")

        stdout = result.stdout

        events = []
        if os.path.exists(trace_path):
            with open(trace_path) as f:
                data = json.load(f)
                events = data.get("events", [])

        metrics = {}
        if os.path.exists(metrics_path):
            with open(metrics_path) as f:
                data = json.load(f)
                metrics = data[0] if isinstance(data, list) and data else data

        tasks, deps, resources, requirements = parse_program_metadata(program)

        return RunResponse(
            events=events,
            metrics=metrics,
            stdout=stdout,
            tasks=tasks,
            dependencies=deps,
            resources=resources,
            requirements=requirements,
        )


@app.get("/health")
def health():
    return {"status": "ok", "scheduler": str(SCHEDULER)}
