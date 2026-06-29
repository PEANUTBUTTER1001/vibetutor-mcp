"""도메인이 의존하는 외부 협력자(Port) 인터페이스.

Domain 은 Jinja2/WeasyPrint/파일시스템을 직접 알지 못한다. UseCase 는 여기 정의된
``Protocol`` 에만 의존하고, 실제 구현체는 ``data`` 레이어에 두며 ``main.py``
(Composition Root)에서 주입한다.
"""

from __future__ import annotations

from typing import Protocol

from .model import MaterialRequest


class CodeScanner(Protocol):
    """로컬 프로젝트 코드를 스캔해 섹션에 실제 예제를 주입한다."""

    def inject_examples(self, request: MaterialRequest) -> MaterialRequest:
        """요청을 받아 코드 예제가 보강된 새 요청을 반환한다."""
        ...


class MaterialRenderer(Protocol):
    """검증된 요청을 교재 HTML 문자열로 렌더링한다(예: Jinja2)."""

    def render(self, request: MaterialRequest, generated_at: str, content_hash: str) -> str:
        """렌더링된 HTML 문자열을 반환한다.

        ``generated_at`` (표지 작성일자)·``content_hash`` (재현성 식별자)는 비결정적
        값을 렌더러 내부에서 만들지 않도록 호출자(UseCase)가 결정해 주입한다(NFR-10).
        """
        ...


class PdfExporter(Protocol):
    """HTML 을 PDF 로 변환·저장하고 저장 경로를 반환한다(예: WeasyPrint)."""

    def export(self, topic: str, html: str) -> str:
        """저장된 PDF 파일의 절대 경로를 반환한다."""
        ...


class Clock(Protocol):
    """현재 날짜를 제공하는 시계(표지 작성일자 결정화·테스트 고정용 Port)."""

    def today_iso(self) -> str:
        """``YYYY-MM-DD`` 형식의 오늘 날짜 문자열을 반환한다."""
        ...
