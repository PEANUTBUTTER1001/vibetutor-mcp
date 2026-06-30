"""10단계 실전 교재 생성 Tool 어댑터 (얇은 어댑터).

비즈니스 로직을 두지 않는다. Pydantic(``PracticalMaterialRequest``)으로 입력을 강제한
뒤 Practical UseCase 로 위임하고, 결과 문자열만 반환한다.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from vibetutor_mcp.core.exceptions import PipelineError
from vibetutor_mcp.domain.material.model import PracticalMaterialRequest
from vibetutor_mcp.domain.material.usecase import GeneratePracticalMaterialUseCase


def register_practical_tools(mcp: FastMCP, use_case: GeneratePracticalMaterialUseCase) -> None:
    """실전 교재 생성 Tool 을 MCP 서버에 등록한다."""

    @mcp.tool()
    def generate_practical_material(request: PracticalMaterialRequest) -> str:
        """단일 챕터 교재를 정밀 생성합니다. (통교재는 generate_book_from_markdown 사용)"""
        try:
            material = use_case(request)
        except PipelineError as exc:
            return (
                "실전 교재 생성 실패\n"
                f"- 단계(stage): {exc.stage}\n"
                f"- 사유(reason): {exc.reason}\n"
                f"- 힌트(hint): {exc.hint}"
            )
        digest = material.content_hash[:12] if material.content_hash else "-"
        return f"실전 교재 생성 완료 → {material.file_path} (id={material.id}, hash={digest})"
