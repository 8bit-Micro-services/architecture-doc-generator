"""Seed data: roles, ISO-aligned phase definitions, representative tasks."""
from __future__ import annotations

import sqlite3

ROLES: list[tuple[str, str]] = [
    ("Product Owner", "Owns business value, priority and acceptance; signs off UAT."),
    ("Business Analyst", "Analyses needs, writes user stories and process flows."),
    ("Scrum Master", "Facilitates Scrum, removes blockers, guards sprint readiness."),
    ("Solution Architect", "Owns system architecture, integration, security design and ADRs."),
    ("Technical Lead", "Owns module/API design, code standards, test strategy and PR approval."),
    ("Developer", "Builds parsers, IR model, generators and tests; delivers evidence."),
    ("QA Engineer", "Designs and executes tests, E2E validation, reports defects."),
    ("DevOps Engineer", "Owns CI/CD, environments, deployment and monitoring."),
    ("Security Reviewer", "Threat modelling, dependency/secret scanning, security gate."),
    ("Technical Writer", "README, user guide, API docs and runbooks."),
]

# name, iso_process, objective, accountable, responsible, inputs, outputs, entry, exit, artifacts
# list fields are newline-separated.
PHASES: list[tuple[str, ...]] = [
    ("Requirement Intake", "ISO/IEC/IEEE 12207 Stakeholder needs & requirements definition",
     "Turn stakeholder requests into measurable scope.",
     "Product Owner", "Business Analyst",
     "Stakeholder request\nSample input files\nBusiness problem",
     "Business Requirement Document (BRD)\nUser journey\nInitial backlog",
     "A clear business request exists",
     "PO confirms requirement has value and is in scope",
     "docs/requirements/BRD.md\ndocs/requirements/glossary.md"),
    ("Refinement", "ISO/IEC/IEEE 29148 Requirements engineering",
     "Make stories ready for a sprint (Definition of Ready).",
     "Product Owner", "Business Analyst",
     "BRD\nInitial backlog",
     "Prioritised backlog\nAcceptance criteria\nTest scenarios",
     "Requirement confirmed by PO",
     "Stories pass Definition of Ready",
     "Product backlog\nAcceptance criteria"),
    ("Design", "ISO/IEC/IEEE 42010 Architecture description / 12207 Design definition",
     "Design architecture and technical contracts before coding.",
     "Solution Architect", "Technical Lead",
     "Approved stories\nAcceptance criteria\nConstraints",
     "Architecture document\nADRs\nParser/generator contracts\nTest strategy\nThreat model",
     "Sprint backlog is ready (stories pass DoR)",
     "Architect and Technical Lead approve design; QA reviewed testability",
     "docs/architecture/\ndocs/adr/\ndocs/specs/"),
    ("Development", "ISO/IEC/IEEE 12207 Implementation",
     "Implement modules per design with tests and peer review.",
     "Technical Lead", "Developer",
     "Approved design\nStories\nTest cases",
     "Source code\nUnit tests\nBuild artifact\nModule docs",
     "Design gate passed",
     "PR approved, CI green, ready for integration",
     "src/\ntests/unit/"),
    ("Integration/E2E Test", "ISO/IEC/IEEE 29119 Software testing / 12207 Verification",
     "Verify modules work together from input to output.",
     "QA Engineer", "QA Engineer",
     "CI-passing build\nTest data\nAcceptance criteria",
     "Test report\nDefect tickets\nQuality dashboard",
     "All modules pass unit tests",
     "No critical/high defects and E2E scenarios pass",
     "tests/e2e/\ntests/reports/"),
    ("UAT", "ISO/IEC/IEEE 12207 Validation",
     "Business confirms the system meets user needs.",
     "Product Owner", "QA Engineer",
     "Staging environment\nQA report\nUAT scenarios",
     "UAT sign-off or change list",
     "QA gate passed",
     "PO accepts the release",
     "UAT sign-off record"),
    ("Release", "ISO/IEC/IEEE 12207 Transition",
     "Deploy safely with rollback and monitoring.",
     "DevOps Engineer", "DevOps Engineer",
     "UAT sign-off\nRelease notes\nDeployment plan",
     "Deployment evidence\nRelease tag\nRunbook",
     "UAT passed and release checklist complete",
     "Smoke test passes and monitoring is active",
     "docs/runbooks/\ndocs/releases/"),
    ("Operation/Retrospective", "ISO/IEC/IEEE 12207 Operation & Maintenance / continual improvement",
     "Operate, learn and feed improvements back into the backlog.",
     "Scrum Master", "Scrum Master",
     "Production metrics\nIncidents\nUser feedback",
     "Improvement backlog\nIncident report\nUpdated runbook",
     "Production release completed",
     "Lessons learned added to backlog with owners",
     "Retrospective notes"),
]

