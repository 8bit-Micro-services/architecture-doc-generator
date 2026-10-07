"""FastAPI application: server-rendered SDLC workboard."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Iterator, Optional

from fastapi import Depends, FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import sqlite3

from . import services
from .db import connect, init_db

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DB = os.environ.get("WORKBOARD_DB", "workboard.sqlite3")


def create_app(db_path: Optional[str] = None) -> FastAPI:
    db_file = db_path or DEFAULT_DB
    init_db(db_file)
    app = FastAPI(title="SDLC Workboard")
    app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
    templates = Jinja2Templates(directory=BASE_DIR / "templates")  # autoescape enabled for .html

    def get_conn() -> Iterator[sqlite3.Connection]:
        conn = connect(db_file)
        try:
            yield conn
        finally:
            conn.close()

    Conn = Depends(get_conn)

    def back_to_task(task_id: int) -> RedirectResponse:
        return RedirectResponse(app.url_path_for("task_detail", task_id=int(task_id)), status_code=303)

    def render(request: Request, name: str, status_code: int = 200, **ctx):
        return templates.TemplateResponse(request, name, ctx, status_code=status_code)

    def error(request: Request, message: str, status_code: int = 400):
        return render(request, "error.html", status_code, message=message)

    @app.exception_handler(services.ValidationError)
    async def validation_handler(request: Request, exc: services.ValidationError):
        return error(request, str(exc), 400)

    @app.exception_handler(LookupError)
    async def lookup_handler(request: Request, exc: LookupError):
        return error(request, str(exc), 404)

    @app.get("/", response_class=HTMLResponse)
    def overview(request: Request, conn: sqlite3.Connection = Conn):
        return render(request, "overview.html", readiness=services.phase_readiness(conn),
                      roles=services.list_roles(conn))

    @app.get("/board", response_class=HTMLResponse)
    def board(request: Request, role: str = "", phase: str = "", status: str = "",
              conn: sqlite3.Connection = Conn):
        tasks = services.list_tasks(conn, role, phase, status)
        phases = services.list_phases(conn)
        columns = [(p, [t for t in tasks if t["phase_id"] == p["id"]]) for p in phases]
        return render(request, "board.html", columns=columns, phases=phases,
                      roles=services.list_roles(conn), statuses=services.STATUSES,
                      priorities=services.PRIORITIES, sel_role=role, sel_phase=phase, sel_status=status)

    @app.post("/tasks")
    def create_task(title: str = Form(""), phase_id: str = Form(""), accountable_role: str = Form(""),
                    responsible_role: str = Form(""), priority: str = Form("Medium"), sprint: str = Form(""),
                    requirement_id: str = Form(""), current_work: str = Form(""),
                    conn: sqlite3.Connection = Conn):
        task_id = services.create_task(conn, title=title, phase_id=phase_id, accountable_role=accountable_role,
                                       responsible_role=responsible_role, priority=priority, sprint=sprint,
                                       requirement_id=requirement_id, current_work=current_work)
        return back_to_task(task_id)

    @app.get("/tasks/{task_id}", response_class=HTMLResponse)
    def task_detail(request: Request, task_id: int, conn: sqlite3.Connection = Conn):
        task = services.get_task(conn, task_id)
        if task is None:
            return error(request, "task not found", 404)
        return render(request, "task.html", task=task, roles=services.list_roles(conn),
                      statuses=services.STATUSES, kinds=services.COMMENT_KINDS)

    @app.post("/tasks/{task_id}/status")
    def task_status(task_id: int, status: str = Form(""), blockers: Optional[str] = Form(None),
                    current_work: Optional[str] = Form(None), conn: sqlite3.Connection = Conn):
        services.update_status(conn, task_id, status, blockers, current_work)
        return back_to_task(task_id)

    @app.post("/tasks/{task_id}/comments")
    def task_comment(task_id: int, author: str = Form(""), role: str = Form(""), kind: str = Form("update"),
                     body: str = Form(""), conn: sqlite3.Connection = Conn):
        services.add_comment(conn, task_id, author=author, role=role, kind=kind, body=body)
        return back_to_task(task_id)

    @app.post("/tasks/{task_id}/handoff")
    def task_handoff(task_id: int, to_role: str = Form(""), note: str = Form(""), author: str = Form(""),
                     conn: sqlite3.Connection = Conn):
        services.record_handoff(conn, task_id, to_role=to_role, note=note, author=author)
        return back_to_task(task_id)

    @app.post("/tasks/{task_id}/contract")
    def task_contract(task_id: int, test_evidence: str = Form(""), risks: str = Form(""),
                      decision_ref: str = Form(""), conn: sqlite3.Connection = Conn):
        services.update_contract(conn, task_id, test_evidence=test_evidence, risks=risks,
                                 decision_ref=decision_ref)
        return back_to_task(task_id)

    @app.post("/tasks/{task_id}/gates/{gate_id}")
    def task_gate(task_id: int, gate_id: int, done: str = Form(""), conn: sqlite3.Connection = Conn):
        services.set_gate_item(conn, task_id, gate_id, done == "1")
        return back_to_task(task_id)

    @app.get("/jobs", response_class=HTMLResponse)
    def jobs(request: Request, conn: sqlite3.Connection = Conn):
        return render(request, "jobs.html", jobs=services.list_jobs(conn), states=services.TEST_STATES)

    @app.post("/jobs")
    def create_job(name: str = Form(""), input_documents: str = Form(""), conn: sqlite3.Connection = Conn):
        services.create_job(conn, name=name, input_documents=input_documents)
        return RedirectResponse("/jobs", status_code=303)

    @app.post("/jobs/{job_id}/state")
    def job_state(job_id: int, test_state: str = Form(""), conn: sqlite3.Connection = Conn):
        services.update_job_state(conn, job_id, test_state)
        return RedirectResponse("/jobs", status_code=303)

    return app


app = create_app()
