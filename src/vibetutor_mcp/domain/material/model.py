"""교재 도메인 모델.

경계(입력 검증)용 스키마는 Pydantic ``BaseModel`` 로, 내부 도메인 엔티티는
``dataclass`` 로 정의한다. 이 모듈은 순수 Python 이며 ``jinja2`` / ``weasyprint`` /
``sqlalchemy`` / ``mcp`` 등 프레임워크 타입을 절대 포함하지 않는다.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel, Field


class StudySection(BaseModel):
    """교재의 단일 학습 섹션. 입력 양식 강제(방식 A)를 위한 경계 스키마."""

    heading: str = Field(..., min_length=1, description="단원 제목")
    concept_explanation: str = Field(..., min_length=1, description="개념 설명 본문")
    # 이론 중심 교재도 지원하기 위해 코드/연습문제는 Optional 로 둔다.
    code_example: str | None = Field(default=None, description="실제 코드 예제(선택)")
    exercises: str | None = Field(default=None, description="연습 문제(선택)")


class MaterialRequest(BaseModel):
    """교재 생성 요청. Tool 입력 스키마로 사용되어 경계에서 검증된다."""

    topic_title: str = Field(..., min_length=1, description="교재 주제 제목")
    sections: list[StudySection] = Field(
        default_factory=list, description="교재를 구성하는 학습 섹션 목록"
    )


@dataclass(frozen=True)
class StudyMaterial:
    """영속화/도메인 엔티티. ``id == 0`` 은 아직 저장되지 않은 상태를 의미한다."""

    topic_title: str
    file_path: str
    id: int = 0
    created_at: datetime | None = None