# title, phase, accountable, responsible, priority, status, current_work, sprint, blockers,
# req, inputs, outputs, acceptance, evidence, risks, decision, consulted, informed, gate_in, gate_out
TASKS: list[dict] = [
    dict(title="Capture requirement: multi-document architecture generator", phase="Requirement Intake",
         acc="Product Owner", resp="Business Analyst", priority="High", status="Done",
         work="BRD approved by PO.", sprint="Sprint 1", blockers="", req="REQ-001",
         inputs="Stakeholder request; sample OpenAPI files", outputs="docs/requirements/BRD.md",
         acceptance="PO confirms scope", evidence="BRD review recorded 2025-01-06", risks="Scope creep across formats",
         decision="", gate_in=[("Clear business request exists", 1)],
         gate_out=[("PO confirms value and scope", 1)]),
    dict(title="Refine backlog and Definition of Ready", phase="Refinement",
         acc="Product Owner", resp="Business Analyst", priority="High", status="Done",
         work="Stories split and estimated.", sprint="Sprint 1", blockers="", req="REQ-001",
         inputs="BRD", outputs="Prioritised backlog; acceptance criteria",
         acceptance="Every story has acceptance criteria and test scenario", evidence="",
         risks="", decision="", gate_in=[("Requirement confirmed by PO", 1)],
         gate_out=[("Stories pass DoR", 1)]),
    dict(title="Define canonical IR schema v1", phase="Design",
         acc="Solution Architect", resp="Technical Lead", priority="High", status="In Review",
         work="Drafting architecture-ir.schema.json and ADR-001.", sprint="Sprint 1", blockers="",
         req="REQ-002", inputs="Approved stories; parser requirements",
         outputs="schemas/architecture-ir.schema.json; docs/adr/ADR-001-ir-schema.md",
         acceptance="Schema versioned with validation rules", evidence="",
         risks="Schema too rigid for Terraform", decision="ADR-001",
         gate_in=[("Sprint backlog ready", 1)],
         gate_out=[("Architect approves", 0), ("QA reviewed testability", 0)]),
    dict(title="Threat model for file ingestion", phase="Design",
         acc="Solution Architect", resp="Security Reviewer", priority="High", status="In Progress",
         work="Enumerating path traversal and malicious file risks.", sprint="Sprint 1", blockers="",
         req="REQ-003", inputs="Architecture draft", outputs="docs/security/threat-model.md",
         acceptance="Controls listed for each threat", evidence="", risks="Untrusted YAML parsing",
         decision="", gate_in=[("Architecture draft exists", 1)],
         gate_out=[("Threats have controls", 0)]),
    dict(title="Implement OpenAPI parser to IR", phase="Development",
         acc="Technical Lead", resp="Developer", priority="High", status="In Progress",
         work="Parsing paths and servers into IR components.", sprint="Sprint 1", blockers="Waiting for IR schema approval",
         req="REQ-002", inputs="IR schema; sample OpenAPI", outputs="OpenAPI -> IR parser + unit tests",
         acceptance="Sample spec yields valid IR", evidence="", risks="Large specs slow",
         decision="ADR-001", gate_in=[("Design gate passed", 0)],
         gate_out=[("PR approved", 0), ("CI green", 0)]),
    dict(title="Implement Draw.io generator", phase="Development",
         acc="Technical Lead", resp="Developer", priority="High", status="Backlog",
         work="Not started.", sprint="Sprint 2", blockers="", req="REQ-004",
         inputs="Valid IR", outputs="architecture.drawio",
         acceptance="Output opens in Draw.io", evidence="", risks="Layout quality",
         decision="", gate_in=[("IR parser merged", 0)], gate_out=[("PR approved", 0)]),
    dict(title="Implement PPTX generator", phase="Development",
         acc="Technical Lead", resp="Developer", priority="Medium", status="Backlog",
         work="Not started.", sprint="Sprint 2", blockers="", req="REQ-005",
         inputs="Diagram image; IR metadata", outputs="architecture-presentation.pptx",
         acceptance="PPTX opens with embedded diagram", evidence="", risks="Image fidelity",
         decision="", gate_in=[("Draw.io exporter available", 0)], gate_out=[("PR approved", 0)]),
    dict(title="Set up CI pipeline", phase="Development",
         acc="Technical Lead", resp="DevOps Engineer", priority="Medium", status="Done",
         work="GitHub Actions runs tests on every PR.", sprint="Sprint 1", blockers="", req="REQ-006",
         inputs="Repository", outputs=".github/workflows/ci.yml",
         acceptance="CI green on main", evidence="CI run #1 passed", risks="",
         decision="", gate_in=[("Repository exists", 1)], gate_out=[("CI runs tests", 1)]),
    dict(title="E2E test: OpenAPI to Draw.io to PPTX", phase="Integration/E2E Test",
         acc="QA Engineer", resp="QA Engineer", priority="High", status="Backlog",
         work="Writing scenarios E2E-001..006.", sprint="Sprint 2", blockers="", req="REQ-007",
         inputs="CI build; fixtures", outputs="tests/reports/e2e-report.md",
         acceptance="All critical scenarios pass", evidence="", risks="Fixture coverage",
         decision="", gate_in=[("Modules pass unit tests", 0)], gate_out=[("No critical defects", 0)]),
    dict(title="Security review of dependencies and secrets", phase="Integration/E2E Test",
         acc="Security Reviewer", resp="Security Reviewer", priority="High", status="Blocked",
         work="Scan prepared.", sprint="Sprint 2", blockers="Needs a frozen dependency list",
         req="REQ-003", inputs="Dependency list; source", outputs="Security gate report",
         acceptance="No unresolved critical/high findings", evidence="", risks="Transitive vulnerabilities",
         decision="", gate_in=[("Build available", 0)], gate_out=[("Security gate approved", 0)]),
    dict(title="UAT with Solution Architects", phase="UAT",
         acc="Product Owner", resp="QA Engineer", priority="Medium", status="Backlog",
         work="Planning scenarios.", sprint="Sprint 3", blockers="", req="REQ-001",
         inputs="Staging environment; QA report", outputs="UAT sign-off",
         acceptance="PO accepts output quality", evidence="", risks="Late feedback",
         decision="", gate_in=[("QA gate passed", 0)], gate_out=[("PO sign-off", 0)]),
    dict(title="Release notes and deployment runbook", phase="Release",
         acc="DevOps Engineer", resp="Technical Writer", priority="Medium", status="Backlog",
         work="Outline drafted.", sprint="Sprint 3", blockers="", req="REQ-008",
         inputs="UAT sign-off; deployment plan", outputs="docs/runbooks/deploy.md; release notes",
         acceptance="Runbook includes rollback", evidence="", risks="",
         decision="", gate_in=[("UAT passed", 0)], gate_out=[("Rollback plan tested", 0)]),
    dict(title="Sprint retrospective and improvement backlog", phase="Operation/Retrospective",
         acc="Scrum Master", resp="Scrum Master", priority="Low", status="Backlog",
         work="Scheduled after Sprint Review.", sprint="Sprint 1", blockers="", req="REQ-009",
         inputs="Metrics; feedback", outputs="Improvement backlog",
         acceptance="Actions have owners", evidence="", risks="",
         decision="", gate_in=[("Release completed", 0)], gate_out=[("Actions have owners", 0)]),
]

