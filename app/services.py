"""Workflow/business logic. All SQL is parameterised; all input is validated here."""
from __future__ import annotations

import sqlite3
from typing import Any, Optional

STATUSES = ["Backlog", "In Progress", "Blocked", "In Review", "Done"]
PRIORITIES = ["Low", "Medium", "High", "Critical"]
COMMENT_KINDS = ["update", "blocker", "decision", "handoff"]
TEST_STATES = ["Not Run", "Running", "Passed", "Failed"]

MAX_SHORT = 200
MAX_LONG = 2000


class ValidationError(ValueError):
    """Raised when user input fails validation."""


def _text(value: Optional[str], field: str, *, required: bool = True, max_len: int = MAX_SHORT) -> str:
    value = (value or "").replace("\x00", "").strip()
    if required and not value:
        raise ValidationError(f"{field} is required")
    if len(value) > max_len:
        raise ValidationError(f"{field} must be at most {max_len} characters")
    return value


def _choice(value: Optional[str], field: str, allowed: list[str]) -> str:
    if value not in allowed:
        raise ValidationError(f"{field} must be one of: {', '.join(allowed)}")
    return value  # type: ignore[return-value]


def role_names(conn: sqlite3.Connection) -> list[str]:
    return [r["name"] for r in conn.execute("SELECT name FROM roles ORDER BY id")]


def _role(conn: sqlite3.Connection, value: Optional[str], field: str) -> str:
    return _choice(value, field, role_names(conn))


