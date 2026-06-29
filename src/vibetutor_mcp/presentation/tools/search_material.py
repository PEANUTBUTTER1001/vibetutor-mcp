"""교재 검색 Tool 어댑터 (얇은 어댑터).

누적된 교재를 제목 부분일치로 검색한다(FR-11). 비즈니스 로직 없이 UseCase 로
위임하고, 사람이 읽기 쉬운 결과 문자열만 반환한다.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from vibetutor_mcp.domain.material.query import SearchMaterialUseCase


def register_search_tool(mcp: FastMCP, use_case: SearchMaterialUseCase) -> None:
    """교재 검색 Tool 을 MCP 서버에 등록한다."""

    @mcp.tool()
    def search_material(query: str) -> str:
        """제목에 검색어가 포함된 누적 교재를 최신순으로 찾는다."""
        results = use_case(query)
        if not results:
            return f"'{query}' 와(과) 일치하는 교재가 없습니다."
        lines = [f"'{query}' 검색 결과 {len(results)}건:"]
        lines += [f"- [{m.id}] {m.topic_title} → {m.file_path}" for m in results]
        return "\n".join(lines)
