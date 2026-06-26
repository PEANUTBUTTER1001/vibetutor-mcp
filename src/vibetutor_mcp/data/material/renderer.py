"""Jinja2 기반 ``MaterialRenderer`` 구현체 (스캐폴딩 단계: 스텁).

교재 HTML 템플릿(``templates/material.html.j2``)과 DESIGN.md 토큰 CSS 연동은
MVP 2단계에서 구현한다. Jinja2 환경은 미리 구성해 두어 와이어링을 검증한다.
"""

from __future__ import annotations

from jinja2 import Environment, FileSystemLoader, select_autoescape

from vibetutor_mcp.domain.material.model import MaterialRequest


class JinjaMaterialRenderer:
    """교재 요청을 HTML 문자열로 렌더링한다."""

    def __init__(self, template_dir: str) -> None:
        self._env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(["html", "xml"]),
        )

    def render(self, request: MaterialRequest) -> str:
        raise NotImplementedError("MVP 2단계에서 구현: material.html.j2 렌더링")
