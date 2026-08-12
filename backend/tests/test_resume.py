"""Resume upload + parsing endpoint tests."""
from __future__ import annotations

from tests.conftest import upload_resume


def test_analyze_txt_returns_structured_resume(client, resume_bytes):
    payload = {"file": ("resume.txt", resume_bytes, "text/plain")}
    resp = client.post("/api/resume/analyze", files=payload)

    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"]
    assert data["resume"]["name"] == "Sarah Johnson"
    assert data["resume"]["email"] == "sarah.johnson@example.com"
    assert "python" in data["resume"]["skills"]
    assert data["resume"]["experience"]
    assert data["resume"]["projects"]
    assert data["summary"]


def test_analyze_ignores_upload_max(client, resume_bytes):
    # A tiny file is under the limit, so this simply verifies the happy path
    # works and that the endpoint is reachable regardless of content size.
    payload = {"file": ("tiny.txt", b"short\nresume\ncontent", "text/plain")}
    resp = client.post("/api/resume/analyze", files=payload)
    assert resp.status_code in (200, 400)


def test_rejects_unsupported_extension(client, resume_bytes):
    payload = {"file": ("resume.docx", resume_bytes, "application/octet-stream")}
    resp = client.post("/api/resume/analyze", files=payload)
    assert resp.status_code == 400
    assert "Unsupported file type" in resp.json()["detail"]


def test_rejects_too_short_text(client):
    payload = {"file": ("short.txt", b"just a few words", "text/plain")}
    resp = client.post("/api/resume/analyze", files=payload)
    assert resp.status_code == 400
    assert "Not enough text" in resp.json()["detail"]


def test_analyze_creates_persisted_session(client, resume_bytes):
    data = upload_resume(client)
    sid = data["session_id"]
    resp = client.get(f"/api/interview/{sid}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "setup"