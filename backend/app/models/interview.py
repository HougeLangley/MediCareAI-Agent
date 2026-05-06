"""Medical Interview (multi-turn questioning) models.

Lightweight state machine for collecting patient information
before generating a diagnosis. State is stored in
AgentSession.context["interview"].
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class QuestionTemplate:
    """A single interview question."""

    question_id: str
    question: str
    type: str  # "choice" or "text"
    options: list[str] = field(default_factory=list)
    hint: str = ""
    allow_skip: bool = True


@dataclass
class InterviewState:
    """Snapshot of an ongoing interview stored in AgentSession.context."""

    collected_info: dict[str, Any] = field(default_factory=dict)
    asked_questions: list[str] = field(default_factory=list)
    current_question_id: str | None = None
    is_sufficient: bool = False
    max_questions: int = 6

    def to_dict(self) -> dict[str, Any]:
        return {
            "collected_info": self.collected_info,
            "asked_questions": self.asked_questions,
            "current_question_id": self.current_question_id,
            "is_sufficient": self.is_sufficient,
            "max_questions": self.max_questions,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "InterviewState":
        return cls(
            collected_info=data.get("collected_info", {}),
            asked_questions=data.get("asked_questions", []),
            current_question_id=data.get("current_question_id"),
            is_sufficient=data.get("is_sufficient", False),
            max_questions=data.get("max_questions", 6),
        )


# ---------------------------------------------------------------------------
# Pre-defined question bank (abdominal pain / diarrhea focus for MVP)
# ---------------------------------------------------------------------------

DEFAULT_QUESTIONS: list[QuestionTemplate] = [
    QuestionTemplate(
        question_id="pain_location",
        question="腹痛的位置在哪里？",
        type="choice",
        options=["上腹部", "下腹部", "脐周", "全腹", "不确定"],
        hint="请选择疼痛最明显的部位",
    ),
    QuestionTemplate(
        question_id="pain_nature",
        question="疼痛的性质是怎样的？",
        type="choice",
        options=["绞痛", "胀痛", "隐痛", "刺痛", "烧灼痛"],
        hint="绞痛是一阵一阵拧着疼",
    ),
    QuestionTemplate(
        question_id="duration",
        question="症状持续多久了？",
        type="choice",
        options=["不到1天", "1-3天", "3-7天", "超过1周"],
        hint="从开始出现症状算起",
    ),
    QuestionTemplate(
        question_id="fever",
        question="有没有发热？",
        type="choice",
        options=["无发热", "低热(37.3-38℃)", "中等发热(38-39℃)", "高热(>39℃)"],
    ),
    QuestionTemplate(
        question_id="stool_type",
        question="大便的性状如何？",
        type="choice",
        options=["水样便", "稀便", "黏液便", "脓血便", "正常"],
        hint="如果有血或脓，请务必说明",
    ),
    QuestionTemplate(
        question_id="nausea_vomit",
        question="有没有恶心、呕吐？",
        type="choice",
        options=["无", "恶心", "呕吐", "两者都有"],
    ),
    QuestionTemplate(
        question_id="diet_history",
        question="近期有无不洁饮食或外出就餐？",
        type="choice",
        options=["无", "可疑不洁食物", "外出就餐", "旅行中", "已吃抗生素"],
    ),
    QuestionTemplate(
        question_id="stool_frequency",
        question="过去24小时内大便几次？",
        type="text",
        hint="例如：3次",
    ),
]


def get_next_question(state: InterviewState) -> QuestionTemplate | None:
    """Return the next unasked question, or None if interview is complete."""
    if state.is_sufficient:
        return None
    if len(state.asked_questions) >= state.max_questions:
        return None

    for q in DEFAULT_QUESTIONS:
        if q.question_id not in state.asked_questions:
            return q

    return None


def is_interview_sufficient(state: InterviewState) -> bool:
    """Heuristic: enough info collected to proceed to diagnosis."""
    # Must have answered at least 4 core questions
    core_ids = {"pain_location", "pain_nature", "duration", "stool_type"}
    answered_core = core_ids.intersection(state.collected_info.keys())
    return len(answered_core) >= 3 or len(state.asked_questions) >= state.max_questions
