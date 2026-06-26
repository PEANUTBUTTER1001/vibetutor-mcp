"""표준 교재 작성 Prompt 어댑터 (학습 진입점, 방식 B).

일관된 교재 구조를 강제하기 위한 표준 프롬프트를 배포한다.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP


def register_prompts(mcp: FastMCP) -> None:
    """표준 교재 작성 Prompt 를 MCP 서버에 등록한다."""

    @mcp.prompt()
    def study_material_template(topic: str) -> str:
        """일관된 학습 진입점을 제공하는 표준 교재 작성 프롬프트."""
        return (
            f"'{topic}' 주제로 표준 교재를 작성한다. 각 섹션은 "
            "heading / concept_explanation / code_example / exercises 구조를 따른다. "
            "작성한 섹션들은 generate_tutor_material Tool 의 MaterialRequest 스키마로 전달한다."
        )
