"""로컬 검증용 스모크 스크립트 (MVP 2단계 생성 파이프라인 E2E).

MCP 클라이언트 없이 main.py 와 동일한 방식으로 구현체를 조립해 교재 PDF 를 1장
실제 생성한다. WeasyPrint(한글 임베딩)·SQLAlchemy(메타데이터 저장)가 설치된
로컬/Docker 환경에서 실행한다.

    uv run python scripts/smoke_generate.py

성공 시 output/ 에 PDF 가 생성되고 저장 경로·DB id 가 출력된다.
이미 같은 제목의 PDF 가 있으면 덮어쓰기 방지로 OverwriteError 가 발생한다(정상 동작).
"""

from __future__ import annotations

from vibetutor_mcp.core.config import Settings
from vibetutor_mcp.data.material.exporter import WeasyPrintExporter
from vibetutor_mcp.data.material.renderer import JinjaMaterialRenderer
from vibetutor_mcp.data.material.repository_impl import SqliteMaterialRepository
from vibetutor_mcp.data.material.scanner import LocalCodeScanner
from vibetutor_mcp.data.system_clock import SystemClock
from vibetutor_mcp.domain.material.model import MaterialRequest, StudySection
from vibetutor_mcp.domain.material.usecase import GenerateTutorMaterialUseCase


def main() -> None:
    cfg = Settings()
    use_case = GenerateTutorMaterialUseCase(
        scanner=LocalCodeScanner(cfg.project_root),
        renderer=JinjaMaterialRenderer(cfg.template_dir),
        exporter=WeasyPrintExporter(cfg.output_dir, cfg.font_dir),
        repository=SqliteMaterialRepository(cfg.session_factory),
        clock=SystemClock(),
    )

    # 두 번째 섹션은 code_example 을 비워 두어, 스캐너가 이 저장소의 실제 코드를
    # 자동으로 찾아 예제로 주입하는 핵심 동작을 함께 검증한다.
    request = MaterialRequest(
        topic_title="VibeTutor 스모크 교재",
        sections=[
            StudySection(
                heading="안전한 PDF 생성 원칙",
                concept_explanation=(
                    "PDF 생성은 권한 검증과 덮어쓰기 방지를 선행한다.\n"
                    "한글은 @font-face 로 임베딩하지 않으면 □ 로 깨진다."
                ),
                code_example="HTML(string=html, base_url=font_dir).write_pdf(target)",
                code_source="SKILLS.md §6",
                exercises="출력 디렉터리가 없을 때 어떤 예외가 발생하는지 확인해보세요.",
            ),
            StudySection(
                heading="코드 출처 표기와 파일명 새니타이즈",
                concept_explanation=(
                    "sanitize_filename 으로 경로 탈출과 예약 문자를 무력화한다. "
                    "아래 예제는 스캐너가 이 저장소에서 자동으로 찾아 주입한다."
                ),
                # code_example=None → 스캐너가 자동 주입
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
