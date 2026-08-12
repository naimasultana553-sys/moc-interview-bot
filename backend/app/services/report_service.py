"""Final report generation: deterministic scoring + AI/mock qualitative feedback."""
from __future__ import annotations

from app.models import (
    BetterAnswerSuggestion,
    InterviewReport,
    InterviewSession,
    QuestionResult,
)
from app.services.ai_service import AIService

DIM_KEYS = ["Relevance", "Technical Accuracy", "Completeness", "Communication", "Clarity", "Confidence", "Problem Solving"]

WEIGHTS = {
    "Relevance": 0.18, "Technical Accuracy": 0.20, "Completeness": 0.18,
    "Communication": 0.12, "Clarity": 0.12, "Confidence": 0.10, "Problem Solving": 0.10,
}


def _answered(session: InterviewSession):
    return [a for a in session.answers if not a.skipped and a.answer.strip()]


def _avg_dims(session: InterviewSession) -> dict:
    answered = _answered(session)
    if not answered:
        return {k: 0.0 for k in DIM_KEYS}
    totals = {k: 0.0 for k in DIM_KEYS}
    for a in answered:
        for k in DIM_KEYS:
            totals[k] += a.dimensions.get(k, 0.0)
    return {k: round(totals[k] / len(answered), 1) for k in DIM_KEYS}


def _resume_relevance(session: InterviewSession) -> float:
    avg_rel = _avg_dims(session).get("Relevance", 0.0)
    role = (session.job_role or "").lower()
    resume_tech = " ".join((session.resume or {}).technologies if session.resume else []).lower()
    overlap = 0.0
    if role and resume_tech:
        role_words = set(role.split())
        tech_terms = [t for t in role_words if len(t) > 3]
        if tech_terms:
            overlap = min(1.0, sum(1 for t in tech_terms if t in resume_tech) / len(tech_terms))
    return round(min(100.0, avg_rel * 8.0 + overlap * 40.0), 1)


def _overall_score(dims: dict) -> float:
    return round(sum(dims[k] * WEIGHTS[k] for k in DIM_KEYS), 1)


def build_report(session: InterviewSession, ai: AIService) -> InterviewReport:
    dims = _avg_dims(session)
    answered = _answered(session)

    technical_score = round(dims["Technical Accuracy"] * 10, 1)
    communication_score = round(((dims["Communication"] + dims["Clarity"] + dims["Confidence"]) / 3) * 10, 1)
    problem_solving_score = round(dims["Problem Solving"] * 10, 1)

    behavioral_answers = [a for a in answered if _type_of(session, a.question_id) in ("behavioral", "situational")]
    behavioral_score = round((sum(a.score for a in behavioral_answers) / len(behavioral_answers)) * 10, 1) if behavioral_answers else 0.0

    overall = _overall_score(dims) * 10
    resume_relevance = _resume_relevance(session)

    question_results: list[QuestionResult] = []
    for a in answered:
        q = session.find_question(a.question_id)
        if not q:
            continue
        follow_up = next(
            (fa.answer for fa in session.answers if not fa.skipped and _is_follow_up_for(session, fa.question_id, a.question_id)),
            None,
        )
        question_results.append(
            QuestionResult(question=q, answer=a.answer, score=a.score, evaluation=a.explanation, follow_up_answer=follow_up)
        )

    skipped_count = len([a for a in session.answers if a.skipped])
    questions_total = max(len(question_results), len(session.question_order))

    areas = sorted(((k, dims[k]) for k in DIM_KEYS), key=lambda kv: -kv[1])
    strongest = [k for k, v in areas if v >= 6.5][:3]
    weakest = [k for k, v in areas if v <= 5.5][:3]

    feedback = ai.generate_feedback(session)
    better_answers = [
        BetterAnswerSuggestion(question=b["question"], your_answer=b["your_answer"], better_answer=b["better_answer"])
        for b in feedback.get("better_answers", [])
    ]

    return InterviewReport(
        overall_score=round(max(0.0, min(100.0, overall)), 1),
        technical_score=technical_score,
        communication_score=communication_score,
        problem_solving_score=problem_solving_score,
        behavioral_score=behavioral_score,
        resume_relevance=resume_relevance,
        questions_answered=len(question_results),
        questions_total=questions_total,
        skipped_count=skipped_count,
        strengths=feedback.get("strengths", []),
        weaknesses=feedback.get("weaknesses", []),
        improvements=feedback.get("improvements", []),
        better_answers=better_answers,
        recommended_practice=feedback.get("recommended_practice", []),
        question_results=question_results,
    )


def _type_of(session: InterviewSession, question_id: str) -> str:
    q = session.find_question(question_id)
    return q.type if q else ""


def _is_follow_up_for(session: InterviewSession, question_id: str, parent_id: str) -> bool:
    q = session.find_question(question_id)
    return bool(q and q.follow_up_for == parent_id)