COMMENTS: list[tuple[int, str, str, str, str]] = [
    (3, "Somchai", "Technical Lead", "update", "Drafting IR schema; reviewing with the architect today."),
    (4, "Mali", "Security Reviewer", "update", "Working on path traversal and YAML bomb threats."),
    (5, "Nok", "Developer", "blocker", "Cannot finalise component mapping until IR schema is approved."),
    (5, "Somchai", "Technical Lead", "decision", "Use ADR-001 canonical IR as the parser output contract."),
    (10, "Mali", "Security Reviewer", "blocker", "Need a frozen dependency list before scanning."),
]

JOBS: list[tuple[str, str, str, str, str, str]] = [
    ("Payment Platform architecture generation",
     "openapi.yaml, deployment.yaml, main.tf",
     "architecture.drawio", "architecture.png", "architecture-presentation.pptx", "Not Run"),
]


def seed(conn: sqlite3.Connection) -> None:
    conn.executemany("INSERT INTO roles (name, description) VALUES (?, ?)", ROLES)
    for pos, p in enumerate(PHASES, start=1):
        conn.execute(
            "INSERT INTO phases (position, name, iso_process, objective, accountable, responsible,"
            " inputs, outputs, entry_criteria, exit_criteria, artifacts) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (pos, *p),
        )
    phase_ids = {r["name"]: r["id"] for r in conn.execute("SELECT id, name FROM phases")}
    for t in TASKS:
        cur = conn.execute(
            "INSERT INTO tasks (title, phase_id, accountable_role, responsible_role, consulted_roles,"
            " informed_roles, process_owner, priority, status, current_work, sprint, blockers,"
            " requirement_id, inputs, outputs, acceptance_criteria, test_evidence, risks, decision_ref)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (t["title"], phase_ids[t["phase"]], t["acc"], t["resp"], "Technical Lead, QA Engineer",
             "Product Owner, Scrum Master", t["acc"], t["priority"], t["status"], t["work"],
             t["sprint"], t["blockers"], t["req"], t["inputs"], t["outputs"], t["acceptance"],
             t["evidence"], t["risks"], t["decision"]),
        )
        for kind, items in (("in", t["gate_in"]), ("out", t["gate_out"])):
            for text, done in items:
                conn.execute("INSERT INTO gate_items (task_id, kind, text, done) VALUES (?,?,?,?)",
                             (cur.lastrowid, kind, text, done))
    conn.executemany("INSERT INTO comments (task_id, author, role, kind, body) VALUES (?,?,?,?,?)", COMMENTS)
    conn.executemany(
        "INSERT INTO artifact_jobs (name, input_documents, drawio_output, image_output, pptx_output,"
        " test_state) VALUES (?,?,?,?,?,?)", JOBS)
