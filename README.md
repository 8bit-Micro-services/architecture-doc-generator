# SDLC Workboard

A local Python application for managing ISO-aligned SDLC work, responsibilities, reviews, progress, and architecture/document metadata. It uses FastAPI, server-rendered auto-escaped Jinja2 templates, and SQLite. No external AI service is called.

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m app.launcher
```

The launcher binds only to `127.0.0.1`, chooses an available port by default, and opens the application in your browser. Use `python -m app.launcher --port 8000` to request a specific local port. The SQLite database is `workboard.sqlite3` in the current working directory; set `WORKBOARD_DB=/path/to/file.sqlite3` to choose another location. On first run it seeds the roles, phases, tasks, architecture document package, departments, and fictional policy/SOP examples.

## Developer run and tests

The standard development command remains available:

```bash
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000. Run the test suite with:

```bash
python -m pytest -q
```

GitHub Actions runs this command on pushes and pull requests. In this repository, some workflow attempts can display `action_required` with zero jobs when GitHub requires repository/organization approval for the workflow run; that is an external Actions approval setting, not a pytest failure. An authorised maintainer must approve the run in GitHub before jobs can execute.

## Dashboard navigation

- **Dashboard** — task-based completion percentage, phase readiness, task/gate/test/document-review summary, and current work by role.
- **SDLC Board** — role-, phase-, and status-filtered Kanban with task contracts, discussions, handoffs, blockers, and gate checks.
- **Architecture Jobs** — input/output tracking and test-state placeholder.
- **Documents** — filter/search by type, department, status, and owner role; register documents and inspect lifecycle detail.
- **Knowledge Base** — department-scoped manual search, indexing/review state, and AI/RAG mode disclosure.

## Document library and architecture output package

Documents persist in SQLite with type, department, owner, lifecycle status, version, linked requirement/task, source path or preview, approver, classification, indexing status, effective date, and update time. Architecture sample records cover the executive summary, requirements traceability, C4 context/container/component views, data flow, deployment, security, ADRs, presentation, and validation/E2E report.

These are **registered artifacts and previews**, not generated files. The MVP does not yet generate Draw.io diagrams, images, or a PowerPoint; source/path fields identify intended artifact locations and make package review/status trackable. Architecture detail pages show review roles, inputs/outputs, gates, approval status, and related records.

## Department knowledge and AI modes

The seeded departments are HR, IT/Engineering, Finance, and Operations. HR examples are fictional policy/SOP content only. Knowledge search is manual and constrained to the selected department. **Manual Only** is the default and sends no data to AI. Local AI/RAG is shown as ready for future integration but is not configured; Cloud AI is disabled/not configured. This application makes no external AI calls.

## Security limitations

This is a local MVP, not a production online service: it does not implement login, RBAC, department authorization, encryption-at-rest management, or an audit-grade access trail. Do not add real HR/PII or confidential department records unless protected storage and access controls are provided. Keep HR data private. A production or true RAG deployment requires RBAC, strict department isolation, audit trails, secure provider configuration, and appropriate deployment/network controls. The local server binds to loopback only; deploying online requires a separate security and persistence design.

## Optional packaged build

PyInstaller can create a platform-specific onedir package; build separately on each target OS. Do not commit generated executables or `dist/` output. From the repository root, install PyInstaller and bundle the templates/static resources with your platform's PyInstaller `--add-data` separator (`:` on Unix, `;` on Windows):

```bash
python -m pip install pyinstaller
pyinstaller --noconfirm --onedir --name SDLC-Workboard \
  --add-data "app/templates:app/templates" --add-data "app/static:app/static" app/launcher.py
```

See [docs/sdlc-workflow.md](docs/sdlc-workflow.md) for process ownership, gates, deliverable standards, and the knowledge workflow.
