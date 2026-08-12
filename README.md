<div align="center">

# 🤖 AI Mock Interview Bot

**Practice job interviews with an AI coach that adapts to your resume, role, and difficulty level.**

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o--mini-412991?style=for-the-badge&logo=openai&logoColor=white)](https://openai.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

[**✨ Live Demo**](https://moc-interview-bot.vercel.app) · [**📖 API Docs**](https://moc-interview-bot.vercel.app/docs) · [**🐛 Report Bug**](https://github.com/naimasultana553-sys/moc-interview-bot/issues) · [**💡 Request Feature**](https://github.com/naimasultana553-sys/moc-interview-bot/issues)

</div>

---

## 📸 Preview

> A cinematic dark-themed interview experience — upload your resume and start practicing in seconds.

---

## 🌟 What Is This?

**AI Mock Interview Bot** is a full-stack web application that turns your resume into a personalized, interactive interview session. It parses your uploaded PDF or text resume, understands your background, and generates role-specific questions across multiple difficulty levels. After every answer, it scores you across 7 professional dimensions and gives actionable written feedback — just like a real technical interviewer.

No sign-up required. No API key needed to try it (works fully offline with the built-in rule-based engine).

---

## ✨ Features

| Feature | Description |
|---|---|
| 📄 **Smart Resume Parsing** | Upload PDF or TXT — extracts name, skills, projects, certifications, and experience automatically |
| 🎯 **Role-Specific Questions** | 8 target roles including Software Engineer, Data Scientist, Product Manager, DevOps, and more |
| 🎚️ **Difficulty Levels** | Junior · Mid · Senior — tailored question depth per level |
| 🧠 **AI-Powered Evaluation** | GPT-4o-mini scores each answer across 7 dimensions with written feedback |
| 🔁 **Adaptive Follow-Ups** | AI asks a smart follow-up question when your answer needs clarification |
| 📊 **Detailed Report** | Final report with overall score, dimension breakdown, strengths, weaknesses, and rewritten model answers |
| 💾 **Session Persistence** | Sessions survive server restarts — resume your interview on page reload |
| 🌐 **Offline Mode** | Fully functional without an OpenAI key using the built-in rule-based engine |
| 📱 **Responsive UI** | Mobile-friendly dark UI with animated neural network background |
| 🔒 **Privacy First** | All data stays on your server — no accounts, no tracking |

---

## 🏗️ Architecture

```
moc-interview-bot/
├── backend/                    # FastAPI Python backend
│   ├── app/
│   │   ├── main.py             # App entry point + static file serving
│   │   ├── config.py           # Pydantic settings (reads .env)
│   │   ├── models.py           # Pydantic data models
│   │   ├── routers/
│   │   │   ├── resume.py       # POST /api/resume/analyze
│   │   │   └── interview.py    # All interview session endpoints
│   │   └── services/
│   │       ├── ai_client.py    # OpenAI wrapper with graceful offline fallback
│   │       ├── ai_service.py   # AI-or-mock orchestration layer
│   │       ├── mock_engine.py  # Built-in rule-based question bank + scoring
│   │       ├── report_service.py # Final report generation
│   │       ├── resume_service.py # PDF / TXT text extraction (pypdf)
│   │       └── storage.py      # In-memory store + JSON persistence
│   ├── tests/                  # 21 pytest tests
│   ├── requirements.txt        # Runtime dependencies
│   ├── requirements-dev.txt    # Dev / test dependencies
│   ├── .env.example            # Environment variable template
│   └── run_server.ps1          # Windows one-click launcher
└── frontend/
    └── dist/                   # Static SPA (HTML + CSS + JS, no build step)
        ├── index.html
        ├── styles.css
        └── app.js
```

---

## 🚀 Quick Start (Local)

### Prerequisites

- Python **3.11+**
- An OpenAI API key *(optional — the app works fully offline without one)*

### 1. Clone the repository

```bash
git clone https://github.com/naimasultana553-sys/moc-interview-bot.git
cd moc-interview-bot
```

### 2. Set up the backend

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\pip install -r requirements.txt

# macOS / Linux
.venv/bin/pip install -r requirements.txt
```

### 3. Configure environment

```bash
# Windows
Copy-Item .env.example .env

# macOS / Linux
cp .env.example .env
```

Then open `.env` and (optionally) add your OpenAI API key:

```env
OPENAI_API_KEY=sk-...        # Leave empty to use offline mock mode
OPENAI_MODEL=gpt-4o-mini     # Model for AI calls
HOST=127.0.0.1
PORT=8000
```

### 4. Run the server

```powershell
# Windows (one-click)
.\run_server.ps1

# Or manually (Windows / macOS / Linux)
.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### 5. Open in browser

```
http://127.0.0.1:8000
```

> 📖 **Interactive API docs** are available at `http://127.0.0.1:8000/docs`

---

## 🌐 Deploy to Vercel

This project ships with a `vercel.json` configuration. To deploy:

```bash
npm install -g vercel
vercel login
vercel --prod
```

Set the required environment variable in the Vercel dashboard:

| Variable | Value |
|---|---|
| `OPENAI_API_KEY` | Your OpenAI key (or leave blank for mock mode) |
| `OPENAI_MODEL` | `gpt-4o-mini` |
| `CORS_ORIGINS` | `*` |

---

## 📡 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Server status, AI mode, session count |
| `POST` | `/api/resume/analyze` | Upload PDF/TXT resume, get parsed profile |
| `POST` | `/api/interview/{id}/setup` | Configure role, difficulty, question count |
| `GET` | `/api/interview/{id}/next` | Fetch current question |
| `POST` | `/api/interview/{id}/answer` | Submit answer, receive score + feedback |
| `POST` | `/api/interview/{id}/skip` | Skip the current question |
| `POST` | `/api/interview/{id}/finish` | Generate final performance report |
| `GET` | `/api/interview/{id}/report` | Retrieve completed report |
| `GET` | `/api/interview/{id}` | Full session state |

---

## 🧪 Running Tests

```bash
cd backend

# Windows
.venv\Scripts\python -m pytest tests -v

# macOS / Linux
.venv/bin/python -m pytest tests -v
```

The test suite covers 21 scenarios across resume parsing, session management, scoring, and the mock engine.

---

## 🛠️ Tech Stack

**Backend**
- [FastAPI](https://fastapi.tiangolo.com/) — High-performance async Python web framework
- [Pydantic v2](https://docs.pydantic.dev/) — Data validation and settings management
- [Uvicorn](https://www.uvicorn.org/) — Lightning-fast ASGI server
- [pypdf](https://pypdf.readthedocs.io/) — PDF text extraction
- [OpenAI Python SDK](https://github.com/openai/openai-python) — GPT-4o-mini integration

**Frontend**
- Vanilla HTML5 + CSS3 + JavaScript (zero build step, zero dependencies)
- Inter font (Google Fonts)
- Material Symbols icons
- Canvas-based animated neural network background

---

## 🤝 Contributing

Contributions are welcome! Here's how to get started:

1. Fork the repository
2. Create your feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

Please make sure your code passes the existing test suite before submitting.

---

## 📄 License

Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for more information.

---

## 👩‍💻 Author

**Naima Sultana**

[![GitHub](https://img.shields.io/badge/GitHub-naimasultana553--sys-181717?style=flat-square&logo=github)](https://github.com/naimasultana553-sys)

---

<div align="center">

Made with ❤️ and a lot of ☕

**⭐ Star this repo if you found it helpful!**

</div>