def list_phases(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM phases ORDER BY position").fetchall()


def list_roles(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM roles ORDER BY id").fetchall()


def list_tasks(conn: sqlite3.Connection, role: str = "", phase: str = "", status: str = "") -> list[sqlite3.Row]:
    """List tasks, optionally filtered by role (accountable or responsible), phase id, status."""
    sql = ("SELECT t.*, p.name AS phase_name FROM tasks t JOIN phases p ON p.id = t.phase_id WHERE 1=1")
    params: list[Any] = []
    if role:
        _role(conn, role, "role")
        sql += " AND (t.responsible_role = ? OR t.accountable_role = ?)"
        params += [role, role]
    if phase:
        if not (phase.isascii() and phase.isdigit()):
            raise ValidationError("phase must be a valid id")
        sql += " AND t.phase_id = ?"
        params.append(int(phase))
    if status:
        _choice(status, "status", STATUSES)
        sql += " AND t.status = ?"
        params.append(status)
    sql += " ORDER BY p.position, t.id"
    return conn.execute(sql, params).fetchall()


def get_task(conn: sqlite3.Connection, task_id: int) -> Optional[dict[str, Any]]:
    row = conn.execute(
        "SELECT t.*, p.name AS phase_name FROM tasks t JOIN phases p ON p.id = t.phase_id WHERE t.id = ?",
        (task_id,),
    ).fetchone()
    if row is None:
        return None
    task = dict(row)
    gates = conn.execute("SELECT * FROM gate_items WHERE task_id = ? ORDER BY id", (task_id,)).fetchall()
    task["gate_in"] = [g for g in gates if g["kind"] == "in"]
    task["gate_out"] = [g for g in gates if g["kind"] == "out"]
    task["comments"] = conn.execute(
        "SELECT * FROM comments WHERE task_id = ? ORDER BY id DESC", (task_id,)).fetchall()
    task["handoffs"] = conn.execute(
        "SELECT * FROM handoffs WHERE task_id = ? ORDER BY id DESC", (task_id,)).fetchall()
    return task


def create_task(conn: sqlite3.Connection, *, title: str, phase_id: str, accountable_role: str,
                responsible_role: str, priority: str = "Medium", sprint: str = "",
                requirement_id: str = "", current_work: str = "") -> int:
    title = _text(title, "title")
    if not ((phase_id or "").isascii() and (phase_id or "").isdigit()) or not conn.execute(
            "SELECT 1 FROM phases WHERE id = ?", (int(phase_id),)).fetchone():
        raise ValidationError("phase is invalid")
    acc = _role(conn, accountable_role, "accountable role")
    resp = _role(conn, responsible_role, "responsible role")
    priority = _choice(priority, "priority", PRIORITIES)
    cur = conn.execute(
        "INSERT INTO tasks (title, phase_id, accountable_role, responsible_role, process_owner, priority,"
        " status, current_work, sprint, requirement_id) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (title, int(phase_id), acc, resp, acc, priority, "Backlog",
         _text(current_work, "current work", required=False, max_len=MAX_LONG),
         _text(sprint, "sprint", required=False), _text(requirement_id, "requirement id", required=False)),
    )
    conn.commit()
    return int(cur.lastrowid)


def update_status(conn: sqlite3.Connection, task_id: int, status: str, blockers: Optional[str] = None,
                  current_work: Optional[str] = None) -> None:
    """Update status; moving to Blocked requires a blocker description."""
    status = _choice(status, "status", STATUSES)
    task = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if task is None:
        raise LookupError("task not found")
    blockers_v = task["blockers"] if blockers is None else _text(blockers, "blockers", required=False, max_len=MAX_LONG)
    work_v = task["current_work"] if current_work is None else _text(
        current_work, "current work", required=False, max_len=MAX_LONG)
    if status == "Blocked" and not blockers_v:
        raise ValidationError("a blocker description is required when status is Blocked")
    if status == "Done":
        pending = conn.execute(
            "SELECT COUNT(*) FROM gate_items WHERE task_id = ? AND kind = 'out' AND done = 0", (task_id,)
        ).fetchone()[0]
        if pending:
            raise ValidationError("all gate-out criteria must be met before marking Done")
        blockers_v = ""
    conn.execute("UPDATE tasks SET status = ?, blockers = ?, current_work = ? WHERE id = ?",
                 (status, blockers_v, work_v, task_id))
    conn.commit()


def add_comment(conn: sqlite3.Connection, task_id: int, *, author: str, role: str, kind: str, body: str) -> int:
    if conn.execute("SELECT 1 FROM tasks WHERE id = ?", (task_id,)).fetchone() is None:
        raise LookupError("task not found")
    author = _text(author, "author", max_len=80)
    role = _role(conn, role, "role")
    kind = _choice(kind, "kind", COMMENT_KINDS)
    body = _text(body, "message", max_len=MAX_LONG)
    cur = conn.execute("INSERT INTO comments (task_id, author, role, kind, body) VALUES (?,?,?,?,?)",
                       (task_id, author, role, kind, body))
    conn.commit()
    return int(cur.lastrowid)


def record_handoff(conn: sqlite3.Connection, task_id: int, *, to_role: str, note: str, author: str = "") -> None:
    """Record a handoff: responsibility moves to the next role and the feed gets an entry."""
    task = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if task is None:
        raise LookupError("task not found")
    to_role = _role(conn, to_role, "next role")
    note = _text(note, "handoff note", max_len=MAX_LONG)
    author = _text(author, "author", required=False, max_len=80) or task["responsible_role"]
    from_role = task["responsible_role"]
    if to_role == from_role:
        raise ValidationError("next role must differ from the current responsible role")
    conn.execute("INSERT INTO handoffs (task_id, from_role, to_role, note) VALUES (?,?,?,?)",
                 (task_id, from_role, to_role, note))
    conn.execute("UPDATE tasks SET responsible_role = ? WHERE id = ?", (to_role, task_id))
    conn.execute("INSERT INTO comments (task_id, author, role, kind, body) VALUES (?,?,?,?,?)",
                 (task_id, author, from_role, "handoff", f"Handoff {from_role} -> {to_role}: {note}"))
    conn.commit()


def update_contract(conn: sqlite3.Connection, task_id: int, *, test_evidence: str, risks: str,
                    decision_ref: str) -> None:
    if conn.execute("SELECT 1 FROM tasks WHERE id = ?", (task_id,)).fetchone() is None:
        raise LookupError("task not found")
    conn.execute("UPDATE tasks SET test_evidence = ?, risks = ?, decision_ref = ? WHERE id = ?", (
        _text(test_evidence, "test evidence", required=False, max_len=MAX_LONG),
        _text(risks, "risks", required=False, max_len=MAX_LONG),
        _text(decision_ref, "decision/ADR reference", required=False), task_id))
    conn.commit()


def set_gate_item(conn: sqlite3.Connection, task_id: int, gate_id: int, done: bool) -> None:
    cur = conn.execute("UPDATE gate_items SET done = ? WHERE id = ? AND task_id = ?",
                       (1 if done else 0, gate_id, task_id))
    if cur.rowcount == 0:
        raise LookupError("gate item not found")
    conn.commit()


def phase_readiness(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Per-phase gate readiness: share of gate-out items satisfied across the phase's tasks."""
    result = []
    for phase in list_phases(conn):
        tasks = conn.execute("SELECT status FROM tasks WHERE phase_id = ?", (phase["id"],)).fetchall()
        total, done = conn.execute(
            "SELECT COUNT(*), COALESCE(SUM(g.done), 0) FROM gate_items g JOIN tasks t ON t.id = g.task_id"
            " WHERE t.phase_id = ? AND g.kind = 'out'", (phase["id"],)).fetchone()
        blocked = sum(1 for t in tasks if t["status"] == "Blocked")
        percent = int(100 * done / total) if total else 0
        if tasks and total and done == total and all(t["status"] == "Done" for t in tasks):
            state = "Ready"
        elif blocked:
            state = "At Risk"
        elif done or any(t["status"] != "Backlog" for t in tasks):
            state = "In Progress"
        else:
            state = "Not Started"
        result.append({"phase": phase, "tasks": len(tasks), "gate_total": total, "gate_done": done,
                       "percent": percent, "state": state, "blocked": blocked})
    return result


def list_jobs(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM artifact_jobs ORDER BY id").fetchall()


def create_job(conn: sqlite3.Connection, *, name: str, input_documents: str) -> int:
    name = _text(name, "job name")
    docs = _text(input_documents, "input documents", max_len=MAX_LONG)
    cur = conn.execute(
        "INSERT INTO artifact_jobs (name, input_documents, drawio_output, image_output, pptx_output, test_state)"
        " VALUES (?,?,?,?,?,?)",
        (name, docs, "architecture.drawio", "architecture.png", "architecture-presentation.pptx", "Not Run"))
    conn.commit()
    return int(cur.lastrowid)


def update_job_state(conn: sqlite3.Connection, job_id: int, test_state: str) -> None:
    test_state = _choice(test_state, "test state", TEST_STATES)
    cur = conn.execute("UPDATE artifact_jobs SET test_state = ? WHERE id = ?", (test_state, job_id))
    if cur.rowcount == 0:
        raise LookupError("job not found")
    conn.commit()
