"""마크다운 원문 기반 통교재 생성 Tool 어댑터 (얇은 어댑터).

대화 전체 히스토리를 통 마크다운으로 받아 파싱한 후 Practical UseCase 로 위임한다.
``output_format`` 으로 산출물 포맷(pdf/html/markdown)을 선택한다(flat 문자열 → $ref 회피).
"""

from __future__ import annotations

from typing import Literal

from mcp.server.fastmcp import FastMCP

from vibetutor_mcp.core.exceptions import PipelineError
from vibetutor_mcp.data.material.markdown_parser import parse_markdown_to_practical_request
from vibetutor_mcp.domain.material.model import ExportFormat
from vibetutor_mcp.domain.material.usecase import GeneratePracticalMaterialUseCase


def register_markdown_tools(mcp: FastMCP, use_case: GeneratePracticalMaterialUseCase) -> None:
    """마크다운 통교재 생성 Tool 을 MCP 서버에 등록한다."""

    @mcp.tool()
    def generate_book_from_markdown(
        topic_title: str,
        markdown_content: str,
        output_format: Literal["pdf", "html", "markdown"] = "pdf",
    ) -> str:
        """[기본/권장] 사용자의 일반적인 교재 생성 요청 시 이 툴을 최우선으로 기본 사용하십시오.

        [중요: 출력 포맷 확인 필수]
        사용자가 '교재 만들어줘'라고 요청할 때 특정 포맷(PDF, HTML, Markdown)을 명시하지 않았다면,
<<<<<<< HEAD
        임의로 기본값을 선택해서 툴을 호출하지 말고 **반드시 먼저 사용자에게 어떤 포맷으로 생성할지 물어보십시오.**
=======
        임의로 기본값을 선택해서 툴을 호출하지 말고
        **반드시 먼저 사용자에게 어떤 포맷으로 생성할지 물어보십시오.**
>>>>>>> 65e07a3 (feat(material): 공식 링크 하이퍼텍스트화 및 핵심 이론 설명 챕터 추가)
        (예: "PDF, HTML, Markdown 중 어떤 형식으로 교재를 만들어 드릴까요?")
        사용자가 대답으로 포맷을 지정하면 그에 맞춰 `output_format`을 설정하여 이 툴을 호출하십시오.

        - "pdf"     : 인쇄/배포용 완성 교재(한글 폰트 임베딩, 표지·콜로폰 포함).
        - "html"    : 웹에서 바로 열어보는 교재(PDF와 동일 레이아웃, 변환 비용 없음).
        - "markdown": PDF 변환 전 단계의 원본 마크다운을 그대로 저장(빠른 텍스트·토큰 절약).

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
        fmt = ExportFormat(output_format)
        try:
            practical_req = parse_markdown_to_practical_request(topic_title, markdown_content)
            # 포맷은 경계(어댑터)에서 주입한다. source_markdown 은 파서가 이미 동봉했다.
            practical_req = practical_req.model_copy(update={"format": fmt})
            material = use_case(practical_req)
        except PipelineError as exc:
            return (
                "통교재 생성 실패\n"
                f"- 단계(stage): {exc.stage}\n"
                f"- 사유(reason): {exc.reason}\n"
                f"- 힌트(hint): {exc.hint}"
            )
        digest = material.content_hash[:12] if material.content_hash else "-"
        return (
            f"통교재 생성 완료({fmt.value}) → {material.file_path} "
            f"(id={material.id}, hash={digest})"
        )
