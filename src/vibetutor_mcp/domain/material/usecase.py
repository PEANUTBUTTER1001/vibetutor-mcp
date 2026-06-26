"""교재 생성 유스케이스.

단일 책임 원칙에 따라 '코드 예제 주입 → 렌더링 → PDF 변환 → 메타데이터 저장'의
오케스트레이션만 담당한다. 모든 협력자는 생성자에서 인터페이스(Port)로 주입받으며
구현체는 알지 못한다.
"""

from __future__ import annotations

from dataclasses import replace

from .model import MaterialRequest, StudyMaterial
from .ports import CodeScanner, MaterialRenderer, PdfExporter
from .repository import MaterialRepository


class GenerateTutorMaterialUseCase:
    """표준 양식 + 로컬 코드 예제를 결합한 교재 PDF 를 생성한다."""

    def __init__(
        self,
        scanner: CodeScanner,
        renderer: MaterialRenderer,
        exporter: PdfExporter,
        repository: MaterialRepository,
    ) -> None:
        self._scanner = scanner
        self._renderer = renderer
        self._exporter = exporter
        self._repo = repository

    def __call__(self, request: MaterialRequest) -> StudyMaterial:
        enriched = self._scanner.inject_examples(request)  # 로컬 코드 예제 주입
        html = self._renderer.render(enriched)  # Jinja2 렌더링
        path = self._exporter.export(request.topic_title, html)  # WeasyPrint + 덮어쓰기 방지
        material = StudyMaterial(topic_title=request.topic_title, file_path=path)
        new_id = self._repo.save_material(material)
        return replace(material, id=new_id)
