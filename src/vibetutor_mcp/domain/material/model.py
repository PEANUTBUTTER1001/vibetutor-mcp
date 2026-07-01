"""교재 도메인 모델.

경계(입력 검증)용 스키마는 Pydantic ``BaseModel`` 로, 내부 도메인 엔티티는
``dataclass`` 로 정의한다. 이 모듈은 순수 Python 이며 ``jinja2`` / ``weasyprint`` /
``sqlalchemy`` / ``mcp`` 등 프레임워크 타입을 절대 포함하지 않는다.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

# ──────────────────────────────────────────────────────────────
# 출력 포맷
# ──────────────────────────────────────────────────────────────


class ExportFormat(StrEnum):
    """교재 산출물 포맷. 도메인 enum 이므로 UseCase 분기에 사용해도 무방하다.

    ``StrEnum`` 으로 ``model_dump`` 직렬화/JSON 스키마에서 평탄한 문자열로 노출된다.
    """

    PDF = "pdf"
    HTML = "html"
    MARKDOWN = "markdown"


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


class OfficialLink(BaseModel):
    """공식 문서 링크 단일 항목."""

    text: str = Field(..., min_length=1, description="링크 표시 텍스트")
    url: str = Field(..., min_length=1, description="링크 URL")


class PracticalStudySection(BaseModel):
    """10단계 실전 교재의 단일 챕터."""

    heading: str = Field(..., min_length=1, description="챕터 제목")
    intro: str = Field(default="", description="들어가며")
    objectives: list[str] = Field(default_factory=list)
    architecture_comparison: list[ComparisonRow] = Field(default_factory=list)
    concept_explanation: str = Field(default="", description="코드 이해를 위한 핵심 이론·개념 설명")
    code_analysis: str = Field(default="", description="주석으로 읽는 핵심 코드 분석")
    local_code_integration: str | None = Field(default=None)
    code_source: str | None = Field(default=None)
    bug_box: list[BugBox] = Field(default_factory=list)
    pro_tip: str = Field(default="")
    study_points: list[str] = Field(default_factory=list)
    qna: list[QnAItem] = Field(default_factory=list)
    glossary: list[GlossaryItem] = Field(default_factory=list)
    official_links: list[OfficialLink] = Field(default_factory=list)


class PracticalMaterialRequest(BaseModel):
    """10단계 실전 교재 생성 요청.

    ``format`` 으로 산출물 포맷(PDF/HTML/Markdown)을 선택한다. ``source_markdown`` 은
    Markdown 출력 시 **손실 없는 원문 그대로 내보내기**를 위해 파서가 동봉하는 원본
    마크다운이다(파싱→재렌더의 손실을 피한다). 두 필드는 '출력 방법'에 대한 메타데이터로,
    콘텐츠 동일성(content_hash) 산출에서는 제외된다.
    """

    topic_title: str = Field(..., min_length=1, description="교재 주제 제목")
    sections: list[PracticalStudySection] = Field(default_factory=list)
    format: ExportFormat = Field(
        default=ExportFormat.PDF, description="산출물 포맷(pdf/html/markdown)"
    )
    source_markdown: str | None = Field(
        default=None, description="Markdown 출력용 원본 마크다운(파서가 동봉)"
    )


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
