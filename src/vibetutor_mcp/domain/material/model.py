"""교재 도메인 모델.

경계(입력 검증)용 스키마는 Pydantic ``BaseModel`` 로, 내부 도메인 엔티티는
``dataclass`` 로 정의한다. 이 모듈은 순수 Python 이며 ``jinja2`` / ``weasyprint`` /
``sqlalchemy`` / ``mcp`` 등 프레임워크 타입을 절대 포함하지 않는다.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel, Field

# ──────────────────────────────────────────────────────────────
# 표준 교재 모델
# ──────────────────────────────────────────────────────────────


class StudySection(BaseModel):
    """교재의 단일 학습 섹션. 입력 양식 강제(방식 A)를 위한 경계 스키마."""

    heading: str = Field(..., min_length=1, description="단원 제목")
    concept_explanation: str = Field(..., min_length=1, description="개념 설명 본문")
    # 이론 중심 교재도 지원하기 위해 코드/연습문제는 Optional 로 둔다.
    code_example: str | None = Field(default=None, description="실제 코드 예제(선택)")
    exercises: str | None = Field(default=None, description="연습 문제(선택)")
    # 스캐너가 주입한 코드의 출처(파일·라인). 자동 생성 초안의 출처 표기 의무(SRS §8.1, FR-15).
    code_source: str | None = Field(
        default=None, description="주입된 코드 예제의 출처(예: src/foo.py:12-20)"
    )


class MaterialRequest(BaseModel):
    """교재 생성 요청. Tool 입력 스키마로 사용되어 경계에서 검증된다."""

    topic_title: str = Field(..., min_length=1, description="교재 주제 제목")
    sections: list[StudySection] = Field(
        default_factory=list, description="교재를 구성하는 학습 섹션 목록"
    )


# ──────────────────────────────────────────────────────────────
# 10단계 실전 교재 모델 (Practical / Markdown 기반)
# ──────────────────────────────────────────────────────────────


class ComparisonRow(BaseModel):
    """아키텍처 비교 테이블의 단일 행."""

    aspect: str = Field(..., min_length=1, description="비교 항목")
    legacy: str = Field(..., min_length=1, description="기존 방식")
    modern: str = Field(..., min_length=1, description="현대적 방식")


class BugBox(BaseModel):
    """흔한 실수(Bug Box)의 단일 항목."""

    symptom: str = Field(..., min_length=1, description="증상")
    cause: str = Field(default="-", description="원인")
    solution: str = Field(default="-", description="해결 방법")


class QnAItem(BaseModel):
    """핵심 Q&A 단일 항목."""

    question: str = Field(..., min_length=1, description="핵심 질문")
    answer: str = Field(..., min_length=1, description="모범 답안")


class GlossaryItem(BaseModel):
    """용어 사전 단일 항목."""

    term: str = Field(..., min_length=1, description="용어")
    definition: str = Field(default="", description="정의")


class PracticalStudySection(BaseModel):
    """10단계 실전 교재의 단일 챕터."""

    heading: str = Field(..., min_length=1, description="챕터 제목")
    intro: str = Field(default="", description="들어가며")
    objectives: list[str] = Field(default_factory=list)
    architecture_comparison: list[ComparisonRow] = Field(default_factory=list)
    code_analysis: str = Field(default="", description="주석으로 읽는 핵심 코드 분석")
    local_code_integration: str | None = Field(default=None)
    code_source: str | None = Field(default=None)
    bug_box: list[BugBox] = Field(default_factory=list)
    pro_tip: str = Field(default="")
    study_points: list[str] = Field(default_factory=list)
    qna: list[QnAItem] = Field(default_factory=list)
    glossary: list[GlossaryItem] = Field(default_factory=list)
    official_links: list[str] = Field(default_factory=list)


class PracticalMaterialRequest(BaseModel):
    """10단계 실전 교재 생성 요청."""

    topic_title: str = Field(..., min_length=1, description="교재 주제 제목")
    sections: list[PracticalStudySection] = Field(default_factory=list)


# ──────────────────────────────────────────────────────────────
# 도메인 엔티티 (영속화)
# ──────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class StudyMaterial:
    """영속화/도메인 엔티티. ``id == 0`` 은 아직 저장되지 않은 상태를 의미한다."""

    topic_title: str
    file_path: str
    id: int = 0
    created_at: datetime | None = None
    content_hash: str | None = None
