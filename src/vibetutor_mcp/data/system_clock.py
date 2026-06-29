"""시스템 시계 ``Clock`` 구현체.

실제 벽시계(로컬 날짜)를 제공한다. 비결정적 시간 의존성을 이 ``data`` 레이어 안에
격리하여, UseCase 는 ``Clock`` Port 에만 의존하고 테스트는 고정 시계를 주입할 수
있게 한다(재현성·테스트 용이성, NFR-10).
"""

from __future__ import annotations

from datetime import date


class SystemClock:
    """오늘 날짜를 ``YYYY-MM-DD`` 문자열로 제공하는 시스템 시계."""

    def today_iso(self) -> str:
        return date.today().isoformat()
