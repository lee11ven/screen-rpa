<p align="right">
  <a href="README.md">中文</a>
</p>

<div align="center">
  <img src="frontend/public/logo.png" width="96" alt="Screen RPA Logo" />
</div>

<h1 align="center">🤖 Screen RPA</h1>

<p align="center">
  A visual automation workflow platform for Windows, focused on flow orchestration and PC-side automation.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue.svg" alt="Python" />
  <img src="https://img.shields.io/badge/Vue-3.x-42b883.svg" alt="Vue" />
  <img src="https://img.shields.io/badge/FastAPI-Workflow%20API-009688.svg" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Platform-Windows-informational.svg" alt="Platform" />
  <img src="https://camo.githubusercontent.com/5ae27c047f5dbaa8d2909bb07be446ec791f9daf429e322106ffb7bba35a4b7e/68747470733a2f2f696d672e736869656c64732e696f2f62616467652fe58d8fe8aeae2d4147504c2d2d332e30253230253242253230e59586e4b89ae68e88e69d832d677265656e2e737667" alt="License AGPL-3.0 + Commercial" />
</p>

## 📖 Overview

Screen RPA lets you build automation workflows through visual drag-and-drop, covering the full loop from design and versioned releases to task execution and runtime observability.  
It suits high-frequency, repetitive, standardized desktop operations such as data entry, rule-based clicking, batch processing, and orchestrated workflow runs.

## 🚀 Current Progress

### ✅ Completed

- Workflow orchestration
- PC automation

### 🧩 Planned

- Web data scraping
- Mobile automation

## ✨ Core Capabilities

### 1) 🔁 Workflow Orchestration (completed)

- Visual editing: build flows by dragging nodes on a canvas
- Node types: `start`, `end`, `action`, `wait`, `if`, `subflow`, `loop-container`, `continue`, `break`, `lowcode_function`
- Error strategies: `fail`, `retry`, `skip`, `to_node`
- Contract validation: catch structural issues early via `contracts/workflow-runtime.schema.json`

### 2) 🖥️ PC Automation (completed)

- Mouse actions: move, click, drag, scroll, smart click
- Keyboard actions: text input, key press, key combos, physical hotkeys
- Image capabilities: template matching, locate center, image-based click
- System capabilities: window find/activate, clipboard read/write, command execution

### 3) ⚙️ Execution Engine & Queue

- Direct run and queued async execution modes
- `idempotency_key` to avoid duplicate runs from repeated submissions
- Built-in retry backoff, lease recovery, and dead-letter handling for stability

### 4) 📊 Runtime Observability

- Run overview: status, per-node results, errors
- Node logs: context and execution trace per node
- Run control: cancel runs to limit damage
- Queue tracking: enqueue, consume, retry, and completion end-to-end

## 🎯 Use Cases

- Build publishable, traceable desktop automation workflows
- Cross-node conditionals, loop control, and subflow reuse
- Batch entry, batch backfill, and rule-based system operations
- Extend business logic via low-code function nodes

## 🗂️ Project Structure

```text
screen-rpa/
  backend/                 # FastAPI + SQLite + execution engine + Worker
  frontend/                # Vue3 + Vite + Element Plus admin UI
  contracts/               # Workflow runtime JSON Schema and examples
  tests/                   # API / engine / system actions / contract tests
  packaging/               # PyInstaller / Inno Setup packaging scripts
  data/                    # Local database and runtime data
```

## 🚀 Quick Start (Development)

### 🧱 Requirements

- Windows (recommended)
- Python 3.10+
- Node.js 18+
- npm 9+

### Option A: ⚡ One-command start (API, Worker, frontend)

```bash
dev.bat
```

Starts:

- Backend API (`uvicorn`)
- Worker (`python -m app.worker`)
- Frontend dev server (`npm run dev`)

### Option B: 🛠️ Manual start

1) Start the backend API

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --app-dir .
```

2) Start the Worker (required for async/queue execution)

```bash
cd backend
python -m app.worker
```

3) Start the frontend

```bash
cd frontend
npm install
npm run dev
```

URLs:

- Frontend: `http://127.0.0.1:5173`
- Backend: `http://127.0.0.1:8000`
- Health check: `http://127.0.0.1:8000/health`

## 🔌 API & Protocol

- API prefix: `/api/workflow`
- Response envelope: `success / code / message / data`
- Protocol version: `GET /api/workflow/meta/protocol`
- DSL contract: `contracts/workflow-runtime.schema.json`
- Example: `contracts/examples/minimal-runtime.json`

## ✅ Tests & Quality

```bash
pip install -r backend/requirements.txt
pytest tests -q
```

Tests cover API, contract validation, executors, and system-action core paths for fast CI regression.

## 📦 Desktop App Packaging

```bash
build.bat
```

Default output: `dist/ScreenRPA/`. Use `packaging/installer.iss` to build an installer.

## 🧪 Common Backend Environment Variables

- `DATABASE_PATH`: SQLite file path (default `../data/rpa.db`)
- `WORKER_ID`: Worker identifier (default `worker-1`)
- `QUEUE_LEASE_SEC`: Message lease seconds (default `60`)
- `QUEUE_MAX_RETRY`: Max retries (default `3`)
- `QUEUE_RETRY_BACKOFF_SEC`: Retry backoff base seconds (default `5`)
- `RECOVERY_SCAN_INTERVAL_SEC`: Expired lease scan interval seconds (default `15`)

## 🛣️ Roadmap

- [ ] Web data scraping (browser capture, element extraction, download pipeline)
- [ ] Mobile automation (device connection, touch actions, recognition-based taps)
- [ ] More ready-to-use action nodes
- [ ] Richer runtime metrics and reporting

---

If you want a “visual + publishable + observable” automation workflow engine, **Screen RPA** is a practical starting point. Issues and PRs are welcome.
