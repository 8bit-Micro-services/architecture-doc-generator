"""SQLite persistence: schema creation and connection helper."""
from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS roles (
    id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, description TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS phases (
    id INTEGER PRIMARY KEY, position INTEGER NOT NULL, name TEXT NOT NULL UNIQUE,
    iso_process TEXT NOT NULL, objective TEXT NOT NULL,
    accountable TEXT NOT NULL, responsible TEXT NOT NULL,
    inputs TEXT NOT NULL, outputs TEXT NOT NULL,
    entry_criteria TEXT NOT NULL, exit_criteria TEXT NOT NULL, artifacts TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    phase_id INTEGER NOT NULL REFERENCES phases(id),
    accountable_role TEXT NOT NULL, responsible_role TEXT NOT NULL,
    consulted_roles TEXT NOT NULL DEFAULT '', informed_roles TEXT NOT NULL DEFAULT '',
    process_owner TEXT NOT NULL DEFAULT '',
    priority TEXT NOT NULL, status TEXT NOT NULL,
    current_work TEXT NOT NULL DEFAULT '', sprint TEXT NOT NULL DEFAULT '',
    blockers TEXT NOT NULL DEFAULT '', requirement_id TEXT NOT NULL DEFAULT '',
    inputs TEXT NOT NULL DEFAULT '', outputs TEXT NOT NULL DEFAULT '',
    acceptance_criteria TEXT NOT NULL DEFAULT '', test_evidence TEXT NOT NULL DEFAULT '',
    risks TEXT NOT NULL DEFAULT '', decision_ref TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS gate_items (
    id INTEGER PRIMARY KEY,
    task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    kind TEXT NOT NULL CHECK (kind IN ('in', 'out')),
    text TEXT NOT NULL, done INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS comments (
    id INTEGER PRIMARY KEY,
    task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    author TEXT NOT NULL, role TEXT NOT NULL, kind TEXT NOT NULL, body TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now'))
);
CREATE TABLE IF NOT EXISTS handoffs (
    id INTEGER PRIMARY KEY,
    task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    from_role TEXT NOT NULL, to_role TEXT NOT NULL, note TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now'))
);
CREATE TABLE IF NOT EXISTS artifact_jobs (
    id INTEGER PRIMARY KEY, name TEXT NOT NULL, input_documents TEXT NOT NULL,
    drawio_output TEXT NOT NULL, image_output TEXT NOT NULL, pptx_output TEXT NOT NULL,
    test_state TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS departments (
    id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    document_type TEXT NOT NULL,
    department TEXT NOT NULL REFERENCES departments(name),
    owner_role TEXT NOT NULL REFERENCES roles(name),
    status TEXT NOT NULL,
    version TEXT NOT NULL,
    linked_requirement TEXT NOT NULL DEFAULT '',
    linked_task_id INTEGER REFERENCES tasks(id),
    source TEXT NOT NULL DEFAULT '',
    content TEXT NOT NULL DEFAULT '',
    approver TEXT NOT NULL DEFAULT '',
    classification TEXT NOT NULL DEFAULT 'Internal',
    indexing_status TEXT NOT NULL DEFAULT 'Not Indexed',
    effective_date TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now'))
);
CREATE TABLE IF NOT EXISTS document_activity (
    id INTEGER PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    author TEXT NOT NULL,
    role TEXT NOT NULL,
    action TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now'))
);
"""


def connect(db_path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: str | Path) -> None:
    """Create the schema and seed a fresh database."""
    from .seed_data import seed

    conn = connect(db_path)
    try:
        conn.executescript(SCHEMA)
        if conn.execute("SELECT COUNT(*) FROM roles").fetchone()[0] == 0:
            seed(conn)
        if conn.execute("SELECT COUNT(*) FROM departments").fetchone()[0] == 0:
            from .seed_data import seed_documents

            seed_documents(conn)
        conn.commit()
    finally:
        conn.close()
