"""Jinja2 기반 ``PracticalMaterialRenderer`` 구현체.

10단계 실전 교재 요청(``PracticalMaterialRequest``)을 ``practical_material.html.j2``
템플릿으로 렌더링하여 HTML 문자열을 반환한다(PDF/HTML 공용). 토큰 CSS(tokens/components)
는 템플릿 ``{% include %}`` 로 인라인되며, 한글 폰트 ``@font-face`` 경로는 익스포터의
``base_url`` 로 해석된다.

Markdown 출력은 렌더링(파싱→재조립)을 거치지 않고 **PDF 변환 전 단계의 원본 마크다운을
그대로** 내보낸다(손실 0). 재현성 식별자만 콜로폰 푸터(HTML 주석)로 덧붙인다(NFR-10).

``autoescape`` 를 유지하여 코드 예제 등 사용자 입력에 포함된 ``<``/``>``/``&`` 가
안전하게 이스케이프되도록 한다(템플릿 인젝션·깨짐 방지).
"""

from __future__ import annotations

from jinja2 import Environment, FileSystemLoader, select_autoescape

from vibetutor_mcp.domain.material.model import PracticalMaterialRequest

_PRACTICAL_TEMPLATE_NAME = "practical_material.html.j2"


class JinjaMaterialRenderer:
    """실전 교재 요청을 출력 컨텐츠(HTML/Markdown) 문자열로 렌더링한다."""

    def __init__(self, template_dir: str) -> None:
        self._env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(enabled_extensions=("html", "xml", "j2")),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render_practical(
        self, request: PracticalMaterialRequest, generated_at: str, content_hash: str
    ) -> str:
        """10단계 실전 교재 HTML 문자열을 반환한다(PDF/HTML 공용).

        비결정적 값(``generated_at``)은 렌더러 내부에서 만들지 않고 호출자(UseCase)가
        ``Clock`` 으로 결정해 주입한다. ``content_hash`` 는 표지 콜로폰에 표기되어 재현성
        식별자로 노출된다(NFR-10).
        """
        template = self._env.get_template(_PRACTICAL_TEMPLATE_NAME)
        return template.render(
            topic=request.topic_title,
            sections=request.sections,
            generated_at=generated_at,
            content_hash=content_hash,
        )

    def render_markdown(self, source_markdown: str, generated_at: str, content_hash: str) -> str:
        """원본 마크다운을 그대로 두고 끝에 재현성 콜로폰(HTML 주석 1줄)을 덧붙인다.

        원문을 파서에 재통과시키지 않으므로 사용자가 작성한 마크다운이 열화되지 않는다.
        콜로폰은 렌더 시 보이지 않는 주석이라 본문 가독성을 해치지 않으면서 재현성
        식별자(작성일자·content_hash)를 보존한다(NFR-10).
        """
        body = source_markdown.rstrip("\n")
        colophon = (
            f"<!-- VibeTutor · 작성일자: {generated_at} · " f"content_hash: {content_hash[:16]} -->"
        )
        return f"{body}\n\n{colophon}\n"
