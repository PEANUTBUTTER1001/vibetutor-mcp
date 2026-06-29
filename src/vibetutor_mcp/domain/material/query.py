"""교재 조회/검색 유스케이스(읽기 전용).

생성 유스케이스와 책임을 분리하여, 누적된 교재의 검색(FR-11)과 목록/단건 노출
(Resource, FR-12)을 담당한다. 리포지토리 인터페이스(Port)에만 의존한다.
"""

from __future__ import annotations

from .model import StudyMaterial
from .repository import MaterialRepository


class SearchMaterialUseCase:
    """제목 부분일치로 누적 교재를 검색한다(FR-11)."""

    def __init__(self, repository: MaterialRepository) -> None:
        self._repo = repository

    def __call__(self, query: str) -> list[StudyMaterial]:
        # 공백만 있는 질의는 빈 결과로 단락(전체 노출 방지·불필요한 쿼리 회피).
        normalized = query.strip()
        if not normalized:
            return []
        return self._repo.search_materials(normalized)


class ListMaterialsUseCase:
    """저장된 모든 교재를 반환한다(Resource 목록 노출용, FR-12)."""

    def __init__(self, repository: MaterialRepository) -> None:
        self._repo = repository

    def __call__(self) -> list[StudyMaterial]:
        return self._repo.list_materials()


class GetMaterialUseCase:
    """id 로 교재 단건을 조회한다(Resource 단건 노출용, FR-12)."""

    def __init__(self, repository: MaterialRepository) -> None:
        self._repo = repository

    def __call__(self, material_id: int) -> StudyMaterial | None:
        return self._repo.find_by_id(material_id)
