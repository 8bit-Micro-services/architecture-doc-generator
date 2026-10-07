import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture()
def client(db_path):
    return TestClient(create_app(str(db_path)))


def test_pages_render(client):
    for url in ("/", "/board", "/jobs", "/tasks/3", "/board?role=Developer&status=Blocked"):
        r = client.get(url)
        assert r.status_code == 200, url
    assert "Requirement Intake" in client.get("/").text
    assert "Define canonical IR schema v1" in client.get("/board").text


def test_unknown_task_and_bad_filter(client):
    assert client.get("/tasks/9999").status_code == 404
    assert client.get("/board?role=Nope").status_code == 400


def test_comment_flow_and_escaping(client):
    r = client.post("/tasks/3/comments", data={"author": "<b>Eve</b>", "role": "Developer",
                                                "kind": "update", "body": "<script>alert(1)</script>"})
    assert r.status_code == 200  # redirected to the task page
    assert "<script>alert(1)</script>" not in r.text
    assert "&lt;script&gt;" in r.text


def test_invalid_form_rejected(client):
    r = client.post("/tasks/3/comments", data={"author": "x", "role": "Nobody", "kind": "update", "body": "b"})
    assert r.status_code == 400
    r = client.post("/tasks/3/status", data={"status": "Blocked", "blockers": ""})
    assert r.status_code == 400


def test_create_task_and_handoff(client):
    r = client.post("/tasks", data={"title": "T", "phase_id": "4", "accountable_role": "Technical Lead",
                                    "responsible_role": "Developer", "priority": "High"})
    assert r.status_code == 200 and "<h2>T</h2>" in r.text
    tid = str(r.url).rsplit("/", 1)[1]
    r = client.post(f"/tasks/{tid}/handoff", data={"to_role": "QA Engineer", "note": "go"})
    assert r.status_code == 200 and "Developer &rarr; QA Engineer" in r.text.replace("→", "&rarr;")
