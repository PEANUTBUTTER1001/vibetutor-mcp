"""WeasyPrint 기반 ``PdfExporter`` 구현체 (스캐폴딩 단계: 스텁).

WeasyPrint 는 네이티브 의존성(Pango/cairo/GDK-PixBuf)을 요구하므로 모듈 import
시점이 아니라 ``export`` 호출 시점에 **지연 import** 한다. 이렇게 하면 PDF 기능을
제외한 서버 전체는 네이티브 의존성 없이도 부팅된다.

실제 변환 로직(권한 검증 → 덮어쓰기 방지 → 한글 폰트 임베딩)은 SKILLS.md §6
패턴에 따라 MVP 2단계에서 구현한다.
"""

from __future__ import annotations

from pathlib import Path


class WeasyPrintExporter:
    """HTML 교재를 PDF 로 변환·저장한다(덮어쓰기 방지 + 한글 폰트 임베딩)."""

    def __init__(self, output_dir: str, font_dir: str) -> None:
        self._out = Path(output_dir)
        self._font_dir = Path(font_dir)

    def export(self, topic: str, html: str) -> str:
        # MVP 2단계 구현 예정:
        #   1) 권한 검증: self._out 이 존재하는 쓰기 가능 디렉터리인지
        #   2) 덮어쓰기 방지: 대상 PDF 가 이미 존재하면 OverwriteError
        #   3) 한글 폰트 임베딩: base_url=self._font_dir 로 @font-face 해석
        #   from weasyprint import HTML  # 지연 import
        raise NotImplementedError("MVP 2단계에서 구현: WeasyPrint PDF 변환")
