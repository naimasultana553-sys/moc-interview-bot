"""Interview session management endpoints."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.models import AnswerEvaluation, InterviewSession, Question
from app.services.ai_service import AIService
from app.services.report_service import build_report
from app.services.storage import storage

router = APIRouter(prefix="/api/interview", tags=["interview"])

ai_service = AIService()


# ---------------------------------------------------------------------------
# Request/response schemas
# ---------------------------------------------------------------------------


class SetupRequest(BaseModel):
    job_role: str
    difficulty: str = "medium"
    num_questions: int = 8


class AnswerRequest(BaseModel):
    question_id: str
    answer: str = Field(..., min_length=1)


class SkipRequest(BaseModel):
    question_id: str


class NextQuestion(BaseModel):
    question: Question
    question_number: int
    total: int
    answered_count: int
    is_follow_up: bool
    follow_up_for: str | None
    done: bool


class EvaluationOut(BaseModel):
    question_id: str
    score: float
    explanation: str
    dimensions: dict[str, float]
    follow_up: Question | None


class AnswerResponse(BaseModel):
    evaluation: EvaluationOut
    next: NextQuestion | None
    report_ready: bool


class NextResponse(BaseModel):
    next: NextQuestion | None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_session(session_id: str) -> InterviewSession:
    session = storage.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Interview session not found.")
    return session


def _next_payload(session: InterviewSession) -> NextQuestion | None:
    q = session.current_question()
    if q is None:
        return None
    return NextQuestion(
        question=q,
        question_number=session.pointer + 1,
        total=session.total(),
        answered_count=session.answered_count(),
        is_follow_up=q.follow_up_for is not None,
        follow_up_for=q.follow_up_for,
        done=False,
    )


def _existing_follow_up(session: InterviewSession, parent_id: str) -> Question | None:
    for q in session.questions:
        if q.follow_up_for == parent_id:
            return q
    return None


MAX_FOLLOWUP_DEPTH = 1


def _follow_up_depth(session: InterviewSession, question_id: str) -> int:
    depth = 0
    seen: set[str] = set()
    current = question_id
    while current and current not in seen:
        seen.add(current)
        q = session.find_question(current)
        if q and q.follow_up_for:
            depth += 1
            current = q.follow_up_for
        else:
            break
    return depth


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/{session_id}/setup", response_model=NextResponse)
async def setup_interview(session_id: str, payload: SetupRequest) -> NextResponse:
    session = _get_session(session_id)
    if session.status == "completed":
        raise HTTPException(status_code=400, detail="This interview has already been completed.")

    session.job_role = payload.job_role.strip()
    session.difficulty = payload.difficulty.lower()
    count = max(3, min(12, payload.num_questions or 8))

    if session.status != "in_progress" or not session.questions:
        questions = ai_service.generate_questions(session.resume, session.job_role, session.difficulty, count)
        session.questions = questions
        session.question_order = [q.id for q in questions]
        session.pointer = 0

    session.status = "in_progress"
    storage.save(session)
    return NextResponse(next=_next_payload(session))


@router.get("/{session_id}/next", response_model=NextResponse)
async def get_next(session_id: str) -> NextResponse:
    session = _get_session(session_id)
    return NextResponse(next=_next_payload(session))


@router.post("/{session_id}/answer", response_model=AnswerResponse)
async def submit_answer(session_id: str, payload: AnswerRequest) -> AnswerResponse:
    session = _get_session(session_id)
    if session.status != "in_progress":
        raise HTTPException(status_code=400, detail="Interview is not in progress.")

    current = session.current_question()
    if current is None:
        raise HTTPException(status_code=400, detail="No active question.")
    if current.id != payload.question_id:
        raise HTTPException(status_code=400, detail="Answer does not match the active question.")

    result = ai_service.evaluate_answer(current, payload.answer, session.resume, session.difficulty)

    session.answers.append(
        AnswerEvaluation(
            question_id=current.id,
            question_text=current.text,
            answer=payload.answer,
            score=result["score"],
            explanation=result["explanation"],
            dimensions=result["dimensions"],
            skipped=False,
        )
    )

    follow_up: Question | None = None
    if (
        result.get("follow_up_needed")
        and result.get("follow_up_question")
        and _existing_follow_up(session, current.id) is None
        and _follow_up_depth(session, current.id) < MAX_FOLLOWUP_DEPTH
    ):
        follow_up = Question(
            text=result["follow_up_question"],
            type=current.type,
            topic=current.topic,
            difficulty=session.difficulty,
            follow_up_for=current.id,
        )
        session.questions.append(follow_up)
        session.question_order.insert(session.pointer + 1, follow_up.id)

    session.pointer += 1
    session.updated_at = datetime.now(timezone.utc)
    storage.save(session)

    next_q = _next_payload(session)
    return AnswerResponse(
        evaluation=EvaluationOut(
            question_id=current.id,
            score=result["score"],
            explanation=result["explanation"],
            dimensions=result["dimensions"],
            follow_up=follow_up,
        ),
        next=next_q,
        report_ready=next_q is None,
    )


@router.post("/{session_id}/skip", response_model=NextResponse)
async def skip_question(session_id: str, payload: SkipRequest) -> NextResponse:
    session = _get_session(session_id)
    if session.status != "in_progress":
        raise HTTPException(status_code=400, detail="Interview is not in progress.")

    current = session.current_question()
    if current is None:
        raise HTTPException(status_code=400, detail="No active question.")
    if current.id != payload.question_id:
        raise HTTPException(status_code=400, detail="Question id does not match the active question.")

    session.answers.append(
        AnswerEvaluation(
            question_id=current.id,
            question_text=current.text,
            skipped=True,
        )
    )
    session.pointer += 1
    storage.save(session)

    return NextResponse(next=_next_payload(session))


@router.post("/{session_id}/finish")
async def finish_interview(session_id: str):
    session = _get_session(session_id)
    if session.report is not None:
        return {"report": session.report}

    report = build_report(session, ai_service)
    session.report = report
    session.status = "completed"
    storage.save(session)
    return {"report": report}


@router.get("/{session_id}/report")
async def get_report(session_id: str):
    session = _get_session(session_id)
    if session.report is None:
        raise HTTPException(status_code=404, detail="Report not ready. Complete the interview first.")
    return {"report": session.report}


@router.get("/{session_id}")
async def get_session(session_id: str):
    session = _get_session(session_id)
    data = session.model_dump(mode="json")
    data["ai_mode"] = ai_service.mode
    return data
