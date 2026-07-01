"""교재 생성 유스케이스.

단일 책임 원칙에 따라 '콘텐츠 해시 → 렌더링 → 포맷 변환 저장 → 메타데이터 저장'의
오케스트레이션만 담당한다. 모든 협력자는 생성자에서 인터페이스(Port)로 주입받으며
구현체는 알지 못한다.

각 단계는 ``_run_stage`` 로 감싸 실패 시 ``PipelineError(stage, reason, hint)`` 로
변환한다(SRS FR-14). 표지 작성일자는 ``Clock`` 으로 결정화하고, 콘텐츠 해시는 날짜를
제외한 입력으로 산출해 동일 입력→동일 출력을 보장한다(NFR-10).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from typing import TypeVar

from vibetutor_mcp.core.exceptions import PipelineError, VibeTutorError

from .hashing import compute_content_hash
from .model import ExportFormat, PracticalMaterialRequest, StudyMaterial
from .ports import Clock, MaterialExporter, PracticalMaterialRenderer
from .repository import MaterialRepository

_T = TypeVar("_T")


class GeneratePracticalMaterialUseCase:
    """10단계 실전 교재를 선택한 포맷(PDF/HTML/Markdown)으로 생성한다(스캐너 불필요)."""

    def __init__(
        self,
        renderer: PracticalMaterialRenderer,
        exporter: MaterialExporter,
        repository: MaterialRepository,
        clock: Clock,
    ) -> None:
        self._renderer = renderer
        self._exporter = exporter
        self._repo = repository
        self._clock = clock

    def __call__(self, request: PracticalMaterialRequest) -> StudyMaterial:
        content_hash = self._run_stage(
            "hash",
            lambda: compute_content_hash(request),
            "입력 섹션의 직렬화 가능 여부를 확인하세요.",
        )
        generated_at = self._clock.today_iso()
        # 포맷 분기는 도메인 enum 기준이라 프레임워크 의존성이 새지 않는다.
        # MARKDOWN: 파싱된 구조가 아니라 PDF 변환 전 단계의 원본 마크다운을 그대로 내보낸다.
        content = self._run_stage(
            "render",
            lambda: self._render_content(request, generated_at, content_hash),
            "템플릿/토큰(CSS) 경로와 문법을 확인하세요.",
        )
        path = self._run_stage(
            "export",
            lambda: self._exporter.export(request.topic_title, content, request.format),
            "다른 제목을 쓰거나 기존 출력 파일을 정리한 뒤 다시 시도하세요.",
        )
        material = StudyMaterial(
            topic_title=request.topic_title,
            file_path=path,
            content_hash=content_hash,
        )
        new_id = self._run_stage(
            "persist",
            lambda: self._repo.save_material(material),
            "DB 경로와 쓰기 권한을 확인하세요.",
        )
        return replace(material, id=new_id)

    def _render_content(
        self, request: PracticalMaterialRequest, generated_at: str, content_hash: str
    ) -> str:
        """포맷에 맞는 출력 컨텐츠 문자열을 만든다(MARKDOWN 은 원본 그대로 + 콜로폰)."""
        if request.format is ExportFormat.MARKDOWN:
            return self._renderer.render_markdown(
                request.source_markdown or "", generated_at, content_hash
            )
        # PDF·HTML 은 동일한 실전 교재 HTML 을 공유한다(HTML 은 변환 없이 그대로 저장).
        return self._renderer.render_practical(request, generated_at, content_hash)

    @staticmethod
    def _run_stage(stage: str, action: Callable[[], _T], hint: str) -> _T:
        """단계를 실행하고, 실패 시 단계 정보를 담은 ``PipelineError`` 로 재던진다."""
        try:
            return action()
        except PipelineError:
            raise  # 이미 구조화된 실패는 그대로 전파.
        except VibeTutorError as exc:
            raise PipelineError(stage, str(exc), hint) from exc
        except Exception as exc:
            # 모든 단계 실패를 구조화해 전달(FR-14): 어떤 예외든 stage/reason/hint 로 변환.
            raise PipelineError(stage, f"{type(exc).__name__}: {exc}", hint) from exc
