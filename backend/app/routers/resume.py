"""Resume upload + analysis endpoints."""
from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.config import get_settings
from app.models import ResumeAnalysisResult
from app.services import resume_service
from app.services.ai_service import AIService
from app.services.storage import storage

router = APIRouter(prefix="/api/resume", tags=["resume"])

ai_service = AIService()


@router.post("/analyze", response_model=ResumeAnalysisResult)
async def analyze_resume(file: UploadFile = File(...)) -> ResumeAnalysisResult:
    data = await file.read()
    settings = get_settings()
    if len(data) > settings.upload_max_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File too large. Maximum size is {settings.upload_max_mb} MB.")

    text = resume_service.extract_text(data, file.filename or "")
    resume, summary = resume_service.analyze(text, ai_service)
    session = storage.create_session(resume=resume, raw_text=text)
    return ResumeAnalysisResult(
        session_id=session.id,
        resume=resume,
        summary=summary,
        raw_text=text[:3000],
    )
