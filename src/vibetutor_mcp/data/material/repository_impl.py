"""SQLite 기반 ``MaterialRepository`` 구현체 (스캐폴딩 단계: 스텁).

DI 와이어링과 타입 경계를 먼저 고정하기 위한 골격이다. 실제 영속화 로직은
MVP 2단계에서 구현하며, 그 전 호출은 ``NotImplementedError`` 로 명시적으로 중단한다.
"""

from __future__ import annotations

from sqlalchemy.orm import Session, sessionmaker

from vibetutor_mcp.domain.material.model import StudyMaterial
from vibetutor_mcp.domain.material.repository import MaterialRepository


class SqliteMaterialRepository(MaterialRepository):
    """``study_materials`` 테이블에 교재 메타데이터를 저장/조회한다."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def save_material(self, material: StudyMaterial) -> int:
        raise NotImplementedError("MVP 2단계에서 구현: 엔티티 저장 후 id 반환")

    def list_materials(self) -> list[StudyMaterial]:
        raise NotImplementedError("MVP 2단계에서 구현: 전체 교재 조회")

    def find_by_topic(self, topic: str) -> StudyMaterial | None:
        raise NotImplementedError("MVP 2단계에서 구현: 주제별 조회")
