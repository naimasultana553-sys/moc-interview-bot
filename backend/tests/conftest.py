"""Pytest shared fixtures.

Configures an isolated data directory and an all-off (mock) AI mode BEFORE
importing the app, so tests never touch real sessions or call an LLM.
"""
from __future__ import annotations

import os
import tempfile

_TMP = tempfile.mkdtemp(prefix="moc_test_")
os.environ["DATA_DIR"] = _TMP
os.environ["OPENAI_API_KEY"] = ""

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

SAMPLE_RESUME = """Sarah Johnson
sarah.johnson@example.com
+1 555-123-4567
San Francisco, CA | github.com/sarahj | linkedin.com/in/sarahjohnson

SUMMARY
Software engineer with 4 years of experience building web applications. Strong background in Python, JavaScript, and React with a focus on machine learning.

EDUCATION
B.Sc. Computer Science, University of California, 2019

SKILLS
Python, JavaScript, TypeScript, React, Node.js, Django, PostgreSQL, MongoDB, Redis, Docker, Kubernetes, AWS, Git

PROGRAMMING LANGUAGES
Python, JavaScript, TypeScript, SQL

PROJECTS
AI Resume Parser - Built a document parsing pipeline with Python, Django, and PostgreSQL. Used NLP techniques and deployed with Docker on AWS.

EXPERIENCE
Backend Engineer, TechCorp, 2022 - Present
- Designed and built REST APIs serving 50k daily active users
- Reduced API latency by 40% by introducing Redis caching
Software Engineer, DataWorks, 2019 - 2022
- Built ETL pipelines in Python processing 2M records daily

CERTIFICATIONS
AWS Certified Solutions Architect
"""

CANNED_ANSWER = (
    "I approached this by first clarifying the requirements, then breaking the problem "
    "into smaller parts. I designed a solution using Python and analyzed the trade-offs, "
    "testing different approaches and measuring the results against our acceptance "
    "criteria. The main challenge was handling edge cases, which I solved by iterating "
    "quickly with my team and keeping a shared log of decisions, and I documented the "
    "whole thing so it could be reused in similar projects."
)


@pytest.fixture(scope="session")
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def resume_bytes() -> bytes:
    return SAMPLE_RESUME.encode("utf-8")


def upload_resume(client: TestClient) -> dict:
    payload = {"file": ("sample.txt", SAMPLE_RESUME.encode("utf-8"), "text/plain")}
    resp = client.post("/api/resume/analyze", files=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()


@pytest.fixture()
def session_id(client: TestClient) -> str:
    return upload_resume(client)["session_id"]