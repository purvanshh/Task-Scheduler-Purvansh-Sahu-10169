# Scheduler Visualization Demo

Interactive web-based visualization for the DAG task scheduler.

## Architecture

```
Browser (React + Vite)  ──POST /run──►  FastAPI Backend  ──stdin──►  Scheduler
         │                                    │                         │
         │◄────── JSON response ──────────────┘◄── trace.json + stdout ─┘
         │
    ┌────┴────────────────────────┐
    │ Dependency Graph (Canvas)   │
    │ Execution Timeline (SVG)    │
    │ Resource Usage (Recharts)   │
    │ Console Output              │
    │ Metrics Dashboard           │
    │ Tick Replay Slider          │
    └─────────────────────────────┘
```

## Quick Start

### 1. Backend

```bash
cd demo/backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install fastapi uvicorn
uvicorn server:app --reload --port 8000
```

### 2. Frontend (in a second terminal)

```bash
cd demo/frontend
npm install
npm run dev
```

### 3. Open

Navigate to [http://localhost:5173](http://localhost:5173)

## Features

- **Scheduler Input**: Text area with preset example programs
- **Dependency Graph**: Canvas-rendered DAG with color-coded task states
- **Execution Timeline**: SVG Gantt chart showing task execution intervals
- **Resource Usage**: Recharts area charts with capacity limit indicators
- **Console Output**: Raw scheduler stdout
- **Metrics Dashboard**: Ticks, completed, failed, retries, peak resource usage
- **Tick Replay Slider**: Scrub through execution to see task states at each tick

## Example Programs Included

| Name | Description |
|------|-------------|
| Simple DAG | Two tasks with a dependency |
| Resource Contention | Three tasks sharing a single resource |
| Failure + Retry | Failure injection with retry logic |
| Diamond DAG + Resources | Diamond dependency pattern with multi-resource constraints |
| Cascade Failure | Root failure cascading through a tree |

## API

### POST /run

**Request:**
```json
{
  "program": "TASK a 2 10\nTASK b 1 5\nDEPEND b a\nRUN\nEND"
}
```

**Response:**
```json
{
  "events": [
    {"tick": 0, "type": "STARTED", "task": "a"},
    {"tick": 2, "type": "COMPLETED", "task": "a"},
    {"tick": 2, "type": "STARTED", "task": "b"},
    {"tick": 3, "type": "COMPLETED", "task": "b"}
  ],
  "metrics": {
    "total_ticks": 4,
    "tasks_completed": 2,
    "tasks_failed": 0,
    "retry_attempts": 0,
    "peak_resource_usage": {},
    "scheduler_decisions": 2,
    "total_tasks": 2
  },
  "stdout": "STARTED a 0\nCOMPLETED a 2\nSTARTED b 2\nCOMPLETED b 3\n",
  "tasks": {"a": {"duration": 2, "priority": 10}, "b": {"duration": 1, "priority": 5}},
  "dependencies": {"b": ["a"]},
  "resources": {},
  "requirements": {}
}
```
