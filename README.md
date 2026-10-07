# architecture-doc-generator

Multi-document architecture visualization tool - Convert files to Draw.io diagrams and PowerPoint presentations.

This repository currently ships an **MVP SDLC workboard**: a local Python web app that models the ISO-aligned
SDLC (requirements → design → implementation → test → release → retrospective) and tracks the work of every role,
including the placeholder jobs that will later produce `architecture.drawio`, a diagram image and
`architecture-presentation.pptx`. The generators themselves are **not** implemented yet.

## Features
- Role-aware Kanban board across 8 phases, with filters by role, phase and status
- Cards show title, phase, accountable/responsible role, priority, status, current work, sprint, blockers, requirement ID
- Task detail page: process contract (owner, RACI, inputs, outputs, gate-in/out checklists, acceptance criteria,
  test evidence, risks, ADR), discussion feed (update / blocker / decision / handoff), status updates and handoffs
- Overview page with phase flow and gate readiness (Ready / In Progress / At Risk / Not Started)
- Architecture job tracker (input documents, expected outputs, test-result state)
- Seeded on first run with 10 roles, 8 phases, 13 tasks, discussion entries and one job

## Architecture
FastAPI + server-rendered Jinja2 templates (auto-escaped) + SQLite (stdlib `sqlite3`).
Routes (`app/main.py`) are thin; all validation and rules live in `app/services.py`
(enum whitelists, length limits, parameterised SQL). A task cannot be Blocked without a blocker
description and cannot be Done until all gate-out items are checked.

## Project structure
```
app/            main.py (routes), services.py (logic), db.py (schema), seed_data.py, templates/, static/
tests/          service tests and HTTP smoke tests
docs/           SDLC workflow, roles, inputs/outputs and gates
.github/workflows/ci.yml
```

## Setup and run
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Open http://127.0.0.1:8000. The database is `workboard.sqlite3` in the working directory
(override with `WORKBOARD_DB=/path/to/file.sqlite3`); delete it to reset to seed data.

## Tests
```bash
python -m pytest -q
```

See [docs/sdlc-workflow.md](docs/sdlc-workflow.md) for the workflow, roles and gates.
