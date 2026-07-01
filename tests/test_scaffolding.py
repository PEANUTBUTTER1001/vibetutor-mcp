"""스캐폴딩 검증 테스트.

서버 부팅, 입력 스키마 강제, 의존성 역전(Domain 무의존)을 확인한다.
"""

from __future__ import annotations

import importlib
import pkgutil

import pytest
from pydantic import ValidationError

import vibetutor_mcp.domain as domain_pkg
from vibetutor_mcp.domain.material.model import (
    ExportFormat,
    PracticalMaterialRequest,
    PracticalStudySection,
)
from vibetutor_mcp.main import build


def test_build_returns_fastmcp_server() -> None:
    """build() 가 예외 없이 FastMCP 인스턴스를 구성한다 (시나리오 #1)."""
    from mcp.server.fastmcp import FastMCP

    server = build()
    assert isinstance(server, FastMCP)


def test_practical_request_accepts_empty_sections_and_defaults() -> None:
    """빈 섹션 목록은 허용되며, 포맷 기본값은 PDF 다 (시나리오 #1·#4)."""
    req = PracticalMaterialRequest(topic_title="파이썬 기초", sections=[])
    assert req.topic_title == "파이썬 기초"
    assert req.sections == []
    assert req.format is ExportFormat.PDF  # 미지정 시 안전 기본값
    assert req.source_markdown is None


def test_practical_section_rejects_blank_heading() -> None:
    """필수 필드 누락/공백은 ValidationError 로 차단된다 (시나리오 #5)."""
    with pytest.raises(ValidationError):
        PracticalStudySection(heading="")


def test_export_format_has_three_values() -> None:
    """출력 포맷 enum 은 pdf/html/markdown 세 가지를 노출한다."""
    assert {fmt.value for fmt in ExportFormat} == {"pdf", "html", "markdown"}


def test_domain_has_no_framework_imports() -> None:
    """domain 패키지의 어떤 모듈도 프레임워크를 import 하지 않는다 (시나리오 #7)."""
    forbidden = {"jinja2", "weasyprint", "sqlalchemy", "mcp"}
    for mod in pkgutil.walk_packages(domain_pkg.__path__, prefix="vibetutor_mcp.domain."):
        module = importlib.import_module(mod.name)
        imported = set(getattr(module, "__dict__", {}).keys())
        # 모듈 전역에 프레임워크 모듈 객체가 바인딩되어 있지 않은지 확인
        for name in forbidden:
            assert name not in imported, f"{mod.name} 가 {name} 을(를) import 함"
