# AI Mock Interview Bot

A full-stack mock interview coach. Upload your resume, choose a role and
difficulty, and get a personalized interview with instant scoring, adaptive
follow-up questions, and a detailed performance report.

- **Backend**: FastAPI + Pydantic (Python 3.13)
- **Frontend**: static single-page app served from `frontend/dist` (no build step)
- **AI**: OpenAI-backed when an API key is configured, otherwise a fully
  offline rule-based engine so the whole flow works with zero setup or cost.

## Features

- PDF / TXT resume upload with automatic parsing (name, skills, projects,
  experience, certifications, ...)
- Personalized question generation from your actual resume
- 8 role-specific question banks, 4 question types, 3 difficulty levels
- Per-answer scoring across 7 dimensions with written feedback
- Adaptive follow-up questions (max 1 per question)
- Full interview report: overall + dimension scores, strengths, weaknesses,
  recommended practice, better-answer rewrites, and a per-question review
- Sessions persist to `backend/data/sessions.json` and survive server restarts
- Resume your in-progress interview on page reload

## Project layout

```
backend/
  app/
    main.py            FastAPI entry point (serves frontend/dist at /)
    config.py          Settings from .env
    models.py          Pydantic models
    routers/
      resume.py        POST /api/resume/analyze
      interview.py     interview session endpoints
    services/
      ai_client.py     OpenAI wrapper (graceful offline)
      ai_service.py    AI-or-mock orchestration with fallback
      mock_engine.py   rule-based question bank, scoring, feedback
      report_service.py  deterministic report scoring
      resume_service.py  PDF/TXT text extraction
      storage.py       in-memory store + JSON persistence
  tests/               pytest suite (21 tests)
  run_server.ps1       Windows launcher
  requirements.txt     runtime deps
  requirements-dev.txt test deps
frontend/dist/         static UI (served automatically when present)
```

## Setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt       # runtime
.\.venv\Scripts\pip install -r requirements-dev.txt   # optional: tests
Copy-Item .env.example .env                            # then edit if you like
```

`OPENAI_API_KEY` is **optional**. Leave it empty to run the app in offline
"mock" mode — everything (resume parsing, questions, scoring, report) uses the
built-in rule-based engine so you can demo the full flow without tokens.

## Run

```powershell
cd backend
.\run_server.ps1
```

Then open <http://127.0.0.1:8000>.

Or manually:

```powershell
cd backend
.\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Test

```powershell
cd backend
.\.venv\Scripts\python -m pytest tests -q
```

## API overview

| Method | Path                                   | Purpose                          |
| ------ | -------------------------------------- | -------------------------------- |
| GET    | `/api/health`                          | Status + AI mode + session count |
| POST   | `/api/resume/analyze`                  | Upload PDF/TXT, get parsed resume |
| POST   | `/api/interview/{id}/setup`            | Set role/difficulty/count        |
| GET    | `/api/interview/{id}/next`             | Current question                 |
| POST   | `/api/interview/{id}/answer`           | Submit an answer, get score      |
| POST   | `/api/interview/{id}/skip`             | Skip the current question        |
| POST   | `/api/interview/{id}/finish`           | Generate the final report        |
| GET    | `/api/interview/{id}/report`           | Fetch a completed report         |
| GET    | `/api/interview/{id}`                  | Full session state               |

Interactive docs are available at <http://127.0.0.1:8000/docs> while running.
