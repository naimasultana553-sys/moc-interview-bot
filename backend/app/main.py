"""AI Mock Interview Bot — FastAPI application entry point."""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.routers import interview, resume
from app.services.storage import storage

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

settings = get_settings()

app = FastAPI(
    title="AI Mock Interview Bot",
    description="Practice job interviews with an AI interviewer that adapts to your CV, role, and difficulty.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(resume.router)
app.include_router(interview.router)


@app.get("/api/health")
async def health() -> dict:
    return {
        "status": "ok",
        "ai_mode": interview.ai_service.mode,
        "sessions": len(storage.sessions),
    }


DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if DIST.exists():
    app.mount("/", StaticFiles(directory=str(DIST), html=True), name="frontend")
