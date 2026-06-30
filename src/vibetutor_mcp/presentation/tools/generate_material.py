"""교재 생성 Tool 어댑터 (얇은 어댑터).

비즈니스 로직을 두지 않는다. Pydantic(``MaterialRequest``)으로 입력을 강제(방식 A)한
뒤 UseCase 로 위임하고, 결과 문자열만 반환한다.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from vibetutor_mcp.core.exceptions import PipelineError
from vibetutor_mcp.domain.material.model import MaterialRequest
from vibetutor_mcp.domain.material.usecase import GenerateTutorMaterialUseCase


def register_tools(mcp: FastMCP, use_case: GenerateTutorMaterialUseCase) -> None:
    """교재 생성 Tool 을 MCP 서버에 등록한다."""

    @mcp.tool()
    def generate_tutor_material(request: MaterialRequest) -> str:
        """[특수 목적용] 사용자가 직접 구조화된 JSON 데이터 구조를 세부적으로 입력했거나,
        단일 챕터/섹션 단위로 정밀하게 로컬 코드를 스캔하여 교재를 만들 때만 사용하십시오.
        일반적인 포괄적 교재 생성 요청에는 이 툴을 사용하지 마십시오.
        """
        # 얇은 어댑터: 비즈니스 로직 없이 위임하고, 실패는 구조화해 사람이 읽을 수 있게
        # 변환한다(stage/reason/hint, FR-14). 예외를 그대로 누출시키지 않는다.
        try:
            material = use_case(request)
        except PipelineError as exc:
            return (
                "교재 생성 실패\n"
                f"- 단계(stage): {exc.stage}\n"
                f"- 사유(reason): {exc.reason}\n"
                f"- 힌트(hint): {exc.hint}"
            )
        digest = material.content_hash[:12] if material.content_hash else "-"
        return f"교재 생성 완료 → {material.file_path} (id={material.id}, hash={digest})"
