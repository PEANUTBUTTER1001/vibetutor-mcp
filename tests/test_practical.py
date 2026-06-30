"""10단계 실전 교재 파이프라인 검증 테스트."""

from __future__ import annotations

from pathlib import Path

from vibetutor_mcp.data.material.renderer import JinjaMaterialRenderer
from vibetutor_mcp.domain.material.model import (
    BugBox,
    ComparisonRow,
    GlossaryItem,
    PracticalMaterialRequest,
    PracticalStudySection,
    QnAItem,
)

_REPO_ROOT = Path(__file__).resolve().parents[1]
_TEMPLATE_DIR = _REPO_ROOT / "templates"


def test_practical_renderer_renders_all_submodels() -> None:
    renderer = JinjaMaterialRenderer(str(_TEMPLATE_DIR))
    req = PracticalMaterialRequest(
        topic_title="안드로이드 Compose 실전 개발",
        sections=[
            PracticalStudySection(
                heading="01장. Compose 기초",
                intro="실무 Compose 개발을 위한 첫걸음입니다.",
                objectives=["Compose 아키텍처 이해", "StateFlow 연동"],
                architecture_comparison=[
                    ComparisonRow(
                        aspect="UI 정의", legacy="XML Layout", modern="Composable Function"
                    )
                ],
                code_analysis="@Composable\ndef Greeting() { // [포인트 1]\n}",
                bug_box=[
                    BugBox(
                        symptom="Recomposition 무한 루프",
                        cause="State 상태 누락",
                        solution="remember 사용",
                    )
                ],
                pro_tip="ViewModel 내에서는 StateFlow를 exposure 하세요.",
                study_points=["Side-effect 처리 방법", "LaunchedEffect 활용"],
                qna=[
                    QnAItem(
                        question="State와 Stateless의 차이는?",
                        answer="상태 보유 여부의 차이입니다.",
                    )
                ],
                glossary=[
                    GlossaryItem(
                        term="Recomposition", definition="상태 변경 시 UI를 다시 그리는 과정"
                    )
                ],
                official_links=["https://developer.android.com"],
            )
        ],
    )

    html = renderer.render_practical(
        req, generated_at="2026-06-29", content_hash="abcdef1234567890"
    )

    assert "안드로이드 Compose 실전 개발" in html
    assert "Composable Function" in html
    assert "Recomposition 무한 루프" in html
    assert "remember 사용" in html
    assert "Recomposition" in html


def test_markdown_parser_converts_full_book() -> None:
    from vibetutor_mcp.data.material.markdown_parser import parse_markdown_to_practical_request

    md_content = """
# 01장. FastMCP 아키텍처 실전
### 1. 들어가며
이 장에서는 MCP 서버 구축에 대해 다룹니다.
### 2. 학습 목표
- FastMCP 구조 이해
- Tool 어댑터 등록
### 4. 핵심 코드 분석
```python
@mcp.tool()
def example():
    pass
```
### 5. 마주친 문제와 디버깅
[증상] 타임아웃 발생
[원인] JSON 과다 생성
[해결] 마크다운 파서 도입
"""
    req = parse_markdown_to_practical_request("FastMCP 가이드", md_content)
    assert req.topic_title == "FastMCP 가이드"
    assert len(req.sections) == 1
    assert "FastMCP 아키텍처" in req.sections[0].heading
    assert "타임아웃 발생" in req.sections[0].bug_box[0].symptom
