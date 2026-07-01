"""보안 게이트 + 리포지토리 단위·통합 테스트.

SQLAlchemy(레포지토리)는 환경 의존성이 크므로 ``importorskip`` 으로 분리한다.
익스포터/렌더러/포맷 분기 테스트는 ``test_export_formats.py`` 로 이관했다.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from vibetutor_mcp.core import security


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
