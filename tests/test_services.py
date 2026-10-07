import pytest

from app import services


def test_seed_roles_phases_tasks(conn):
    assert len(services.list_roles(conn)) == 10
    phases = [p["name"] for p in services.list_phases(conn)]
    assert phases[0] == "Requirement Intake" and phases[-1] == "Operation/Retrospective"
    assert len(phases) == 8
    assert len(services.list_tasks(conn)) >= 10
    assert services.list_jobs(conn)[0]["pptx_output"] == "architecture-presentation.pptx"
    assert conn.execute("SELECT COUNT(*) FROM comments").fetchone()[0] > 0


def test_filters(conn):
    qa = services.list_tasks(conn, role="QA Engineer")
    assert qa and all("QA Engineer" in (t["responsible_role"], t["accountable_role"]) for t in qa)
    assert all(t["status"] == "Blocked" for t in services.list_tasks(conn, status="Blocked"))
    with pytest.raises(services.ValidationError):
        services.list_tasks(conn, role="Hacker")
    with pytest.raises(services.ValidationError):
        services.list_tasks(conn, phase="1; DROP TABLE tasks")


def test_create_task_validation(conn):
    tid = services.create_task(conn, title="New", phase_id="1", accountable_role="Product Owner",
                               responsible_role="Developer")
    assert services.get_task(conn, tid)["status"] == "Backlog"
    with pytest.raises(services.ValidationError):
        services.create_task(conn, title=" ", phase_id="1", accountable_role="Product Owner",
                             responsible_role="Developer")
    with pytest.raises(services.ValidationError):
        services.create_task(conn, title="x", phase_id="999", accountable_role="Product Owner",
                             responsible_role="Developer")


def test_status_rules(conn):
    with pytest.raises(services.ValidationError):
        services.update_status(conn, 6, "Blocked", blockers="")
    services.update_status(conn, 6, "Blocked", blockers="waiting")
    assert services.get_task(conn, 6)["blockers"] == "waiting"
    with pytest.raises(services.ValidationError):  # gate-out unmet
        services.update_status(conn, 6, "Done")
    with pytest.raises(services.ValidationError):
        services.update_status(conn, 6, "Bogus")
    with pytest.raises(LookupError):
        services.update_status(conn, 9999, "Done")


def test_done_after_gate_out(conn):
    for g in services.get_task(conn, 6)["gate_out"]:
        services.set_gate_item(conn, 6, g["id"], True)
    services.update_status(conn, 6, "Done")
    assert services.get_task(conn, 6)["status"] == "Done"


def test_comment_and_handoff(conn):
    services.add_comment(conn, 5, author="Nok", role="Developer", kind="update", body="Working")
    assert services.get_task(conn, 5)["comments"][0]["body"] == "Working"
    with pytest.raises(services.ValidationError):
        services.add_comment(conn, 5, author="", role="Developer", kind="update", body="x")
    services.record_handoff(conn, 5, to_role="QA Engineer", note="ready for test", author="Nok")
    task = services.get_task(conn, 5)
    assert task["responsible_role"] == "QA Engineer"
    assert task["handoffs"][0]["to_role"] == "QA Engineer"
    assert task["comments"][0]["kind"] == "handoff"
    with pytest.raises(services.ValidationError):
        services.record_handoff(conn, 5, to_role="QA Engineer", note="again")


def test_readiness_and_jobs(conn):
    ready = {r["phase"]["name"]: r for r in services.phase_readiness(conn)}
    assert ready["Requirement Intake"]["state"] == "Ready"
    assert ready["Integration/E2E Test"]["state"] == "At Risk"
    assert ready["UAT"]["state"] == "Not Started"
    jid = services.create_job(conn, name="Job", input_documents="a.yaml")
    services.update_job_state(conn, jid, "Passed")
    assert [j for j in services.list_jobs(conn) if j["id"] == jid][0]["test_state"] == "Passed"
    with pytest.raises(services.ValidationError):
        services.update_job_state(conn, jid, "Maybe")


def test_status_preserves_fields_and_done_clears_blockers(conn):
    before = services.get_task(conn, 5)
    services.update_status(conn, 5, "In Review")
    after = services.get_task(conn, 5)
    assert after["blockers"] == before["blockers"] and after["current_work"] == before["current_work"]
    for g in after["gate_out"]:
        services.set_gate_item(conn, 5, g["id"], True)
    services.update_status(conn, 5, "Done")
    assert services.get_task(conn, 5)["blockers"] == ""


def test_update_contract_and_gate_mismatch(conn):
    services.update_contract(conn, 3, test_evidence="ok", risks="r", decision_ref="ADR-9")
    assert services.get_task(conn, 3)["decision_ref"] == "ADR-9"
    gate_id = services.get_task(conn, 3)["gate_in"][0]["id"]
    with pytest.raises(LookupError):
        services.set_gate_item(conn, 4, gate_id, True)
    with pytest.raises(services.ValidationError):
        services.list_tasks(conn, phase="²")


def test_dashboard_summary_and_current_work(conn):
    summary = services.dashboard_summary(conn)
    assert summary["total"] == 13
    assert summary["done"] == 3
    assert summary["progress"] == 23
    assert summary["blocked"] == 1
    assert summary["documents_pending"] > 0
    work = services.current_work_by_role(conn)
    assert work and all(item["role"] and item["title"] for item in work)
    conn.execute("UPDATE tasks SET status = 'Rework' WHERE id = 3")
    assert next(r for r in services.phase_readiness(conn) if r["phase"]["name"] == "Design")["state"] == "Rework"


def test_document_search_department_and_create(conn):
    hr_docs = services.list_documents(conn, query="demo", department="HR", knowledge_only=True)
    assert hr_docs and all(doc["department"] == "HR" for doc in hr_docs)
    assert services.list_documents(conn, query="leave", department="Finance", knowledge_only=True) == []
    assert {doc["department"] for doc in services.list_documents(conn, document_type="Architecture Design")} == {
        "IT/Engineering"
    }
    doc_id = services.create_document(
        conn, title="Procedure", document_type="Department Knowledge", department="HR",
        owner_role="Business Analyst", source="hr/procedure.md", content="Demo only",
    )
    assert services.get_document(conn, doc_id)["activity"][0]["action"] == "created"
    with pytest.raises(services.ValidationError):
        services.create_document(
            conn, title="Bad", document_type="Department Knowledge", department="Unknown",
            owner_role="Business Analyst",
        )
    with pytest.raises(services.ValidationError):
        services.create_document(
            conn, title="Unapproved", document_type="Requirements", department="IT/Engineering",
            owner_role="Business Analyst", status="Approved",
        )


def test_document_approval_requires_approver(conn):
    doc = services.list_documents(conn)[0]
    with pytest.raises(services.ValidationError):
        services.update_document_status(conn, doc["id"], status="Approved")
    services.update_document_status(conn, doc["id"], status="Approved", approver="Architect")
    assert services.get_document(conn, doc["id"])["approver"] == "Architect"
