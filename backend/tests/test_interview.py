"""Interview flow tests: setup, answer, skip, follow-up cap, report."""
from __future__ import annotations

import pytest

from tests.conftest import CANNED_ANSWER

SETUP = {"job_role": "Backend Developer", "difficulty": "medium", "num_questions": 5}


def _setup(client, session_id, **overrides):
    payload = {**SETUP, **overrides}
    resp = client.post(f"/api/interview/{session_id}/setup", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()


def _next(client, session_id):
    resp = client.get(f"/api/interview/{session_id}/next")
    assert resp.status_code == 200
    return resp.json()


def _answer(client, session_id, question_id, answer=CANNED_ANSWER):
    resp = client.post(
        f"/api/interview/{session_id}/answer",
        json={"question_id": question_id, "answer": answer},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def _finish(client, session_id):
    resp = client.post(f"/api/interview/{session_id}/finish")
    assert resp.status_code == 200, resp.text
    return resp.json()["report"]


def test_setup_returns_first_question(client, session_id):
    data = _setup(client, session_id)
    assert data["next"] is not None
    assert data["next"]["question"]["text"]
    assert data["next"]["question_number"] == 1
    assert data["next"]["total"] == 5


def test_next_matches_setup(client, session_id):
    _setup(client, session_id)
    data = _next(client, session_id)
    assert data["next"]["question_number"] == 1
    assert data["next"]["question"]["id"]


def test_answer_moves_to_next_question(client, session_id):
    _setup(client, session_id)
    qid = _next(client, session_id)["next"]["question"]["id"]
    data = _answer(client, session_id, qid)
    assert data["evaluation"]["score"] >= 0.0
    assert data["next"]["question_number"] == 2


def test_answer_with_wrong_question_id_400(client, session_id):
    _setup(client, session_id)
    resp = client.post(
        f"/api/interview/{session_id}/answer",
        json={"question_id": "does-not-exist", "answer": "something"},
    )
    assert resp.status_code == 400


def test_answer_when_not_in_progress_400(client, session_id):
    resp = client.post(
        f"/api/interview/{session_id}/answer",
        json={"question_id": "whatever", "answer": "something"},
    )
    assert resp.status_code == 400


def test_interview_terminates_with_bounded_followups(client, session_id):
    """The mock engine must not grow follow-ups without bound.

    Each base question may spawn at most one follow-up, so the total number of
    questions must stay <= 2 * num_questions and the flow must reach a report.
    """
    _setup(client, session_id)
    max_total = 0
    iterations = 0
    report_ready = False
    qid = None

    while iterations < 30:
        iterations += 1
        data = _next(client, session_id)
        nxt = data["next"]
        if nxt is None:
            break
        max_total = max(max_total, nxt["total"])
        qid = nxt["question"]["id"]
        result = _answer(client, session_id, qid)
        if result["report_ready"]:
            report_ready = True
            break

    assert report_ready, f"never reached report_ready in {iterations} iterations"
    assert max_total <= 2 * SETUP["num_questions"], f"follow-up explosion: total={max_total}"


def test_report_after_full_interview(client, session_id):
    _setup(client, session_id)
    for _ in range(20):
        data = _next(client, session_id)
        if data["next"] is None:
            break
        result = _answer(client, session_id, data["next"]["question"]["id"])
        if result["report_ready"]:
            break

    report = _finish(client, session_id)
    assert report["overall_score"] >= 0.0
    assert report["questions_answered"] >= 1
    assert report["question_results"]
    assert "strengths" in report
    assert "weaknesses" in report

    # Completed sessions reject re-setup.
    resp = client.post(f"/api/interview/{session_id}/setup", json=SETUP)
    assert resp.status_code == 400


def test_report_not_ready_before_finish(client, session_id):
    resp = client.get(f"/api/interview/{session_id}/report")
    assert resp.status_code == 404


def test_skip_counts_in_report(client, session_id):
    _setup(client, session_id, num_questions=3)
    qid = _next(client, session_id)["next"]["question"]["id"]

    resp = client.post(f"/api/interview/{session_id}/skip", json={"question_id": qid})
    assert resp.status_code == 200, resp.text
    assert resp.json()["next"]["question_number"] == 2

    # Skip the remaining two to keep the test fast and deterministic.
    for _ in range(2):
        data = _next(client, session_id)
        if data["next"] is None:
            break
        client.post(
            f"/api/interview/{session_id}/skip",
            json={"question_id": data["next"]["question"]["id"]},
        )

    report = _finish(client, session_id)
    assert report["skipped_count"] == 3
    assert report["questions_answered"] == 0


def test_get_session_shape(client, session_id):
    _setup(client, session_id)
    resp = client.get(f"/api/interview/{session_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "in_progress"
    assert body["job_role"] == SETUP["job_role"]
    assert body["difficulty"] == SETUP["difficulty"]
    assert body["questions"]
    assert body["ai_mode"] == "mock"


def test_unknown_session_404(client):
    resp = client.get("/api/interview/does-not-exist")
    assert resp.status_code == 404
    resp = client.post("/api/interview/does-not-exist/setup", json=SETUP)
    assert resp.status_code == 404


@pytest.mark.parametrize("difficulty", ["easy", "medium", "hard"])
def test_all_difficulties_supported(client, session_id, difficulty):
    data = _setup(client, session_id, difficulty=difficulty)
    assert data["next"]["question"]["difficulty"] in ("easy", "medium", "hard")