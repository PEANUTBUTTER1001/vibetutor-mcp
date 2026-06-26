"""교재 메타데이터 영속화 인터페이스.

구조적 타이핑(``Protocol``)으로 정의하여 Domain 이 특정 DB/ORM 구현에 의존하지
않도록 한다. 구현체는 ``data`` 레이어의 ``SqliteMaterialRepository`` 가 담당한다.
"""

from __future__ import annotations

from typing import Protocol

from .model import StudyMaterial


class MaterialRepository(Protocol):
    """생성된 교재의 메타데이터를 저장/조회한다."""

    def save_material(self, material: StudyMaterial) -> int:
        """교재를 저장하고 새로 부여된 id 를 반환한다."""
        ...

    def list_materials(self) -> list[StudyMaterial]:
        """저장된 모든 교재 메타데이터를 반환한다."""
        ...

    def find_by_topic(self, topic: str) -> StudyMaterial | None:
        """주제로 교재를 조회한다. 없으면 ``None``."""
        ...
