"""WeasyPrint 기반 ``PdfExporter`` 구현체.

HTML 교재를 PDF 로 변환·저장한다. PDF 생성의 3대 필수 선행 조건을 강제한다:
권한 검증 → 덮어쓰기 방지 → 한글 폰트 임베딩(SKILLS.md §6, SRS FR-07·FR-08·FR-09).
또한 임시 파일에 렌더링한 뒤 ``os.replace`` 로 원자적으로 확정하여, 중간 실패 시
부분(깨진) PDF 가 남지 않도록 한다(NFR-06).

WeasyPrint 는 네이티브 의존성(Pango/cairo/GDK-PixBuf)을 요구하므로 모듈 import
시점이 아니라 ``export`` 호출 시점에 **지연 import** 한다. 이렇게 하면 PDF 기능을
제외한 서버 전체는 네이티브 의존성 없이도 부팅·테스트된다.
"""

from __future__ import annotations

import os
from pathlib import Path

from vibetutor_mcp.core.exceptions import OverwriteError, PermissionDeniedError
from vibetutor_mcp.core.security import sanitize_filename


class WeasyPrintExporter:
    """HTML 교재를 PDF 로 변환·저장한다(권한·덮어쓰기 방지·원자적 쓰기·한글 임베딩)."""

    def __init__(self, output_dir: str, font_dir: str) -> None:
        self._out = Path(output_dir)
        self._font_dir = Path(font_dir)

    def export(self, topic: str, html: str) -> str:
        """교재 HTML 을 PDF 로 저장하고 저장된 절대 경로(str)를 반환한다."""
        from weasyprint import HTML  # 지연 import: 네이티브 의존성 격리

        # 1) 권한 검증: 출력 디렉터리 보장 + 쓰기 가능 확인.
        try:
            self._out.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise PermissionDeniedError(f"출력 디렉터리 생성 실패: {self._out} ({exc})") from exc
        if not os.access(self._out, os.W_OK):
            raise PermissionDeniedError(f"출력 디렉터리에 쓰기 권한이 없음: {self._out}")

        # 2) 덮어쓰기 방지: 파일명 안전화(FR-13) 후 대상 충돌 시 즉시 중단.
        target = self._out / f"{sanitize_filename(topic)}.pdf"
        if target.exists():
            raise OverwriteError(f"이미 존재하는 교재 파일: {target}")

        # 3) 원자적 쓰기 + 한글 폰트 임베딩(@font-face 는 base_url=font_dir 로 해석).
        tmp = target.with_name(target.name + ".part")
        try:
            HTML(string=html, base_url=str(self._font_dir)).write_pdf(str(tmp))
            os.replace(tmp, target)
        finally:
            # 변환 실패로 임시 파일이 남았다면 정리(성공 시 replace 로 이미 사라짐).
            if tmp.exists():
                tmp.unlink(missing_ok=True)
        return str(target)
