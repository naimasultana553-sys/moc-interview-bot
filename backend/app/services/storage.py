"""In-memory session store with JSON persistence."""
from __future__ import annotations

import json
import logging
from pathlib import Path

from app.config import get_settings
from app.models import InterviewSession, ResumeInfo

logger = logging.getLogger("interview.storage")


class Storage:
    def __init__(self) -> None:
        settings = get_settings()
        self._path = Path(settings.data_dir) / "sessions.json"
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self.sessions: dict[str, InterviewSession] = {}
        self._load()

    def create_session(self, resume: ResumeInfo | None = None, raw_text: str = "") -> InterviewSession:
        session = InterviewSession(resume=resume, raw_text=raw_text)
        self.sessions[session.id] = session
        self._dump()
        return session

    def get(self, session_id: str) -> InterviewSession | None:
        return self.sessions.get(session_id)

    def save(self, session: InterviewSession) -> None:
        self.sessions[session.id] = session
        self._dump()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            for key, raw in data.items():
                self.sessions[key] = InterviewSession.model_validate(raw)
            logger.info("Loaded %d session(s) from %s", len(self.sessions), self._path)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not load persisted sessions (%s); starting fresh", exc)

    def _dump(self) -> None:
        try:
            payload = {sid: s.model_dump(mode="json") for sid, s in self.sessions.items()}
            self._path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not persist sessions: %s", exc)


storage = Storage()
