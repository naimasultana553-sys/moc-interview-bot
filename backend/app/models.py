from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return uuid4().hex


# ---------------------------------------------------------------------------
# Resume
# ---------------------------------------------------------------------------


class Education(BaseModel):
    degree: str = ""
    institution: str = ""
    year: str = ""


class Experience(BaseModel):
    role: str = ""
    company: str = ""
    period: str = ""
    description: str = ""


class Project(BaseModel):
    name: str = ""
    description: str = ""
    technologies: list[str] = Field(default_factory=list)


class ResumeInfo(BaseModel):
    name: str = ""
    email: str = ""
    phone: str = ""
    summary: str = ""
    education: list[Education] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    experience: list[Experience] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)


class ResumeAnalysisResult(BaseModel):
    session_id: str
    resume: ResumeInfo
    summary: str
    raw_text: str


# ---------------------------------------------------------------------------
# Interview
# ---------------------------------------------------------------------------

QuestionType = Literal["technical", "cv", "project", "behavioral", "situational"]


class Question(BaseModel):
    id: str = Field(default_factory=_new_id)
    text: str
    type: QuestionType = "technical"
    topic: str = ""
    difficulty: str = "medium"
    follow_up_for: str | None = None


class AnswerEvaluation(BaseModel):
    question_id: str
    question_text: str
    answer: str = ""
    score: float = 0.0
    explanation: str = ""
    dimensions: dict[str, float] = Field(default_factory=dict)
    skipped: bool = False


class QuestionResult(BaseModel):
    question: Question
    answer: str
    score: float
    evaluation: str
    follow_up_answer: str | None = None


class BetterAnswerSuggestion(BaseModel):
    question: str
    your_answer: str
    better_answer: str


class InterviewReport(BaseModel):
    overall_score: float
    technical_score: float
    communication_score: float
    problem_solving_score: float
    behavioral_score: float
    resume_relevance: float
    questions_answered: int
    questions_total: int
    skipped_count: int
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)
    better_answers: list[BetterAnswerSuggestion] = Field(default_factory=list)
    recommended_practice: list[str] = Field(default_factory=list)
    question_results: list[QuestionResult] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=_now)


class InterviewSession(BaseModel):
    id: str = Field(default_factory=_new_id)
    resume: ResumeInfo | None = None
    raw_text: str = ""
    job_role: str = ""
    difficulty: str = "medium"
    questions: list[Question] = Field(default_factory=list)
    question_order: list[str] = Field(default_factory=list)
    pointer: int = 0
    answers: list[AnswerEvaluation] = Field(default_factory=list)
    status: Literal["setup", "in_progress", "completed"] = "setup"
    report: InterviewReport | None = None
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)

    def remaining(self) -> int:
        return max(0, len(self.question_order) - self.pointer)

    def current_question(self) -> Question | None:
        if self.pointer >= len(self.question_order):
            return None
        qid = self.question_order[self.pointer]
        for q in self.questions:
            if q.id == qid:
                return q
        return None

    def find_question(self, question_id: str) -> Question | None:
        for q in self.questions:
            if q.id == question_id:
                return q
        return None

    def answered_count(self) -> int:
        return len([a for a in self.answers if a.answer.strip() or a.skipped])

    def total(self) -> int:
        return len(self.question_order)
