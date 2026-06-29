"""MVP 2단계 생성 파이프라인 단위·통합 테스트.

레이어/구현체별 동작과 안전 규칙을 검증한다. SQLAlchemy(레포지토리)·WeasyPrint
(익스포터)는 환경 의존성이 크므로, 레포지토리 테스트는 ``importorskip`` 으로 분리하고
익스포터 테스트는 가짜 ``weasyprint`` 모듈을 주입(monkeypatch)하여 네이티브 의존성
없이도 로직을 검증한다.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

from vibetutor_mcp.core import security
from vibetutor_mcp.core.exceptions import OverwriteError, PermissionDeniedError
from vibetutor_mcp.data.material.exporter import WeasyPrintExporter
from vibetutor_mcp.data.material.renderer import JinjaMaterialRenderer
from vibetutor_mcp.data.material.scanner import LocalCodeScanner
from vibetutor_mcp.domain.material.model import MaterialRequest, StudySection

_REPO_ROOT = Path(__file__).resolve().parents[1]
_TEMPLATE_DIR = _REPO_ROOT / "templates"
_FONT_DIR = _TEMPLATE_DIR / "fonts"


# --------------------------------------------------------------------------- #
# security (보안 게이트)
# --------------------------------------------------------------------------- #
def test_sanitize_filename_strips_path_separators() -> None:
    for raw in ["../etc/passwd", "a\\b\\c", "a/b:c*?", "..\\..\\x", "파이썬 I/O"]:
        out = security.sanitize_filename(raw)
        assert "/" not in out and "\\" not in out  # 경로 구분자 제거
        assert ".." not in out  # 상위 참조 무력화
        assert out  # 비어 있지 않음


def test_sanitize_filename_falls_back_when_empty() -> None:
    assert security.sanitize_filename("///") == "material"
    assert security.sanitize_filename("   ") == "material"
    assert security.sanitize_filename("..") == "material"


def test_is_sensitive_detects_env_and_keys(tmp_path: Path) -> None:
    assert security.is_sensitive(tmp_path / ".env")
    assert security.is_sensitive(tmp_path / "server.pem")
    assert not security.is_sensitive(tmp_path / "main.py")


def test_is_excluded_dir() -> None:
    assert security.is_excluded_dir(".venv")
    assert security.is_excluded_dir("__pycache__")
    assert security.is_excluded_dir(".hidden")
    assert not security.is_excluded_dir("src")


def test_is_within_root_rejects_outside(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    inside = root / "a.py"
    inside.write_text("x = 1", encoding="utf-8")
    assert security.is_within_root(inside, root)
    assert not security.is_within_root(tmp_path / "outside.py", root)


# --------------------------------------------------------------------------- #
# renderer (Jinja2 + DESIGN 토큰)
# --------------------------------------------------------------------------- #
def test_renderer_outputs_tokens_korean_and_fonts() -> None:
    renderer = JinjaMaterialRenderer(str(_TEMPLATE_DIR))
    html = renderer.render(
        MaterialRequest(
            topic_title="파이썬 데코레이터",
            sections=[
                StudySection(
                    heading="데코레이터 개념", concept_explanation="함수를 감싸는 함수다."
                ),
            ],
        ),
        "2026-01-01",
        "0" * 64,
    )
    assert "파이썬 데코레이터" in html  # 한글 제목
    assert "@font-face" in html  # 폰트 임베딩 선언 포함
    assert "var(--color-accent" in html  # DESIGN 토큰 사용(하드코딩 색상 아님)
    assert "AI 생성 초안" in html  # 초안 고지(§8.1)
    assert "Pretendard-Regular.ttf" in html  # 한글 TTF 참조
    assert "2026-01-01" in html  # 주입된 작성일자(시스템 시계 비의존)
    assert "0000000000000000" in html  # 콘텐츠 해시 콜로폰(앞 16자리)


def test_renderer_escapes_code_example() -> None:
    renderer = JinjaMaterialRenderer(str(_TEMPLATE_DIR))
    html = renderer.render(
        MaterialRequest(
            topic_title="이스케이프",
            sections=[
                StudySection(
                    heading="제네릭",
                    concept_explanation="설명",
                    code_example="List<String> & <script>",
                ),
            ],
        ),
        "2026-01-01",
        "a" * 64,
    )
    assert "&lt;String&gt;" in html  # < > 가 안전하게 이스케이프됨
    assert "<script>" not in html  # 원본 태그가 그대로 들어가지 않음


def test_renderer_renders_code_source_caption() -> None:
    renderer = JinjaMaterialRenderer(str(_TEMPLATE_DIR))
    html = renderer.render(
        MaterialRequest(
            topic_title="출처",
            sections=[
                StudySection(
                    heading="h",
                    concept_explanation="c",
                    code_example="x = 1",
                    code_source="src/foo.py:10-20",
                ),
            ],
        ),
        "2026-01-01",
        "b" * 64,
    )
    assert "출처:" in html
    assert "src/foo.py:10-20" in html


# --------------------------------------------------------------------------- #
# exporter (WeasyPrint 격리)
# --------------------------------------------------------------------------- #
def _install_fake_weasyprint(monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    """가짜 ``weasyprint`` 모듈을 주입하고 마지막 호출 인자를 기록한다."""
    recorded: dict[str, object] = {}

    class _FakeHTML:
        def __init__(self, *, string: str, base_url: str) -> None:
            recorded["string"] = string
            recorded["base_url"] = base_url

        def write_pdf(self, target: str) -> None:
            recorded["target"] = target
            Path(target).write_bytes(b"%PDF-1.7 fake\n%%EOF\n")

    module = types.ModuleType("weasyprint")
    module.HTML = _FakeHTML  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "weasyprint", module)
    return recorded


def test_exporter_writes_pdf_atomically(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    recorded = _install_fake_weasyprint(monkeypatch)
    out = tmp_path / "out"
    exporter = WeasyPrintExporter(str(out), str(_FONT_DIR))
    path = exporter.export("파이썬 기초", "<html>본문</html>")

    saved = Path(path)
    assert saved.exists() and saved.suffix == ".pdf"
    assert saved.read_bytes().startswith(b"%PDF")
    # base_url 로 폰트 디렉터리가 전달되어 @font-face 가 해석됨.
    assert recorded["base_url"] == str(_FONT_DIR)
    # 임시 .part 파일이 남지 않음(원자적 확정).
    assert not list(out.glob("*.part"))


def test_exporter_prevents_overwrite(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_weasyprint(monkeypatch)
    out = tmp_path / "out"
    out.mkdir()
    existing = "기존".encode()
    (out / "주제.pdf").write_bytes(existing)
    exporter = WeasyPrintExporter(str(out), str(_FONT_DIR))
    with pytest.raises(OverwriteError):
        exporter.export("주제", "<html></html>")
    assert (out / "주제.pdf").read_bytes() == existing  # 기존 파일 보존


def test_exporter_raises_on_unwritable_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_fake_weasyprint(monkeypatch)
    # 출력 경로의 부모가 파일이라 디렉터리 생성이 불가능 → PermissionDeniedError.
    blocker = tmp_path / "blocker"
    blocker.write_text("not a dir", encoding="utf-8")
    exporter = WeasyPrintExporter(str(blocker / "sub"), str(_FONT_DIR))
    with pytest.raises(PermissionDeniedError):
        exporter.export("주제", "<html></html>")


def test_exporter_sanitizes_traversal_filename(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_fake_weasyprint(monkeypatch)
    out = tmp_path / "out"
    exporter = WeasyPrintExporter(str(out), str(_FONT_DIR))
    path = exporter.export("../../etc/passwd", "<html></html>")
    saved = Path(path)
    # 출력은 항상 출력 디렉터리 직속 단일 파일(경로 탈출 차단).
    assert saved.parent == out
    assert ".." not in saved.name


# --------------------------------------------------------------------------- #
# scanner (AST 추출 + 점수 매칭 + 보안 필터)
# --------------------------------------------------------------------------- #
def _make_project(tmp_path: Path) -> Path:
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "calc.py").write_text(
        '"""계산 유틸."""\n\n\n'
        "def add_numbers(a, b):\n"
        '    """두 숫자를 더한다."""\n'
        "    return a + b\n",
        encoding="utf-8",
    )
    # 민감 파일과 제외 디렉터리는 스캔되면 안 된다.
    (proj / ".env").write_text("SECRET=should_not_appear", encoding="utf-8")
    venv = proj / ".venv"
    venv.mkdir()
    (venv / "vendor.py").write_text("def hidden_secret():\n    return 'x'\n", encoding="utf-8")
    return proj


def test_scanner_injects_matching_symbol(tmp_path: Path) -> None:
    proj = _make_project(tmp_path)
    scanner = LocalCodeScanner(str(proj))
    result = scanner.inject_examples(
        MaterialRequest(
            topic_title="t",
            sections=[
                StudySection(
                    heading="숫자를 더하기",
                    concept_explanation="add_numbers 함수로 두 숫자를 더한다",
                ),
            ],
        )
    )
    section = result.sections[0]
    assert section.code_example is not None
    assert "add_numbers" in section.code_example
    assert section.code_source is not None and "calc.py" in section.code_source


def test_scanner_excludes_sensitive_and_vendor(tmp_path: Path) -> None:
    proj = _make_project(tmp_path)
    scanner = LocalCodeScanner(str(proj))
    result = scanner.inject_examples(
        MaterialRequest(
            topic_title="t",
            sections=[StudySection(heading="비밀", concept_explanation="secret hidden vendor")],
        )
    )
    injected = result.sections[0].code_example or ""
    assert "SECRET" not in injected  # .env 미스캔
    assert "hidden_secret" not in injected  # .venv 제외


def test_scanner_preserves_existing_code_example(tmp_path: Path) -> None:
    proj = _make_project(tmp_path)
    scanner = LocalCodeScanner(str(proj))
    result = scanner.inject_examples(
        MaterialRequest(
            topic_title="t",
            sections=[
                StudySection(
                    heading="숫자를 더하기",
                    concept_explanation="add_numbers",
                    code_example="이미 작성된 예제",
                ),
            ],
        )
    )
    # 사용자가 제공한 코드 예제는 덮어쓰지 않는다.
    assert result.sections[0].code_example == "이미 작성된 예제"
    assert result.sections[0].code_source is None


def test_scanner_no_match_leaves_section_untouched(tmp_path: Path) -> None:
    proj = _make_project(tmp_path)
    scanner = LocalCodeScanner(str(proj))
    result = scanner.inject_examples(
        MaterialRequest(
            topic_title="t",
            sections=[
                StudySection(heading="전혀무관xyz", concept_explanation="zzz qqq wholly unrelated"),
            ],
        )
    )
    assert result.sections[0].code_example is None
    assert result.sections[0].code_source is None


# --------------------------------------------------------------------------- #
# repository (SQLAlchemy: 환경에 sqlalchemy 가 있을 때만 실행)
# --------------------------------------------------------------------------- #
def test_repository_save_list_find(tmp_path: Path) -> None:
    pytest.importorskip("sqlalchemy")
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from vibetutor_mcp.data.material.repository_impl import SqliteMaterialRepository
    from vibetutor_mcp.domain.material.model import StudyMaterial

    db_file = tmp_path / "v.sqlite3"
    engine = create_engine(f"sqlite:///{db_file}", future=True)
    factory = sessionmaker(bind=engine, future=True)
    repo = SqliteMaterialRepository(factory)

    new_id = repo.save_material(StudyMaterial(topic_title="파이썬", file_path="/x/p.pdf"))
    assert new_id >= 1

    materials = repo.list_materials()
    assert any(m.topic_title == "파이썬" for m in materials)

    found = repo.find_by_topic("파이썬")
    assert found is not None and found.file_path == "/x/p.pdf"
    assert repo.find_by_topic("존재하지 않는 주제") is None
