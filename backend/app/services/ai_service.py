"""High-level AI service.

Every public method first attempts the configured LLM provider and transparently
falls back to the rule-based mock engine when no API key is set or the provider
errors. Callers always receive the same data shape.
"""
from __future__ import annotations

import json
import logging

from app.models import Question, ResumeInfo
from app.services import mock_engine
from app.services.ai_client import AIClient

logger = logging.getLogger("interview.ai")

AI_SYSTEM = "You are an expert technical interviewer and career coach. Always respond with valid JSON only."

DIMENSION_KEYS = ["Relevance", "Technical Accuracy", "Completeness", "Communication", "Clarity", "Confidence", "Problem Solving"]


def _normalize_dimensions(dims: dict) -> dict:
    result = {}
    for key in DIMENSION_KEYS:
        val = dims.get(key, 0)
        try:
            val = float(val)
        except (TypeError, ValueError):
            val = 0.0
        result[key] = round(max(0.0, min(10.0, val)), 1)
    return result


class AIService:
    def __init__(self) -> None:
        self.client = AIClient()

    @property
    def mode(self) -> str:
        return "openai" if self.client.available else "mock"

    # ------------------------------------------------------------------
    # Resume analysis
    # ------------------------------------------------------------------

    def analyze_resume(self, text: str) -> tuple[ResumeInfo, str]:
        if self.client.available:
            try:
                payload = self.client.chat_json(
                    "You are a precise resume parser.",
                    _resume_prompt(text),
                    temperature=0.2,
                )
                resume = ResumeInfo.model_validate(_pick(payload, "resume", payload))
                summary = _build_ai_summary(resume, payload)
                return resume, summary
            except Exception as exc:  # noqa: BLE001
                logger.warning("AI resume analysis failed, falling back to mock: %s", exc)
        return mock_engine.mock_analyze_resume(text)

    # ------------------------------------------------------------------
    # Question generation
    # ------------------------------------------------------------------

    def generate_questions(self, resume: ResumeInfo, role: str, difficulty: str, count: int = 8) -> list[Question]:
        if self.client.available:
            try:
                payload = self.client.chat_json(
                    "You prepare personalized interview question sets.",
                    _questions_prompt(resume, role, difficulty, count),
                    temperature=0.8,
                )
                raw_list = _pick(payload, "questions", payload)
                questions = []
                for item in raw_list:
                    text = str(item.get("text", "")).strip()
                    if not text:
                        continue
                    questions.append(
                        Question(
                            text=text,
                            type=item.get("type", "technical"),
                            topic=str(item.get("topic", "") or ""),
                            difficulty=difficulty,
                        )
                    )
                if questions:
                    return questions
            except Exception as exc:  # noqa: BLE001
                logger.warning("AI question generation failed, falling back to mock: %s", exc)
        return mock_engine.mock_generate_questions(resume, role, difficulty, count)

    # ------------------------------------------------------------------
    # Answer evaluation + follow-up
    # ------------------------------------------------------------------

    def evaluate_answer(self, question: Question, answer: str, resume: ResumeInfo, difficulty: str) -> dict:
        if self.client.available:
            try:
                payload = self.client.chat_json(
                    AI_SYSTEM,
                    _evaluate_prompt(question, answer, difficulty),
                    temperature=0.3,
                )
                dims = _normalize_dimensions(_pick(payload, "dimensions", {}))
                score = _clamp_score(payload.get("score", 0))
                follow_up_question = payload.get("follow_up_question")
                if isinstance(follow_up_question, str) and follow_up_question.strip():
                    follow_up_question = follow_up_question.strip()
                else:
                    follow_up_question = None
                return {
                    "score": score,
                    "dimensions": dims,
                    "explanation": str(payload.get("explanation", "") or ""),
                    "follow_up_needed": bool(payload.get("follow_up_needed", False)),
                    "follow_up_question": follow_up_question,
                }
            except Exception as exc:  # noqa: BLE001
                logger.warning("AI evaluation failed, falling back to mock: %s", exc)
        return mock_engine.mock_evaluate_answer(question, answer, resume, difficulty)

    # ------------------------------------------------------------------
    # Qualitative report feedback
    # ------------------------------------------------------------------

    def generate_feedback(self, session) -> dict:
        dim_averages = _dimension_averages(session)
        overall = _overall_from_dims(dim_averages)
        mock_result = mock_engine.mock_feedback(session, dim_averages, overall)
        if not self.client.available:
            return mock_result
        try:
            payload = self.client.chat_json(
                AI_SYSTEM,
                _feedback_prompt(session, dim_averages),
                temperature=0.5,
            )
            better = payload.get("better_answers", [])
            better_list = []
            if isinstance(better, list):
                for item in better:
                    q_text = str(item.get("question", "") or "")
                    y_text = str(item.get("your_answer", "") or "")
                    b_text = str(item.get("better_answer", "") or "")
                    if q_text and b_text:
                        better_list.append({"question": q_text, "your_answer": y_text, "better_answer": b_text})
            return {
                "strengths": [str(s) for s in (payload.get("strengths") or mock_result["strengths"])],
                "weaknesses": [str(s) for s in (payload.get("weaknesses") or mock_result["weaknesses"])],
                "improvements": [str(s) for s in (payload.get("improvements") or mock_result["improvements"])],
                "recommended_practice": [str(s) for s in (payload.get("recommended_practice") or mock_result["recommended_practice"])],
                "better_answers": better_list or _fallback_better_answers(session),
            }
        except Exception as exc:  # noqa: BLE001
            logger.warning("AI feedback generation failed, falling back to mock: %s", exc)
            return mock_result


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------


