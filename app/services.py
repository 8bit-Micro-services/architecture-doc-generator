"""Workflow/business logic. All SQL is parameterised; all input is validated here."""
from __future__ import annotations

import sqlite3
from typing import Any, Optional

STATUSES = ["Backlog", "In Progress", "Blocked", "In Review", "Rework", "Done"]
PRIORITIES = ["Low", "Medium", "High", "Critical"]
COMMENT_KINDS = ["update", "blocker", "decision", "handoff"]
TEST_STATES = ["Not Run", "Running", "Passed", "Failed"]
DOCUMENT_TYPES = ["Requirements", "Architecture Design", "Technical Design", "Test Result",
                  "Security & Compliance", "Release & Runbook", "Department Knowledge"]
DOCUMENT_STATUSES = ["Draft", "Under Review", "Approved", "Rework", "Archived"]
INDEXING_STATES = ["Not Indexed", "Ready", "Needs Review"]
CLASSIFICATIONS = ["Public", "Internal", "Confidential", "Restricted"]

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


def update_contract(conn: sqlite3.Connection, task_id: int, *, test_evidence: Optional[str] = None,
                    risks: Optional[str] = None, decision_ref: Optional[str] = None) -> None:
    task = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if task is None:
        raise LookupError("task not found")
    test_evidence = task["test_evidence"] if test_evidence is None else _text(
        test_evidence, "test evidence", required=False, max_len=MAX_LONG)
    risks = task["risks"] if risks is None else _text(risks, "risks", required=False, max_len=MAX_LONG)
    decision_ref = task["decision_ref"] if decision_ref is None else _text(
        decision_ref, "decision/ADR reference", required=False)
    conn.execute("UPDATE tasks SET test_evidence = ?, risks = ?, decision_ref = ? WHERE id = ?", (
        test_evidence, risks, decision_ref, task_id))
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
        if any(t["status"] == "Rework" for t in tasks):
            state = "Rework"
        elif tasks and total and done == total and all(t["status"] == "Done" for t in tasks):
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


def dashboard_summary(conn: sqlite3.Connection) -> dict[str, Any]:
    """Return task, gate, test, and review totals for the main dashboard."""
    counts = {row["status"]: row["total"] for row in conn.execute(
        "SELECT status, COUNT(*) AS total FROM tasks GROUP BY status")}
    total = sum(counts.values())
    done = counts.get("Done", 0)
    readiness = phase_readiness(conn)
    tests = {row["test_state"]: row["total"] for row in conn.execute(
        "SELECT test_state, COUNT(*) AS total FROM artifact_jobs GROUP BY test_state")}
    return {
        "total": total,
        "done": done,
        "in_progress": counts.get("In Progress", 0),
        "blocked": counts.get("Blocked", 0),
        "progress": int(100 * done / total) if total else 0,
        "ready_phases": sum(1 for phase in readiness if phase["state"] == "Ready"),
        "phase_count": len(readiness),
        "tests_passed": tests.get("Passed", 0),
        "tests_failed": tests.get("Failed", 0),
        "tests_unknown": sum(value for key, value in tests.items() if key not in ("Passed", "Failed")),
        "documents_pending": conn.execute(
            "SELECT COUNT(*) FROM documents WHERE status IN ('Draft', 'Under Review')").fetchone()[0],
    }


def current_work_by_role(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT t.id, t.title, t.responsible_role AS role, t.current_work, t.blockers, p.name AS phase_name"
        " FROM tasks t JOIN phases p ON p.id = t.phase_id WHERE t.status = 'In Progress'"
        " ORDER BY t.responsible_role, t.id").fetchall()
    return [dict(row) for row in rows]


def list_departments(conn: sqlite3.Connection) -> list[str]:
    return [row["name"] for row in conn.execute("SELECT name FROM departments ORDER BY id")]


def list_documents(conn: sqlite3.Connection, *, query: str = "", document_type: str = "",
                   department: str = "", status: str = "", owner_role: str = "",
                   knowledge_only: bool = False) -> list[sqlite3.Row]:
    sql = "SELECT d.*, t.title AS linked_task_title FROM documents d LEFT JOIN tasks t ON t.id = d.linked_task_id WHERE 1=1"
    params: list[Any] = []
    if knowledge_only:
        sql += " AND d.document_type = ?"
        params.append("Department Knowledge")
    if query:
        query = _text(query, "search", required=False, max_len=200)
        pattern = f"%{query}%"
        sql += " AND (d.title LIKE ? OR d.content LIKE ? OR d.source LIKE ? OR d.linked_requirement LIKE ?)"
        params.extend([pattern] * 4)
    if document_type:
        sql += " AND d.document_type = ?"
        params.append(_choice(document_type, "document type", DOCUMENT_TYPES))
    if department:
        sql += " AND d.department = ?"
        params.append(_choice(department, "department", list_departments(conn)))
    if status:
        sql += " AND d.status = ?"
        params.append(_choice(status, "document status", DOCUMENT_STATUSES))
    if owner_role:
        sql += " AND d.owner_role = ?"
        params.append(_role(conn, owner_role, "owner role"))
    sql += " ORDER BY d.department, d.document_type, d.title"
    return conn.execute(sql, params).fetchall()


