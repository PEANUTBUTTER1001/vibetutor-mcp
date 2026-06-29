"""FastMCP 서버 엔트리포인트 및 Composition Root.

모든 의존성 와이어링(인터페이스 → 구현체)은 오직 이 모듈에서만 수행한다.
UseCase 와 Presentation 어댑터는 구현체를 알지 못한다.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from vibetutor_mcp.core.config import Settings
from vibetutor_mcp.data.material.exporter import WeasyPrintExporter
from vibetutor_mcp.data.material.renderer import JinjaMaterialRenderer
from vibetutor_mcp.data.material.repository_impl import SqliteMaterialRepository
from vibetutor_mcp.data.material.scanner import LocalCodeScanner
from vibetutor_mcp.data.system_clock import SystemClock
from vibetutor_mcp.domain.material.query import (
    GetMaterialUseCase,
    ListMaterialsUseCase,
    SearchMaterialUseCase,
)
from vibetutor_mcp.domain.material.usecase import GenerateTutorMaterialUseCase
from vibetutor_mcp.presentation.prompts.template import register_prompts
from vibetutor_mcp.presentation.resources.materials import register_resources
from vibetutor_mcp.presentation.tools.generate_material import register_tools
from vibetutor_mcp.presentation.tools.search_material import register_search_tool


def build() -> FastMCP:
    """설정을 읽어 구현체를 조립하고 등록을 마친 FastMCP 서버를 반환한다."""
    cfg = Settings()

    repository = SqliteMaterialRepository(cfg.session_factory)
    generate_use_case = GenerateTutorMaterialUseCase(
        scanner=LocalCodeScanner(cfg.project_root),
        renderer=JinjaMaterialRenderer(cfg.template_dir),
        exporter=WeasyPrintExporter(cfg.output_dir, cfg.font_dir),
        repository=repository,
        clock=SystemClock(),
    )
    search_use_case = SearchMaterialUseCase(repository)
    list_use_case = ListMaterialsUseCase(repository)
    get_use_case = GetMaterialUseCase(repository)

    mcp = FastMCP("VibeTutor")
    register_prompts(mcp)
    register_tools(mcp, generate_use_case)
    register_search_tool(mcp, search_use_case)
    register_resources(mcp, list_use_case, get_use_case)
    return mcp


def main() -> None:
    """콘솔 스크립트 진입점. 기본 stdio 전송으로 서버를 실행한다."""
    build().run()


if __name__ == "__main__":
    main()
