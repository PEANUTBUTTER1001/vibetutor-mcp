"""교재 목록/단건 MCP Resource 어댑터 (얇은 어댑터).

누적된 교재를 ``vibetutor://materials`` (목록)와 ``vibetutor://materials/{id}``
(단건) Resource 로 노출한다(FR-12). 비즈니스 로직 없이 UseCase 로 위임하고, 결과를
JSON 문자열로 직렬화해 반환한다.
"""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from vibetutor_mcp.domain.material.model import StudyMaterial
from vibetutor_mcp.domain.material.query import GetMaterialUseCase, ListMaterialsUseCase


def _to_dict(material: StudyMaterial) -> dict[str, object]:
    """도메인 엔티티를 JSON 직렬화 가능한 딕셔너리로 변환한다."""
    return {
        "id": material.id,
        "topic_title": material.topic_title,
        "file_path": material.file_path,
        "created_at": material.created_at.isoformat() if material.created_at else None,
        "content_hash": material.content_hash,
    }


def register_resources(
    mcp: FastMCP,
    list_use_case: ListMaterialsUseCase,
    get_use_case: GetMaterialUseCase,
) -> None:
    """교재 Resource(목록/단건)를 MCP 서버에 등록한다."""

    @mcp.resource("vibetutor://materials")
    def list_materials_resource() -> str:
        """저장된 모든 교재 메타데이터를 JSON 배열로 반환한다."""
        materials = list_use_case()
        return json.dumps(
            [_to_dict(m) for m in materials],
            ensure_ascii=False,
            indent=2,
        )

    @mcp.resource("vibetutor://materials/{material_id}")
    def get_material_resource(material_id: str) -> str:
        """id 로 교재 단건을 JSON 으로 반환한다. 없으면 ``{}`` (예외 없이 빈 객체)."""
        try:
            parsed = int(material_id)
        except ValueError:
            return json.dumps(
                {"error": f"유효하지 않은 교재 id: {material_id}"},
                ensure_ascii=False,
            )
        material = get_use_case(parsed)
        if material is None:
            return json.dumps({}, ensure_ascii=False)
        return json.dumps(_to_dict(material), ensure_ascii=False, indent=2)
