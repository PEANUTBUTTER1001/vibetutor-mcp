"""로컬 코드 스캐너 ``CodeScanner`` 구현체.

``project_root`` 하위의 Python 소스를 AST 로 스캔해 함수/클래스 심볼을 라인 범위와
함께 추출하고(SRS FR-04), 각 학습 섹션의 제목·개념 텍스트와 점수 매칭하여 실제 코드
예제를 주입한다(FR-05). 코드 예제가 이미 있는 섹션은 사용자 입력을 존중해 건드리지
않는다.

보안·성능: 가상환경/VCS/캐시/서드파티 디렉터리와 심볼릭 링크·민감 파일(.env 등)을
제외하고(FR-13/NFR-03), 파일 크기·총 스캔 개수에 상한을 두어 대용량 프로젝트에서도
빠르게 동작한다(NFR-02).
"""

from __future__ import annotations

import ast
import re
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from vibetutor_mcp.core.security import is_excluded_dir, is_sensitive, is_within_root
from vibetutor_mcp.domain.material.model import MaterialRequest, StudySection

# 성능 가드(NFR-02): 과도한 스캔 방지 상한.
_MAX_FILES = 2000
_MAX_FILE_BYTES = 512 * 1024
_MAX_SNIPPET_LINES = 40

# 토큰: 영문/숫자/밑줄 식별자 또는 한글 음절 덩어리.
_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+|[가-힣]+")

# 매칭 신호 가치가 낮은 불용어.
_STOPWORDS: frozenset[str] = frozenset(
    {
        "the",
        "and",
        "for",
        "def",
        "class",
        "self",
        "return",
        "코드",
        "예제",
        "함수",
        "클래스",
        "개념",
        "설명",
        "구현",
        "사용",
        "처리",
        "정의",
    }
)


@dataclass(frozen=True)
class _Symbol:
    """추출된 코드 심볼과 매칭에 사용할 토큰 집합."""

    name: str
    source: str
    location: str  # "relpath:start-end"
    haystack: frozenset[str]


def _tokenize(text: str) -> set[str]:
    """텍스트를 소문자 토큰 집합으로 분해(길이 1 토큰은 잡음으로 제외)."""
    return {tok.lower() for tok in _TOKEN_RE.findall(text or "") if len(tok) > 1}


def _dotted_name(node: ast.expr) -> str:
    """데코레이터 식을 점 표기 문자열로 환원(예: ``mcp.tool``)."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _dotted_name(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    if isinstance(node, ast.Call):
        return _dotted_name(node.func)
    return ""


class LocalCodeScanner:
    """프로젝트 루트의 코드를 스캔해 교재 요청에 실제 예제를 보강한다."""

    def __init__(self, project_root: str) -> None:
        self._root = Path(project_root)

    def inject_examples(self, request: MaterialRequest) -> MaterialRequest:
        """코드 예제가 비어 있는 섹션에 매칭된 실제 코드와 출처를 주입한다."""
        # 보강이 필요한 섹션이 없으면 스캔 자체를 생략(성능).
        if not any(section.code_example is None for section in request.sections):
            return request

        symbols = self._collect_symbols()
        if not symbols:
            return request

        used: set[str] = set()
        new_sections: list[StudySection] = []
        for section in request.sections:
            if section.code_example is not None:
                new_sections.append(section)
                continue
            best = self._best_match(section, symbols, used)
            if best is None:
                new_sections.append(section)
                continue
            used.add(best.location)
            new_sections.append(
                section.model_copy(
                    update={"code_example": best.source, "code_source": best.location}
                )
            )
        return request.model_copy(update={"sections": new_sections})

    # --- 내부 구현 ---

    def _collect_symbols(self) -> list[_Symbol]:
        symbols: list[_Symbol] = []
        scanned = 0
        for path in self._iter_python_files():
            if scanned >= _MAX_FILES:
                break
            scanned += 1
            try:
                text = path.read_text(encoding="utf-8")
                tree = ast.parse(text)
            except (OSError, UnicodeDecodeError, SyntaxError, ValueError):
                continue
            rel = self._relpath(path)
            for node in ast.iter_child_nodes(tree):
                symbol = self._symbol_from_node(node, text, rel)
                if symbol is not None:
                    symbols.append(symbol)
        return symbols

    def _iter_python_files(self) -> Iterator[Path]:
        root = self._root
        stack: list[Path] = [root]
        while stack:
            current = stack.pop()
            try:
                entries = list(current.iterdir())
            except OSError:
                continue
            for entry in entries:
                try:
                    if entry.is_symlink():
                        continue
                    if entry.is_dir():
                        if not is_excluded_dir(entry.name):
                            stack.append(entry)
                        continue
                    if entry.suffix != ".py" or is_sensitive(entry):
                        continue
                    if not is_within_root(entry, root):
                        continue
                    if entry.stat().st_size > _MAX_FILE_BYTES:
                        continue
                    yield entry
                except OSError:
                    continue

    def _symbol_from_node(self, node: ast.AST, source: str, rel: str) -> _Symbol | None:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            return None
        segment = ast.get_source_segment(source, node)
        if not segment:
            return None
        start = node.lineno
        end = node.end_lineno or start
        if end - start + 1 > _MAX_SNIPPET_LINES:
            head = segment.splitlines()[:_MAX_SNIPPET_LINES]
            segment = "\n".join(head) + "\n    # ... (이하 생략)"

        haystack: set[str] = _tokenize(node.name)
        for decorator in node.decorator_list:
            haystack |= _tokenize(_dotted_name(decorator))
        docstring = ast.get_docstring(node)
        if docstring:
            haystack |= _tokenize(docstring)

        return _Symbol(
            name=node.name,
            source=segment,
            location=f"{rel}:{start}-{end}",
            haystack=frozenset(haystack),
        )

    def _best_match(
        self, section: StudySection, symbols: list[_Symbol], used: set[str]
    ) -> _Symbol | None:
        query = (_tokenize(section.heading) | _tokenize(section.concept_explanation)) - _STOPWORDS
        if not query:
            return None
        heading_tokens = _tokenize(section.heading)
        best: _Symbol | None = None
        best_score = 0
        for symbol in symbols:
            if symbol.location in used:
                continue
            score = len(query & symbol.haystack)
            # 심볼명이 섹션 제목 토큰과 겹치면 가중치를 더한다.
            if heading_tokens & _tokenize(symbol.name):
                score += 2
            if score > best_score:
                best_score = score
                best = symbol
        return best

    def _relpath(self, path: Path) -> str:
        try:
            return path.resolve().relative_to(self._root.resolve()).as_posix()
        except ValueError:
            return path.name