def get_document(conn: sqlite3.Connection, document_id: int) -> Optional[dict[str, Any]]:
    row = conn.execute(
        "SELECT d.*, t.title AS linked_task_title FROM documents d"
        " LEFT JOIN tasks t ON t.id = d.linked_task_id WHERE d.id = ?", (document_id,)
    ).fetchone()
    if row is None:
        return None
    result = dict(row)
    result["activity"] = conn.execute(
        "SELECT * FROM document_activity WHERE document_id = ? ORDER BY id DESC", (document_id,)
    ).fetchall()
    result["related"] = conn.execute(
        "SELECT id, title, document_type, status FROM documents"
        " WHERE department = ? AND id != ? AND linked_requirement = ? ORDER BY id",
        (result["department"], document_id, result["linked_requirement"]),
    ).fetchall() if result["linked_requirement"] else []
    return result


def create_document(conn: sqlite3.Connection, *, title: str, document_type: str, department: str,
                    owner_role: str, status: str = "Draft", version: str = "1.0",
                    linked_requirement: str = "", linked_task_id: str = "", source: str = "",
                    content: str = "", approver: str = "", classification: str = "Internal",
                    indexing_status: str = "Not Indexed", effective_date: str = "",
                    author: str = "") -> int:
    title = _text(title, "title")
    document_type = _choice(document_type, "document type", DOCUMENT_TYPES)
    department = _choice(department, "department", list_departments(conn))
    owner_role = _role(conn, owner_role, "owner role")
    status = _choice(status, "document status", DOCUMENT_STATUSES)
    classification = _choice(classification, "classification", CLASSIFICATIONS)
    indexing_status = _choice(indexing_status, "indexing status", INDEXING_STATES)
    version = _text(version, "version", max_len=40)
    linked_requirement = _text(linked_requirement, "linked requirement", required=False)
    source = _text(source, "source", required=False, max_len=500)
    content = _text(content, "content", required=False, max_len=MAX_LONG)
    approver = _text(approver, "approver", required=False, max_len=80)
    if status == "Approved" and not approver:
        raise ValidationError("approver is required when registering an approved document")
    effective_date = _text(effective_date, "effective date", required=False, max_len=20)
    linked_task = None
    if linked_task_id:
        if not linked_task_id.isascii() or not linked_task_id.isdigit():
            raise ValidationError("linked task must be a valid id")
        linked_task = int(linked_task_id)
        if not conn.execute("SELECT 1 FROM tasks WHERE id = ?", (linked_task,)).fetchone():
            raise ValidationError("linked task is invalid")
    cur = conn.execute(
        "INSERT INTO documents (title, document_type, department, owner_role, status, version,"
        " linked_requirement, linked_task_id, source, content, approver, classification, indexing_status,"
        " effective_date) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (title, document_type, department, owner_role, status, version, linked_requirement, linked_task,
         source, content, approver, classification, indexing_status, effective_date),
    )
    doc_id = int(cur.lastrowid)
    conn.execute("INSERT INTO document_activity (document_id, author, role, action, note) VALUES (?,?,?,?,?)",
                 (doc_id, _text(author, "author", required=False, max_len=80) or owner_role,
                  owner_role, "created", "Document registered"))
    conn.commit()
    return doc_id


def update_document_status(conn: sqlite3.Connection, document_id: int, *, status: str,
                           approver: Optional[str] = None, author: str = "", role: str = "") -> None:
    status = _choice(status, "document status", DOCUMENT_STATUSES)
    document = conn.execute("SELECT * FROM documents WHERE id = ?", (document_id,)).fetchone()
    if document is None:
        raise LookupError("document not found")
    approver = document["approver"] if approver is None else _text(
        approver, "approver", required=False, max_len=80)
    author = _text(author, "author", required=False, max_len=80) or document["owner_role"]
    role = _role(conn, role or document["owner_role"], "role")
    if status == "Approved" and not approver:
        raise ValidationError("approver is required when approving a document")
    conn.execute(
        "UPDATE documents SET status = ?, approver = ?, indexing_status = ?,"
        " updated_at = strftime('%Y-%m-%d %H:%M:%S', 'now') WHERE id = ?",
        (status, approver, "Ready" if status == "Approved" else "Needs Review", document_id),
    )
    conn.execute("INSERT INTO document_activity (document_id, author, role, action, note) VALUES (?,?,?,?,?)",
                 (document_id, author, role, "status", f"Status changed to {status}"))
    conn.commit()


def knowledge_mode() -> dict[str, str]:
    return {
        "default": "Manual Only",
        "local": "Local AI/RAG Ready (not configured)",
        "cloud": "Cloud AI Disabled / Not Configured",
        "notice": "Manual Only does not send document or query data to any AI service.",
    }


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
