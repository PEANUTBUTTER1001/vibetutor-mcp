"""로컬 코드 스캐너 ``CodeScanner`` 구현체 (스캐폴딩 단계: 스텁).

지정된 프로젝트 루트를 스캔해 각 섹션에 실제 코드 예제를 주입한다. 대용량 프로젝트
스캔 성능과 경로 인코딩(Windows/Unix) 처리는 MVP 2단계에서 다룬다.
"""

from __future__ import annotations

from pathlib import Path

from vibetutor_mcp.domain.material.model import MaterialRequest


class LocalCodeScanner:
    """프로젝트 루트의 코드를 스캔해 교재 요청에 예제를 보강한다."""

    def __init__(self, project_root: str) -> None:
        self._root = Path(project_root)

    def inject_examples(self, request: MaterialRequest) -> MaterialRequest:
        raise NotImplementedError("MVP 2단계에서 구현: 로컬 코드 스캔 후 예제 주입")
