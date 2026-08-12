from fastapi.testclient import TestClient

from tests.conftest import CANNED_ANSWER, upload_resume


def test_health_endpoint(client: TestClient):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["ai_mode"] == "mock"
    assert isinstance(body["sessions"], int)


def test_full_flow_report_fields(client: TestClient):
    sid = upload_resume(client)["session_id"]
    setup = client.post(
        f"/api/interview/{sid}/setup",
        json={"job_role": "Machine Learning Engineer", "difficulty": "hard", "num_questions": 4},
    )
    assert setup.status_code == 200

    for _ in range(30):
        nxt = client.get(f"/api/interview/{sid}/next").json()["next"]
        if nxt is None:
            break
        result = client.post(
            f"/api/interview/{sid}/answer",
            json={"question_id": nxt["question"]["id"], "answer": CANNED_ANSWER},
        ).json()
        if result["report_ready"]:
            break

    finish = client.post(f"/api/interview/{sid}/finish")
    assert finish.status_code == 200
    report = finish.json()["report"]

    expected = {
        "overall_score",
        "technical_score",
        "communication_score",
        "problem_solving_score",
        "behavioral_score",
        "resume_relevance",
        "questions_answered",
        "questions_total",
        "skipped_count",
        "strengths",
        "weaknesses",
        "improvements",
        "better_answers",
        "recommended_practice",
        "question_results",
    }
    assert expected.issubset(set(report.keys()))
    assert report["questions_total"] == report["questions_answered"] + report["skipped_count"]