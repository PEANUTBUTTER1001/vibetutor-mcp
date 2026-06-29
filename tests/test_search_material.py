"""교재 검색(search_material) 테스트.

UseCase 단락 로직과 Tool 어댑터 포맷은 가짜 리포지토리로 검증하고, 실제 LIKE 검색·
와일드카드 이스케이프는 SQLAlchemy(``importorskip``)로 검증한다.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from vibetutor_mcp.domain.material.model import StudyMaterial
from vibetutor_mcp.domain.material.query import SearchMaterialUseCase
from vibetutor_mcp.presentation.tools.search_material import register_search_tool


class _FakeRepo:
    """검색만 구현한 가짜 리포지토리(질의 인자 기록)."""

    def __init__(self, results: list[StudyMaterial]) -> None:
        self._results = results
        self.calls: list[str] = []

    def search_materials(self, query: str) -> list[StudyMaterial]:
        self.calls.append(query)
        return self._results


class _FakeMCP:
    def __init__(self) -> None:
        self.tools: dict[str, object] = {}

    def tool(self):  # type: ignore[no-untyped-def]
        def deco(fn):  # type: ignore[no-untyped-def]
            self.tools[fn.__name__] = fn
            return fn

        return deco


def test_search_usecase_short_circuits_blank_query() -> None:
    repo = _FakeRepo([StudyMaterial(topic_title="x", file_path="/x")])
    use_case = SearchMaterialUseCase(repo)  # type: ignore[arg-type]
    assert use_case("   ") == []  # 공백 질의는 빈 결과
    assert repo.calls == []  # 리포지토리 호출조차 하지 않음


def test_search_usecase_trims_and_delegates() -> None:
    expected = [StudyMaterial(topic_title="파이썬", file_path="/p", id=3)]
    repo = _FakeRepo(expected)
    use_case = SearchMaterialUseCase(repo)  # type: ignore[arg-type]
    assert use_case("  파이썬  ") == expected
    assert repo.calls == ["파이썬"]  # 트림 후 위임


def test_search_tool_formats_results_and_empty() -> None:
    repo = _FakeRepo([StudyMaterial(topic_title="데코레이터", file_path="/d.pdf", id=7)])
    mcp = _FakeMCP()
    register_search_tool(mcp, SearchMaterialUseCase(repo))  # type: ignore[arg-type]
    out = mcp.tools["search_material"]("데코")  # type: ignore[operator]
    assert "검색 결과 1건" in out and "[7] 데코레이터" in out

    empty_mcp = _FakeMCP()
    register_search_tool(empty_mcp, SearchMaterialUseCase(_FakeRepo([])))  # type: ignore[arg-type]
    empty_out = empty_mcp.tools["search_material"]("없음")  # type: ignore[operator]
    assert "일치하는 교재가 없습니다" in empty_out


# --------------------------------------------------------------------------- #
# 실제 LIKE 검색 + 와일드카드 이스케이프 (SQLAlchemy 필요)
# --------------------------------------------------------------------------- #
def _make_repo(tmp_path: Path):  # type: ignore[no-untyped-def]
    pytest.importorskip("sqlalchemy")
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from vibetutor_mcp.data.material.repository_impl import SqliteMaterialRepository

    engine = create_engine(f"sqlite:///{tmp_path / 's.sqlite3'}", future=True)
    return SqliteMaterialRepository(sessionmaker(bind=engine, future=True))


def test_repo_search_partial_match(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    repo.save_material(StudyMaterial(topic_title="파이썬 데코레이터", file_path="/a.pdf"))
    repo.save_material(StudyMaterial(topic_title="자바 제네릭", file_path="/b.pdf"))

    hits = repo.search_materials("데코")
    assert len(hits) == 1 and hits[0].topic_title == "파이썬 데코레이터"
    assert repo.search_materials("없는주제") == []


def test_repo_search_escapes_wildcards(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    repo.save_material(StudyMaterial(topic_title="할인 50% 정책", file_path="/c.pdf"))
    repo.save_material(StudyMaterial(topic_title="일반 정책", file_path="/d.pdf"))

    # '%' 는 와일드카드가 아니라 리터럴로 취급되어야 한다.
    assert [m.topic_title for m in repo.search_materials("50%")] == ["할인 50% 정책"]
    # '_' 도 단일 문자 와일드카드가 아니라 리터럴.
    assert repo.search_materials("_") == []