def _pick(payload: dict, key: str, default):
    if isinstance(payload, dict):
        return payload.get(key, default)
    return default


def _resume_prompt(text: str) -> str:
    return f"""Parse the resume text below into a JSON object with EXACTLY this shape:
{{
  "name": "string", "email": "string", "phone": "string", "summary": "string",
  "education": [{{"degree": "string", "institution": "string", "year": "string"}}],
  "skills": ["string"],
  "languages": ["string"],
  "technologies": ["string"],
  "projects": [{{"name": "string", "description": "string", "technologies": ["string"]}}],
  "experience": [{{"role": "string", "company": "string", "period": "string", "description": "string"}}],
  "certifications": ["string"]
}}
Use empty values when something is not present. Return only the JSON object.

RESUME TEXT:
{text[:12000]}"""


def _build_ai_summary(resume: ResumeInfo, payload: dict) -> str:
    description = str(payload.get("description", "") or "")
    if description:
        return description
    top = ", ".join(resume.technologies[:5]) if resume.technologies else "no explicit technologies listed"
    return (
        f"Candidate identified: {resume.name or 'Unknown'}. "
        f"Detected {len(resume.skills)} relevant skills — highlights: {top}. "
        f"Education entries: {len(resume.education)}. Experience: {len(resume.experience)} role(s). "
        f"Projects identified: {len(resume.projects)}. Certifications: {len(resume.certifications)}."
    )


def _questions_prompt(resume: ResumeInfo, role: str, difficulty: str, count: int) -> str:
    return f"""Prepare {count} interview questions for a {role} interview at "{difficulty}" difficulty.
Build the questions from the candidate's ACTUAL resume below. They must be personalized — reference their skills, projects, experience, and education where possible.
Mix question types: technical, cv, project, behavioral, situational. Scale complexity to the difficulty level.
Return a JSON object: {{"questions": [{{"text": "string", "type": "technical|cv|project|behavioral|situational", "topic": "string"}}]}}
Do not number the questions. Return only the JSON.

RESUME:
{json.dumps(resume.model_dump(), indent=2)[:8000]}"""


def _evaluate_prompt(question: Question, answer: str, difficulty: str) -> str:
    return f"""You are a strict but fair interviewer. Evaluate the candidate's answer.
Interview difficulty: {difficulty}.
Question type: {question.type}. Question: {question.text}
Answer: {answer}
Return JSON:
{{
  "score": float 1-10,
  "dimensions": {{"Relevance": 0-10, "Technical Accuracy": 0-10, "Completeness": 0-10, "Communication": 0-10, "Clarity": 0-10, "Confidence": 0-10, "Problem Solving": 0-10}},
  "explanation": "2-3 sentences: what was good and what could be improved",
  "follow_up_needed": bool,
  "follow_up_question": "a deeper question based strictly on their answer, or null"
}}
Only valid JSON."""


def _feedback_prompt(session, dim_averages: dict) -> str:
    lines = []
    for a in session.answers:
        if a.skipped:
            lines.append(f"- [SKIPPED] Q: {a.question_text}")
            continue
        lines.append(f"- Q: {a.question_text}\n  A: {a.answer[:600]}\n  Score: {a.score}/10 ({a.explanation})")
    summaries = "\n".join(lines)
    return f"""Write a professional performance review for a completed mock interview.
Role: {session.job_role} | Difficulty: {session.difficulty}
Dimension averages (0-10): {json.dumps(dim_averages)}
Questions and answers with scores:
{summaries}
Return JSON:
{{
  "strengths": ["string"],
  "weaknesses": ["string"],
  "improvements": ["string"],
  "better_answers": [{{"question": "string", "your_answer": "string", "better_answer": "string"}}],
  "recommended_practice": ["string"]
}}
Create up to 3 better_answers for the lowest-scored questions. Only valid JSON."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _clamp_score(value) -> float:
    try:
        val = float(value)
    except (TypeError, ValueError):
        val = 0.0
    return round(max(0.0, min(10.0, val)), 1)


def _dimension_averages(session) -> dict:
    answered = [a for a in session.answers if not a.skipped and a.answer.strip() and a.dimensions]
    if not answered:
        return {key: 0.0 for key in DIMENSION_KEYS}
    totals = {key: 0.0 for key in DIMENSION_KEYS}
    for a in answered:
        for key in DIMENSION_KEYS:
            totals[key] += a.dimensions.get(key, 0.0)
    return {key: round(totals[key] / len(answered), 1) for key in DIMENSION_KEYS}


def _overall_from_dims(dims: dict) -> float:
    weights = {
        "Relevance": 0.18, "Technical Accuracy": 0.2, "Completeness": 0.18,
        "Communication": 0.12, "Clarity": 0.12, "Confidence": 0.1, "Problem Solving": 0.1,
    }
    return round(sum(dims[k] * weights.get(k, 0.1) for k in dims), 1)


def _fallback_better_answers(session) -> list:
    results = []
    answered = [a for a in session.answers if not a.skipped and a.answer.strip()]
    scored = sorted(answered, key=lambda a: a.score)[:3]
    for a in scored:
        results.append({
            "question": a.question_text,
            "your_answer": a.answer[:400],
            "better_answer": (
                f"A stronger answer would directly address the question, open with a clear conclusion, "
                f"give one concrete example from your experience, walk through your approach (what, how, why), "
                f"and close by linking back to the role you are applying for — all in a confident, structured way."
            ),
        })
    return results
