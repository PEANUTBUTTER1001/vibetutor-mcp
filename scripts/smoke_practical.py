"""10단계 실전 교재 생성 검증용 스모크 스크립트."""

from __future__ import annotations

from vibetutor_mcp.core.config import Settings
from vibetutor_mcp.data.material.exporter import WeasyPrintExporter
from vibetutor_mcp.data.material.renderer import JinjaMaterialRenderer
from vibetutor_mcp.data.material.repository_impl import SqliteMaterialRepository
from vibetutor_mcp.data.system_clock import SystemClock
from vibetutor_mcp.domain.material.model import (
    BugBox,
    ComparisonRow,
    GlossaryItem,
    PracticalMaterialRequest,
    PracticalStudySection,
    QnAItem,
)
from vibetutor_mcp.domain.material.usecase import GeneratePracticalMaterialUseCase


def main() -> None:
    cfg = Settings()
    use_case = GeneratePracticalMaterialUseCase(
        renderer=JinjaMaterialRenderer(cfg.template_dir),
        exporter=WeasyPrintExporter(cfg.output_dir, cfg.font_dir),
        repository=SqliteMaterialRepository(cfg.session_factory),
        clock=SystemClock(),
    )

    request = PracticalMaterialRequest(
        topic_title="실전 안드로이드 Compose 아키텍처",
        sections=[
            PracticalStudySection(
                heading="01장. Compose 상태 관리와 실무 패턴",
                intro=(
                    "선언형 UI 프레임워크인 Compose에서 상태(State) 관리의 인지적 과부하를 줄이고 "
                    "실무 패턴을 익힙니다."
                ),
                objectives=[
                    "StateFlow와 rememberSaveable의 차이점 이해",
                    "Recomposition 성능 최적화 팁 습득",
                ],
                architecture_comparison=[
                    ComparisonRow(
                        aspect="UI 상태 업데이트",
                        legacy="findViewById & setText() 수동 갱신",
                        modern="State 관찰을 통한 자동 Recomposition",
                    )
                ],
                code_analysis=(
                    "@Composable\ndef UserProfile(vm: ProfileViewModel = hiltViewModel()) {\n"
                    "    // [포인트 1] StateFlow를 Compose State로 변환\n"
                    "    val uiState by vm.uiState.collectAsStateWithLifecycle()\n"
                    "}"
                ),
                bug_box=[
                    BugBox(
                        symptom="화면 회전 시 텍스트 입력값 초기화 현상",
                        cause="remember만 사용하여 액티비티 재생성 시 상태가 유실됨",
                        solution="rememberSaveable을 사용하여 Bundle 상태로 저장하도록 수정",
                    )
                ],
                pro_tip=(
                    "ViewModel 내부의 MutableStateFlow는 private으로 두고, "
                    "외부에 공개할 때는 읽기 전용 StateFlow로 노출하세요."
                ),
                study_points=[
                    "LaunchedEffect와 rememberCoroutineScope의 올바른 사용 시점은?",
                    "DerivedStateOf를 통한 불필요한 Recomposition 방지 방법",
                ],
                qna=[
                    QnAItem(
                        question="Compose에서 Recomposition이란 무엇인가요?",
                        answer=(
                            "상태(State) 데이터가 변경되었을 때 해당 상태를 참조하는 "
                            "Composable 함수를 다시 실행하여 UI를 갱신하는 과정입니다."
                        ),
                    )
                ],
                glossary=[
                    GlossaryItem(
                        term="Recomposition",
                        definition="상태 변화에 따라 UI 트리 일부를 재구성하여 그리는 프로세스",
                    )
                ],
                official_links=["https://developer.android.com/jetpack/compose/state"],
            )
        ],
    )

    material = use_case(request)
    print("✨ 10단계 실전 교재 생성 완료!")
    print("  📁 저장 경로:", material.file_path)
    print("  🆔 DB ID    :", material.id)
    print("  🔑 콘텐츠해시:", material.content_hash)


if __name__ == "__main__":
    main()
