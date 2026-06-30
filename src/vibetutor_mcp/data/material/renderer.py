"""Jinja2 기반 ``MaterialRenderer`` 구현체.

교재 요청(``MaterialRequest``)을 ``material.html.j2`` 템플릿으로 렌더링하여 HTML
문자열을 반환한다(SRS FR-06). 토큰 CSS(tokens/components)는 템플릿 ``{% include %}``
로 인라인되며, 한글 폰트 ``@font-face`` 경로는 익스포터의 ``base_url`` 로 해석된다.

``autoescape`` 를 유지하여 코드 예제 등 사용자 입력에 포함된 ``<``/``>``/``&`` 가
안전하게 이스케이프되도록 한다(템플릿 인젝션·깨짐 방지).
"""

from __future__ import annotations

from jinja2 import Environment, FileSystemLoader, select_autoescape

from vibetutor_mcp.domain.material.model import MaterialRequest, PracticalMaterialRequest

_TEMPLATE_NAME = "material.html.j2"
_PRACTICAL_TEMPLATE_NAME = "practical_material.html.j2"


class JinjaMaterialRenderer:
    """교재 요청을 표준 양식 HTML 문자열로 렌더링한다."""

    def __init__(self, template_dir: str) -> None:
        self._env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(enabled_extensions=("html", "xml", "j2")),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render(self, request: MaterialRequest, generated_at: str, content_hash: str) -> str:
        """렌더링된 교재 HTML 문자열을 반환한다.

        비결정적 값(``generated_at``)은 렌더러 내부에서 만들지 않고 호출자(UseCase)가
        ``Clock`` 으로 결정해 주입한다. ``content_hash`` 는 표지 콜로폰에 표기되어 재현성
        식별자로 노출된다(NFR-10).
        """
        template = self._env.get_template(_TEMPLATE_NAME)
        return template.render(
            topic=request.topic_title,
            sections=request.sections,
            generated_at=generated_at,
            content_hash=content_hash,
        )

    def render_practical(
        self, request: PracticalMaterialRequest, generated_at: str, content_hash: str
    ) -> str:
        """10단계 실전 교재 HTML 문자열을 반환한다.

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
