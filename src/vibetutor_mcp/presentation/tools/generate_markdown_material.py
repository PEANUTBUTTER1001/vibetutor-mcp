"""마크다운 원문 기반 통교재 생성 Tool 어댑터 (얇은 어댑터).

대화 전체 히스토리를 통 마크다운으로 받아 파싱한 후 Practical UseCase 로 위임한다.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from vibetutor_mcp.core.exceptions import PipelineError
from vibetutor_mcp.data.material.markdown_parser import parse_markdown_to_practical_request
from vibetutor_mcp.domain.material.usecase import GeneratePracticalMaterialUseCase


def register_markdown_tools(mcp: FastMCP, use_case: GeneratePracticalMaterialUseCase) -> None:
    """마크다운 통교재 생성 Tool 을 MCP 서버에 등록한다."""

    @mcp.tool()
    def generate_book_from_markdown(topic_title: str, markdown_content: str) -> str:
        """[기본/권장] 사용자의 일반적인 교재 생성 요청 시 이 툴을 최우선으로 기본 사용하십시오.

        사용자가 특정 포맷 언급 없이 '교재를 만들어달라'고 요청하면, 지금까지의
        대화 맥락을 기반으로 아래의 10단계 마크다운 규격을 엄격히 준수한 마크다운 본문을
        작성하여 이 툴을 호출하십시오.

        [마크다운 작성 규칙]
        - 챕터 시작: # 01장. 챕터 제목
        - 서브 섹션 필수 구성:
          ### 1. 들어가며
          ### 2. 학습 목표
          ### 3. 핵심 이론 비교표
          ### 4. 핵심 코드 분석
          ### 5. 마주친 문제와 디버깅
          ### 6. 실무 연동 팁
          ### 7. 심화 학습
          ### 8. Q&A 표
          ### 9. 용어 사전
          ### 10. 공식 링크
        """
        try:
            practical_req = parse_markdown_to_practical_request(topic_title, markdown_content)
            material = use_case(practical_req)
        except PipelineError as exc:
            return (
                "통교재 생성 실패\n"
                f"- 단계(stage): {exc.stage}\n"
                f"- 사유(reason): {exc.reason}\n"
                f"- 힌트(hint): {exc.hint}"
            )
        digest = material.content_hash[:12] if material.content_hash else "-"
        return f"통교재 생성 완료 → {material.file_path} (id={material.id}, hash={digest})"
