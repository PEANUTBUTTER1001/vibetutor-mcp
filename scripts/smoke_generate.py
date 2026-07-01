"""로컬 검증용 스모크 스크립트 (10단계 실전 교재 생성 파이프라인 E2E).

MCP 클라이언트 없이 main.py 와 동일한 방식으로 구현체를 조립해 교재를 1권 실제
생성한다. WeasyPrint(한글 임베딩)·SQLAlchemy(메타데이터 저장)가 설치된 로컬/Docker
환경에서 실행한다.

    uv run python scripts/smoke_generate.py

성공 시 output/ 에 PDF 가 생성되고 저장 경로·DB id·콘텐츠 해시가 출력된다.
이미 같은 제목의 산출물이 있으면 덮어쓰기 방지로 OverwriteError 가 발생한다(정상 동작).
"""

from __future__ import annotations

from vibetutor_mcp.core.config import Settings
from vibetutor_mcp.data.material.exporter import FormatRouterExporter
from vibetutor_mcp.data.material.renderer import JinjaMaterialRenderer
from vibetutor_mcp.data.material.repository_impl import SqliteMaterialRepository
from vibetutor_mcp.data.system_clock import SystemClock
from vibetutor_mcp.domain.material.model import (
    BugBox,
    ExportFormat,
    PracticalMaterialRequest,
    PracticalStudySection,
)
from vibetutor_mcp.domain.material.usecase import GeneratePracticalMaterialUseCase


def main() -> None:
    cfg = Settings()
    use_case = GeneratePracticalMaterialUseCase(
        renderer=JinjaMaterialRenderer(cfg.template_dir),
        exporter=FormatRouterExporter(cfg.output_dir, cfg.font_dir),
        repository=SqliteMaterialRepository(cfg.session_factory),
        clock=SystemClock(),
    )

    request = PracticalMaterialRequest(
        topic_title="VibeTutor 스모크 교재",
        format=ExportFormat.PDF,
        sections=[
            PracticalStudySection(
                heading="안전한 산출물 생성 원칙",
                intro="PDF/HTML/Markdown 생성 파이프라인이 파일 안전 3원칙을 지키는지 검증한다.",
                objectives=["권한 검증 → 덮어쓰기 방지 → 원자적 쓰기 흐름 이해"],
                concept_explanation=(
                    "산출물 생성은 권한 검증과 덮어쓰기 방지를 선행한다.\n"
                    "한글은 @font-face 로 임베딩하지 않으면 □ 로 깨진다."
                ),
                code_analysis="HTML(string=html, base_url=font_dir).write_pdf(target)",
                bug_box=[
                    BugBox(
                        symptom="한글이 □ 로 깨져서 출력됨",
                        cause="PDF 변환 시 base_url 을 폰트 디렉터리로 지정하지 않음",
                        solution="WeasyPrint 호출 시 base_url=font_dir 로 @font-face 를 해석시킨다",
                    )
                ],
                pro_tip="출력 디렉터리가 없을 때 어떤 예외가 발생하는지 먼저 확인해보세요.",
            ),
            PracticalStudySection(
                heading="파일명 새니타이즈와 콘텐츠 해시",
                intro=(
                    "sanitize_filename 으로 경로 탈출과 예약 문자를 무력화하고, "
                    "콘텐츠 해시로 재현성을 검증한다."
                ),
                concept_explanation=(
                    "sanitize_filename 은 경로 구분자·상위 참조를 제거해 경로 탈출을 막는다.\n"
                    "content_hash 는 format/source_markdown 을 제외해 "
                    "포맷 무관 콘텐츠 동일성을 보장한다."
                ),
                code_analysis="content_hash = compute_content_hash(request)",
            ),
        ],
    )

    material = use_case(request)
    print("생성 완료")
    print("  파일 :", material.file_path)
    print("  DB id:", material.id)
    print("  해시 :", material.content_hash)


if __name__ == "__main__":
    main()
