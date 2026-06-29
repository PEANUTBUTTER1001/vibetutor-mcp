"""SQLite 기반 ``MaterialRepository`` 구현체.

세션 팩토리를 주입받아 ``study_materials`` 테이블에 교재 메타데이터를 저장/조회한다.
ORM 의존성은 이 ``data`` 레이어에 격리되며, Domain 의 ``StudyMaterial`` 과의 변환은
``db`` 모듈의 매퍼(``to_domain`` / ``to_entity``)로만 수행한다(SRS FR-10·FR-11).
"""

from __future__ import annotations

from sqlalchemy import select, text
from sqlalchemy.orm import Session, sessionmaker

from vibetutor_mcp.domain.material.model import StudyMaterial
from vibetutor_mcp.domain.material.repository import MaterialRepository

from .db import Base, StudyMaterialEntity, to_domain, to_entity

# LIKE 패턴에서 와일드카드(%, _)와 이스케이프 문자(\\)를 리터럴로 처리하기 위한 이스케이프.
_LIKE_ESCAPE = "\\"


def _escape_like(term: str) -> str:
    """사용자 입력의 LIKE 메타문자를 무력화한다(``%``/``_``/``\\`` → 리터럴)."""
    return (
        term.replace(_LIKE_ESCAPE, _LIKE_ESCAPE * 2)
        .replace("%", _LIKE_ESCAPE + "%")
        .replace("_", _LIKE_ESCAPE + "_")
    )


class SqliteMaterialRepository(MaterialRepository):
    """``study_materials`` 테이블에 교재 메타데이터를 저장/조회한다."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        """테이블 생성(최초 1회) + 누락 컬럼 멱등 마이그레이션.

        ``create_all`` 은 기존 테이블에 신규 컬럼을 추가하지 않으므로, 과거에 만들어진
        DB 와의 호환을 위해 ``content_hash`` 컬럼이 없으면 ``ALTER TABLE`` 로 더한다.
        """
        with self._session_factory() as session:
            Base.metadata.create_all(session.get_bind())
            # PRAGMA 로 현재 컬럼을 조회(인덱스 1 == 컬럼명) 후 누락 시에만 추가.
            rows = session.execute(text("PRAGMA table_info(study_materials)")).all()
            columns = {row[1] for row in rows}
            if "content_hash" not in columns:
                session.execute(text("ALTER TABLE study_materials ADD COLUMN content_hash VARCHAR"))
                session.commit()

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

    def find_by_id(self, material_id: int) -> StudyMaterial | None:
        """id 로 교재 단건을 조회한다. 없으면 ``None`` (Resource 단건, FR-12)."""
        with self._session_factory() as session:
            entity = session.get(StudyMaterialEntity, material_id)
            return to_domain(entity) if entity is not None else None

    def search_materials(self, query: str) -> list[StudyMaterial]:
        """제목에 ``query`` 가 포함된 교재를 최신순(id 내림차순)으로 검색한다(FR-11).

        LIKE 메타문자를 이스케이프해 ``%``/``_`` 가 와일드카드로 오해석되지 않도록 한다.
        """
        pattern = f"%{_escape_like(query)}%"
        with self._session_factory() as session:
            stmt = (
                select(StudyMaterialEntity)
                .where(StudyMaterialEntity.topic_title.like(pattern, escape=_LIKE_ESCAPE))
                .order_by(StudyMaterialEntity.id.desc())
            )
            return [to_domain(entity) for entity in session.scalars(stmt).all()]
