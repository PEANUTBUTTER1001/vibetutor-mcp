"""스캐폴딩 검증 테스트.

서버 부팅, 입력 스키마 강제, 의존성 역전(Domain 무의존), 스텁 동작을 확인한다.
"""

from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path

import pytest
from pydantic import ValidationError

import vibetutor_mcp.domain as domain_pkg
from vibetutor_mcp.domain.material.model import MaterialRequest, StudySection
from vibetutor_mcp.main import build


def test_build_returns_fastmcp_server() -> None:
    """build() 가 예외 없이 FastMCP 인스턴스를 구성한다 (시나리오 #1)."""
    from mcp.server.fastmcp import FastMCP

    server = build()
    assert isinstance(server, FastMCP)


def test_material_request_accepts_empty_sections() -> None:
    """빈 섹션 목록은 허용된다 (시나리오 #4)."""
    req = MaterialRequest(topic_title="파이썬 기초", sections=[])
    assert req.topic_title == "파이썬 기초"
    assert req.sections == []


def test_study_section_optional_code_and_exercises() -> None:
    """code_example / exercises 는 선택값이다 (이론 중심 교재 지원)."""
    section = StudySection(heading="제목", concept_explanation="설명")
    assert section.code_example is None
    assert section.exercises is None


def test_study_section_rejects_blank_heading() -> None:
    """필수 필드 누락/공백은 ValidationError 로 차단된다 (시나리오 #5)."""
    with pytest.raises(ValidationError):
        StudySection(heading="", concept_explanation="설명")


def test_scanner_returns_request_without_error(tmp_path: Path) -> None:
    """MVP 2단계: 스캐너는 더 이상 NotImplementedError 를 던지지 않고 요청을 반환한다."""
    from vibetutor_mcp.data.material.scanner import LocalCodeScanner

    scanner = LocalCodeScanner(project_root=str(tmp_path))
    request = MaterialRequest(
        topic_title="t",
        sections=[StudySection(heading="제목", concept_explanation="설명")],
    )
    result = scanner.inject_examples(request)
    assert isinstance(result, MaterialRequest)
    assert len(result.sections) == 1


def test_domain_has_no_framework_imports() -> None:
    """domain 패키지의 어떤 모듈도 프레임워크를 import 하지 않는다 (시나리오 #7)."""
    forbidden = {"jinja2", "weasyprint", "sqlalchemy", "mcp"}
    for mod in pkgutil.walk_packages(domain_pkg.__path__, prefix="vibetutor_mcp.domain."):
        module = importlib.import_module(mod.name)
        imported = set(getattr(module, "__dict__", {}).keys())
        # 모듈 전역에 프레임워크 모듈 객체가 바인딩되어 있지 않은지 확인
        for name in forbidden:
            assert name not in imported, f"{mod.name} 가 {name} 을(를) import 함"
