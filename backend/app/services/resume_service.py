"""Resume upload parsing (PDF/TXT) and analysis orchestration."""
from __future__ import annotations

from io import BytesIO

from fastapi import HTTPException

from app.services.ai_service import AIService

SUPPORTED_EXTS = {"pdf", "txt"}


def extract_text(data: bytes, filename: str) -> str:
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if ext not in SUPPORTED_EXTS:
        raise HTTPException(status_code=400, detail="Unsupported file type. Please upload a PDF or TXT resume.")

    if ext == "txt":
        try:
            text = data.decode("utf-8", errors="ignore")
        except Exception:  # noqa: BLE001
            text = ""
    else:
        try:
            from pypdf import PdfReader

            reader = PdfReader(BytesIO(data))
            text = "\n".join((page.extract_text() or "") for page in reader.pages)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=f"Could not read the PDF file: {exc}") from exc

    text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    if len(text) < 30:
        raise HTTPException(
            status_code=400,
            detail="Not enough text could be extracted from this resume. "
            "If it is a scanned/image PDF, please provide a text-based PDF or a plain-text resume.",
        )
    return text[:20000]


def analyze(text: str, ai: AIService) -> tuple:
    return ai.analyze_resume(text)
