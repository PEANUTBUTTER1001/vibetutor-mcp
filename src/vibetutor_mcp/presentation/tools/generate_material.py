"""교재 생성 Tool 어댑터 (얇은 어댑터).

비즈니스 로직을 두지 않는다. Pydantic(``MaterialRequest``)으로 입력을 강제(방식 A)한
뒤 UseCase 로 위임하고, 결과 문자열만 반환한다.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from vibetutor_mcp.domain.material.model import MaterialRequest
from vibetutor_mcp.domain.material.usecase import GenerateTutorMaterialUseCase


def register_tools(mcp: FastMCP, use_case: GenerateTutorMaterialUseCase) -> None:
    """교재 생성 Tool 을 MCP 서버에 등록한다."""

    @mcp.tool()
    def generate_tutor_material(request: MaterialRequest) -> str:
        """표준 양식에 맞춰 사용자 코드 연동형 교재 PDF 를 생성한다."""
        material = use_case(request)
        return f"교재 생성 완료 → {material.file_path}"
