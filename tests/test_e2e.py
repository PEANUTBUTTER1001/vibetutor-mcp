"""E2E 통합 + 재현성 + 진단 테스트 (마크다운 → 파싱 → 렌더 → 포맷 출력 → DB).

생성 경로 전 구간을 포맷(pdf/html/markdown)별로 검증한다. WeasyPrint 는 가짜 모듈로
격리하고(네이티브 의존성 불필요), SQLAlchemy 의존 부분은 ``importorskip`` 으로 분리한다.
재현성(동일 콘텐츠→동일 해시, 포맷 무관)과 실패 진단(PipelineError·구조화 반환)은
프레임워크 의존성 없이 검증한다.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

from vibetutor_mcp.core.exceptions import PipelineError
from vibetutor_mcp.data.material.exporter import FormatRouterExporter
from vibetutor_mcp.data.material.markdown_parser import parse_markdown_to_practical_request
from vibetutor_mcp.data.material.renderer import JinjaMaterialRenderer
from vibetutor_mcp.domain.material.hashing import compute_content_hash
from vibetutor_mcp.domain.material.model import ExportFormat, PracticalMaterialRequest
from vibetutor_mcp.domain.material.usecase import GeneratePracticalMaterialUseCase
from vibetutor_mcp.presentation.tools.generate_markdown_material import register_markdown_tools

_REPO_ROOT = Path(__file__).resolve().parents[1]
_TEMPLATE_DIR = _REPO_ROOT / "templates"
_FONT_DIR = _TEMPLATE_DIR / "fonts"

_SAMPLE_MD = """# 01장. FastMCP 아키텍처 실전
### 1. 들어가며
이 장에서는 MCP 서버 구축을 다룬다.
### 4. 핵심 코드 분석
```python
@mcp.tool()
def greet_user():
    pass
```
### 5. 마주친 문제와 디버깅
[증상] 타임아웃 발생
[원인] JSON 과다 생성
[해결] 마크다운 파서 도입
"""


class _FixedClock:
    """테스트용 고정 시계(표지 날짜 결정화 검증)."""

    def __init__(self, value: str = "2026-06-29") -> None:
        self._value = value

    def today_iso(self) -> str:
        return self._value


def _install_fake_weasyprint(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakeHTML:
        def __init__(self, *, string: str, base_url: str) -> None:
            self._string = string

        def write_pdf(self, target: str) -> None:
            Path(target).write_bytes(
                b"%PDF-1.7 fake\n" + self._string.encode("utf-8") + b"\n%%EOF\n"
            )

    module = types.ModuleType("weasyprint")
    module.HTML = _FakeHTML  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "weasyprint", module)


def _build_use_case(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[GeneratePracticalMaterialUseCase, object, Path]:
    pytest.importorskip("sqlalchemy")
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from vibetutor_mcp.data.material.repository_impl import SqliteMaterialRepository

    _install_fake_weasyprint(monkeypatch)
    out = tmp_path / "out"
    engine = create_engine(f"sqlite:///{tmp_path / 'v.sqlite3'}", future=True)
    factory = sessionmaker(bind=engine, future=True)
    repo = SqliteMaterialRepository(factory)
    use_case = GeneratePracticalMaterialUseCase(
        renderer=JinjaMaterialRenderer(str(_TEMPLATE_DIR)),
        exporter=FormatRouterExporter(str(out), str(_FONT_DIR)),
        repository=repo,
        clock=_FixedClock(),
    )
    return use_case, repo, out


def _make_request(fmt: ExportFormat, md: str = _SAMPLE_MD) -> PracticalMaterialRequest:
    req = parse_markdown_to_practical_request("E2E 교재", md)
    return req.model_copy(update={"format": fmt})


# --------------------------------------------------------------------------- #
# E2E 포맷별 (SQLAlchemy 필요)
# --------------------------------------------------------------------------- #
def test_e2e_pdf_creates_file_db_and_hash(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    use_case, repo, _ = _build_use_case(tmp_path, monkeypatch)
    material = use_case(_make_request(ExportFormat.PDF))

    saved = Path(material.file_path)
    assert saved.exists() and saved.suffix == ".pdf"
    assert saved.read_bytes().startswith(b"%PDF")
    assert material.id >= 1
    assert material.content_hash is not None and len(material.content_hash) == 64
    body = saved.read_bytes()
    # 표지 콜로폰의 작성일자·해시(앞 16자리)가 렌더 산출물에 포함됨(결정화·재현성).
    assert b"2026-06-29" in body
    assert material.content_hash[:16].encode() in body
    found = repo.find_by_id(material.id)  # type: ignore[attr-defined]
    assert found is not None and found.content_hash == material.content_hash


def test_e2e_html_writes_rendered_html(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    use_case, _, _ = _build_use_case(tmp_path, monkeypatch)
    material = use_case(_make_request(ExportFormat.HTML))

    saved = Path(material.file_path)
    assert saved.suffix == ".html"
    html = saved.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in html
    assert "E2E 교재" in html
    assert "@font-face" in html  # PDF 와 동일 레이아웃(폰트 선언 포함)
    assert "2026-06-29" in html  # 주입된 작성일자


def test_e2e_markdown_is_lossless_passthrough(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    use_case, _, _ = _build_use_case(tmp_path, monkeypatch)
    material = use_case(_make_request(ExportFormat.MARKDOWN))

    saved = Path(material.file_path)
    assert saved.suffix == ".md"
    text = saved.read_text(encoding="utf-8")
    # 원본 마크다운이 파서를 거치지 않고 그대로 보존됨(손실 0).
    assert _SAMPLE_MD.rstrip("\n") in text
    assert "```python" in text  # 코드블록 원형 유지
    assert "[증상] 타임아웃 발생" in text  # 파서가 변형하던 표현도 원문 그대로
    # (B) 콜로폰 푸터: 작성일자·content_hash 가 HTML 주석으로 덧붙음.
    assert "<!-- VibeTutor" in text
    assert "2026-06-29" in text
    assert material.content_hash is not None
    assert material.content_hash[:16] in text


def test_e2e_same_topic_pdf_and_markdown_coexist(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    use_case, _, _ = _build_use_case(tmp_path, monkeypatch)
    pdf = use_case(_make_request(ExportFormat.PDF))
    md = use_case(_make_request(ExportFormat.MARKDOWN))
    assert Path(pdf.file_path).suffix == ".pdf"
    assert Path(md.file_path).suffix == ".md"
    assert Path(pdf.file_path).exists() and Path(md.file_path).exists()


def test_e2e_export_conflict_same_format_raises_pipeline_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    use_case, _, _ = _build_use_case(tmp_path, monkeypatch)
    use_case(_make_request(ExportFormat.PDF))  # 1회차 성공
    with pytest.raises(PipelineError) as excinfo:
        use_case(_make_request(ExportFormat.PDF))  # 2회차: 덮어쓰기 방지 → export 실패
    assert excinfo.value.stage == "export"
    assert excinfo.value.hint  # 사용자 행동 힌트 포함


# --------------------------------------------------------------------------- #
# 재현성 — 프레임워크 의존성 불필요
# --------------------------------------------------------------------------- #
def test_content_hash_is_deterministic() -> None:
    assert compute_content_hash(_make_request(ExportFormat.PDF)) == compute_content_hash(
        _make_request(ExportFormat.PDF)
    )


def test_content_hash_ignores_format_and_source_markdown() -> None:
    """같은 콘텐츠는 출력 포맷이 달라도 동일한 해시(콘텐츠 동일성 식별자)를 갖는다."""
    pdf_req = _make_request(ExportFormat.PDF)
    md_req = _make_request(ExportFormat.MARKDOWN)
    assert compute_content_hash(pdf_req) == compute_content_hash(md_req)


def test_content_hash_changes_with_content() -> None:
    base = PracticalMaterialRequest(topic_title="재현성", sections=[])
    changed = base.model_copy(update={"topic_title": "다른 주제"})
    assert compute_content_hash(base) != compute_content_hash(changed)


# --------------------------------------------------------------------------- #
# 진단 — Tool 어댑터 구조화 반환(가짜 MCP/UseCase, 프레임워크 의존성 불필요)
# --------------------------------------------------------------------------- #
class _FakeMCP:
    def __init__(self) -> None:
        self.tools: dict[str, object] = {}

    def tool(self):  # type: ignore[no-untyped-def]
        def deco(fn):  # type: ignore[no-untyped-def]
            self.tools[fn.__name__] = fn
            return fn

        return deco


def test_generate_tool_returns_structured_error_on_failure() -> None:
    class _FailingUseCase:
        def __call__(self, request: PracticalMaterialRequest):  # type: ignore[no-untyped-def]
            raise PipelineError("render", "템플릿을 찾을 수 없음", "템플릿 경로를 확인하세요.")

    mcp = _FakeMCP()
    register_markdown_tools(mcp, _FailingUseCase())  # type: ignore[arg-type]
    tool = mcp.tools["generate_book_from_markdown"]
    out = tool("주제", "# 01장. 제목\n### 1. 들어가며\n내용\n")  # type: ignore[operator]

    assert "통교재 생성 실패" in out
    assert "stage): render" in out
    assert "템플릿을 찾을 수 없음" in out
    assert "템플릿 경로를 확인하세요." in out
