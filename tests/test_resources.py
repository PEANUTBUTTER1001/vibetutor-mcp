"""교재 Resource(vibetutor://materials) 테스트.

목록/단건/없는 id/유효하지 않은 id 의 JSON 응답을 가짜 MCP·UseCase 로 검증한다
(프레임워크 의존성 불필요).
"""

from __future__ import annotations

import json
from datetime import datetime

from vibetutor_mcp.domain.material.model import StudyMaterial
from vibetutor_mcp.domain.material.query import GetMaterialUseCase, ListMaterialsUseCase
from vibetutor_mcp.presentation.resources.materials import register_resources


class _FakeRepo:
    def __init__(self, materials: list[StudyMaterial]) -> None:
        self._by_id = {m.id: m for m in materials}
        self._all = materials

    def list_materials(self) -> list[StudyMaterial]:
        return self._all

    def find_by_id(self, material_id: int) -> StudyMaterial | None:
        return self._by_id.get(material_id)


class _FakeMCP:
    def __init__(self) -> None:
        self.resources: dict[str, object] = {}

    def resource(self, uri: str):  # type: ignore[no-untyped-def]
        def deco(fn):  # type: ignore[no-untyped-def]
            self.resources[uri] = fn
            return fn

        return deco


def _register(materials: list[StudyMaterial]) -> _FakeMCP:
    repo = _FakeRepo(materials)
    mcp = _FakeMCP()
    register_resources(
        mcp,  # type: ignore[arg-type]
        ListMaterialsUseCase(repo),  # type: ignore[arg-type]
        GetMaterialUseCase(repo),  # type: ignore[arg-type]
    )
    return mcp


_SAMPLE = [
    StudyMaterial(
        topic_title="파이썬",
        file_path="/p.pdf",
        id=1,
        created_at=datetime(2026, 6, 29, 12, 0, 0),
        content_hash="abc123",
    ),
]


def test_resource_lists_materials_as_json() -> None:
    mcp = _register(_SAMPLE)
    payload = json.loads(mcp.resources["vibetutor://materials"]())  # type: ignore[operator]
    assert isinstance(payload, list) and len(payload) == 1
    assert payload[0]["topic_title"] == "파이썬"
    assert payload[0]["content_hash"] == "abc123"
    assert payload[0]["created_at"] == "2026-06-29T12:00:00"


def test_resource_single_material() -> None:
    mcp = _register(_SAMPLE)
    fn = mcp.resources["vibetutor://materials/{material_id}"]
    payload = json.loads(fn("1"))  # type: ignore[operator]
    assert payload["id"] == 1 and payload["file_path"] == "/p.pdf"


def test_resource_missing_id_returns_empty_object() -> None:
    mcp = _register(_SAMPLE)
    fn = mcp.resources["vibetutor://materials/{material_id}"]
    assert json.loads(fn("999")) == {}  # type: ignore[operator]


def test_resource_invalid_id_returns_error() -> None:
    mcp = _register(_SAMPLE)
    fn = mcp.resources["vibetutor://materials/{material_id}"]
    payload = json.loads(fn("not-a-number"))  # type: ignore[operator]
    assert "error" in payload
