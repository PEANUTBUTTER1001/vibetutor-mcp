"""다중 포맷 익스포터(FormatRouterExporter) 단위 테스트.

PDF 는 가짜 ``weasyprint`` 모듈로 격리하고, HTML/Markdown 은 텍스트 쓰기를 직접 검증한다.
모든 포맷에 동일하게 적용되는 파일 안전 규칙(권한·덮어쓰기 방지·원자적 쓰기·파일명
안전화)을 확인한다.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

from vibetutor_mcp.core.exceptions import OverwriteError, PermissionDeniedError
from vibetutor_mcp.data.material.exporter import FormatRouterExporter
from vibetutor_mcp.domain.material.model import ExportFormat

_REPO_ROOT = Path(__file__).resolve().parents[1]
_FONT_DIR = _REPO_ROOT / "templates" / "fonts"


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


# --------------------------------------------------------------------------- #
# 포맷별 정상 출력
# --------------------------------------------------------------------------- #
def test_exporter_writes_pdf_atomically(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    recorded = _install_fake_weasyprint(monkeypatch)
    out = tmp_path / "out"
    exporter = FormatRouterExporter(str(out), str(_FONT_DIR))
    path = exporter.export("파이썬 기초", "<html>본문</html>", ExportFormat.PDF)

    saved = Path(path)
    assert saved.exists() and saved.suffix == ".pdf"
    assert saved.read_bytes().startswith(b"%PDF")
    # base_url 로 폰트 디렉터리가 전달되어 @font-face 가 해석됨.
    assert recorded["base_url"] == str(_FONT_DIR)
    # 임시 .part 파일이 남지 않음(원자적 확정).
    assert not list(out.glob("*.part"))


def test_exporter_writes_html_verbatim(tmp_path: Path) -> None:
    out = tmp_path / "out"
    exporter = FormatRouterExporter(str(out), str(_FONT_DIR))
    html = "<!DOCTYPE html><html><body>실전 교재</body></html>"
    path = exporter.export("HTML 교재", html, ExportFormat.HTML)

    saved = Path(path)
    assert saved.suffix == ".html"
    assert saved.read_text(encoding="utf-8") == html  # 렌더 결과 그대로
    assert not list(out.glob("*.part"))


def test_exporter_writes_markdown_verbatim(tmp_path: Path) -> None:
    out = tmp_path / "out"
    exporter = FormatRouterExporter(str(out), str(_FONT_DIR))
    md = "# 01장. 제목\n### 1. 들어가며\n원본 그대로\n\n<!-- VibeTutor · ... -->\n"
    path = exporter.export("MD 교재", md, ExportFormat.MARKDOWN)

    saved = Path(path)
    assert saved.suffix == ".md"
    assert saved.read_text(encoding="utf-8") == md  # 손실 없이 그대로


# --------------------------------------------------------------------------- #
# 파일 안전 규칙
# --------------------------------------------------------------------------- #
def test_exporter_prevents_overwrite_same_format(tmp_path: Path) -> None:
    out = tmp_path / "out"
    out.mkdir()
    (out / "주제.html").write_text("기존", encoding="utf-8")
    exporter = FormatRouterExporter(str(out), str(_FONT_DIR))
    with pytest.raises(OverwriteError):
        exporter.export("주제", "<html></html>", ExportFormat.HTML)
    assert (out / "주제.html").read_text(encoding="utf-8") == "기존"  # 기존 보존


def test_exporter_allows_same_topic_across_formats(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """확장자가 다르므로 같은 제목이라도 포맷별로 공존한다(경로 충돌 없음)."""
    _install_fake_weasyprint(monkeypatch)
    out = tmp_path / "out"
    exporter = FormatRouterExporter(str(out), str(_FONT_DIR))
    pdf_path = exporter.export("동일 제목", "<html></html>", ExportFormat.PDF)
    md_path = exporter.export("동일 제목", "# 동일 제목\n", ExportFormat.MARKDOWN)
    assert Path(pdf_path).suffix == ".pdf"
    assert Path(md_path).suffix == ".md"
    assert Path(pdf_path).exists() and Path(md_path).exists()


def test_exporter_raises_on_unwritable_output(tmp_path: Path) -> None:
    # 출력 경로의 부모가 파일이라 디렉터리 생성이 불가능 → PermissionDeniedError.
    blocker = tmp_path / "blocker"
    blocker.write_text("not a dir", encoding="utf-8")
    exporter = FormatRouterExporter(str(blocker / "sub"), str(_FONT_DIR))
    with pytest.raises(PermissionDeniedError):
        exporter.export("주제", "본문", ExportFormat.MARKDOWN)


def test_exporter_sanitizes_traversal_filename(tmp_path: Path) -> None:
    out = tmp_path / "out"
    exporter = FormatRouterExporter(str(out), str(_FONT_DIR))
    path = exporter.export("../../etc/passwd", "본문", ExportFormat.HTML)
    saved = Path(path)
    # 출력은 항상 출력 디렉터리 직속 단일 파일(경로 탈출 차단).
    assert saved.parent == out
    assert ".." not in saved.name
