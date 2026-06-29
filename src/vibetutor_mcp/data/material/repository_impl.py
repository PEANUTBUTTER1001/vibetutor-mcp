"""SQLite 기반 ``MaterialRepository`` 구현체.

세션 팩토리를 주입받아 ``study_materials`` 테이블에 교재 메타데이터를 저장/조회한다.
ORM 의존성은 이 ``data`` 레이어에 격리되며, Domain 의 ``StudyMaterial`` 과의 변환은
``db`` 모듈의 매퍼(``to_domain`` / ``to_entity``)로만 수행한다(SRS FR-10·FR-11).
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from vibetutor_mcp.domain.material.model import StudyMaterial
from vibetutor_mcp.domain.material.repository import MaterialRepository

from .db import Base, StudyMaterialEntity, to_domain, to_entity


class SqliteMaterialRepository(MaterialRepository):
    """``study_materials`` 테이블에 교재 메타데이터를 저장/조회한다."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        """테이블이 없으면 생성한다(최초 1회). 바인드는 세션에서 얻는다."""
        with self._session_factory() as session:
            Base.metadata.create_all(session.get_bind())

    def save_material(self, material: StudyMaterial) -> int:
        """교재 메타데이터를 INSERT 하고 새로 부여된 id 를 반환한다."""
        with self._session_factory() as session:
            entity = to_entity(material)
            session.add(entity)
            session.commit()
            session.refresh(entity)
            return entity.id

    def list_materials(self) -> list[StudyMaterial]:
        """저장된 모든 교재를 id 오름차순으로 반환한다."""
        with self._session_factory() as session:
            stmt = select(StudyMaterialEntity).order_by(StudyMaterialEntity.id)
            return [to_domain(entity) for entity in session.scalars(stmt).all()]

    def find_by_topic(self, topic: str) -> StudyMaterial | None:
        """주제로 가장 최근(가장 큰 id) 교재를 조회한다. 없으면 ``None``."""
        with self._session_factory() as session:
            stmt = (
                select(StudyMaterialEntity)
                .where(StudyMaterialEntity.topic_title == topic)
                .order_by(StudyMaterialEntity.id.desc())
            )
            entity = session.scalars(stmt).first()
            return to_domain(entity) if entity is not None else None
