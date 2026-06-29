"""SQLAlchemy 엔티티 및 도메인 ↔ 엔티티 매퍼.

ORM 의존성은 이 ``data`` 레이어 안에 격리한다. Domain 의 ``StudyMaterial`` 과의
변환은 반드시 매퍼 함수(``to_domain`` / ``to_entity``)를 통해서만 수행한다.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from vibetutor_mcp.domain.material.model import StudyMaterial


class Base(DeclarativeBase):
    """SQLAlchemy 2.0 선언적 베이스."""


def _utcnow() -> datetime:
    return datetime.now(UTC)


class StudyMaterialEntity(Base):
    """``study_materials`` 테이블 매핑 엔티티."""

    __tablename__ = "study_materials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    topic_title: Mapped[str] = mapped_column(String, nullable=False)
    file_path: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    # 재현성 식별자(NFR-10). 과거 레코드 호환을 위해 nullable.
    content_hash: Mapped[str | None] = mapped_column(String, nullable=True)


def to_domain(entity: StudyMaterialEntity) -> StudyMaterial:
    """ORM 엔티티를 순수 도메인 엔티티로 변환한다."""
    return StudyMaterial(
        id=entity.id,
        topic_title=entity.topic_title,
        file_path=entity.file_path,
        created_at=entity.created_at,
        content_hash=entity.content_hash,
    )


def to_entity(material: StudyMaterial) -> StudyMaterialEntity:
    """도메인 엔티티를 ORM 엔티티로 변환한다(id 는 DB 가 부여)."""
    return StudyMaterialEntity(
        topic_title=material.topic_title,
        file_path=material.file_path,
        content_hash=material.content_hash,
    )
