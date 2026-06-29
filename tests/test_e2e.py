"""MVP 3단계 E2E 통합 + 재현성 + 진단 테스트.

생성 경로(스캔→해시→렌더→PDF→DB) 전 구간을 한 번에 검증한다. WeasyPrint 는 가짜
모듈로 격리하고(네이티브 의존성 불필요), SQLAlchemy 의존 부분은 ``importorskip`` 으로
분리한다. 재현성(동일 입력→동일 해시)과 실패 진단(PipelineError·구조화 반환)은
프레임워크 의존성 없이 검증한다.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

from vibetutor_mcp.core.exceptions import PipelineError
from vibetutor_mcp.data.material.exporter import WeasyPrintExporter
from vibetutor_mcp.data.material.renderer import JinjaMaterialRenderer
from vibetutor_mcp.data.material.scanner import LocalCodeScanner
from vibetutor_mcp.domain.material.hashing import compute_content_hash
from vibetutor_mcp.domain.material.model import MaterialRequest, StudySection
from vibetutor_mcp.domain.material.usecase import GenerateTutorMaterialUseCase
from vibetutor_mcp.presentation.tools.generate_material import register_tools

_REPO_ROOT = Path(__file__).resolve().parents[1]
_TEMPLATE_DIR = _REPO_ROOT / "templates"
_FONT_DIR = _TEMPLATE_DIR / "fonts"


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


def _make_project(tmp_path: Path) -> Path:
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "greeting.py").write_text(
        "def greet_user(name):\n"
        '    """사용자에게 인사 메시지를 만든다."""\n'
        '    return f"안녕하세요 {name}"\n',
        encoding="utf-8",
    )
    return proj


def _build_use_case(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[GenerateTutorMaterialUseCase, object, Path]:
    pytest.importorskip("sqlalchemy")
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from vibetutor_mcp.data.material.repository_impl import SqliteMaterialRepository

    _install_fake_weasyprint(monkeypatch)
    proj = _make_project(tmp_path)
    out = tmp_path / "out"
    engine = create_engine(f"sqlite:///{tmp_path / 'v.sqlite3'}", future=True)
    factory = sessionmaker(bind=engine, future=True)
    repo = SqliteMaterialRepository(factory)
    use_case = GenerateTutorMaterialUseCase(
        scanner=LocalCodeScanner(str(proj)),
        renderer=JinjaMaterialRenderer(str(_TEMPLATE_DIR)),
        exporter=WeasyPrintExporter(str(out), str(_FONT_DIR)),
        repository=repo,
        clock=_FixedClock(),
    )
    return use_case, repo, out


# --------------------------------------------------------------------------- #
# E2E (스캔→해시→렌더→PDF→DB) — SQLAlchemy 필요
# --------------------------------------------------------------------------- #
def test_e2e_generate_creates_pdf_db_and_hash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    use_case, repo, _ = _build_use_case(tmp_path, monkeypatch)
    request = MaterialRequest(
        topic_title="E2E 교재",
        sections=[
            StudySection(
                heading="사용자 인사",
                concept_explanation="greet_user 함수로 사용자에게 인사한다",
            ),
        ],
    )
    material = use_case(request)

    saved = Path(material.file_path)
    assert saved.exists() and saved.suffix == ".pdf"  # PDF 실제 생성
    assert saved.read_bytes().startswith(b"%PDF")
    assert material.id >= 1  # DB id 부여
    assert material.content_hash is not None and len(material.content_hash) == 64
    # 표지 날짜·해시가 렌더 산출물(PDF 바이트)에 포함됨(결정화·재현성 식별자)
    body = saved.read_bytes()
    assert b"2026-06-29" in body
    assert material.content_hash[:16].encode() in body
    # DB 단건 조회로 해시 보존 확인
    found = repo.find_by_id(material.id)  # type: ignore[attr-defined]
    assert found is not None and found.content_hash == material.content_hash
    # 스캐너가 실제 코드(greet_user)를 주입했는지 PDF 본문으로 확인
    assert b"greet_user" in body


def test_e2e_export_conflict_raises_pipeline_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    use_case, _, _ = _build_use_case(tmp_path, monkeypatch)
    request = MaterialRequest(
        topic_title="중복 제목",
        sections=[StudySection(heading="h", concept_explanation="c", code_example="x = 1")],
    )
    use_case(request)  # 1회차 성공
    with pytest.raises(PipelineError) as excinfo:
        use_case(request)  # 2회차: 덮어쓰기 방지 → export 단계 실패
    assert excinfo.value.stage == "export"
    assert excinfo.value.hint  # 사용자 행동 힌트 포함


# --------------------------------------------------------------------------- #
# 재현성 — 프레임워크 의존성 불필요
# --------------------------------------------------------------------------- #
def test_content_hash_is_deterministic() -> None:
    def make() -> MaterialRequest:
        return MaterialRequest(
            topic_title="재현성",
            sections=[
                StudySection(heading="h", concept_explanation="c", code_example="x = 1"),
            ],
        )

    assert compute_content_hash(make()) == compute_content_hash(make())


def test_content_hash_changes_with_content() -> None:
    base = MaterialRequest(
        topic_title="재현성",
        sections=[StudySection(heading="h", concept_explanation="c")],
    )
    changed = MaterialRequest(
        topic_title="재현성",
        sections=[StudySection(heading="h", concept_explanation="다른 설명")],
    )
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
        def __call__(self, request: MaterialRequest):  # type: ignore[no-untyped-def]
            raise PipelineError("render", "템플릿을 찾을 수 없음", "템플릿 경로를 확인하세요.")

    mcp = _FakeMCP()
    register_tools(mcp, _FailingUseCase())  # type: ignore[arg-type]
    tool = mcp.tools["generate_tutor_material"]
    out = tool(MaterialRequest(topic_title="t", sections=[]))  # type: ignore[operator]

    assert "교재 생성 실패" in out
    assert "stage): render" in out
    assert "템플릿을 찾을 수 없음" in out
    assert "템플릿 경로를 확인하세요." in out
