"""마크다운(Markdown) 텍스트를 PracticalMaterialRequest 도메인 모델로 파싱하는 모듈."""

from __future__ import annotations

import re

from vibetutor_mcp.domain.material.model import (
    BugBox,
    ComparisonRow,
    GlossaryItem,
    OfficialLink,
    PracticalMaterialRequest,
    PracticalStudySection,
    QnAItem,
)


def parse_markdown_to_practical_request(
    topic_title: str, markdown_content: str
) -> PracticalMaterialRequest:
    """마크다운 통텍스트를 파싱하여 PracticalMaterialRequest 구조체로 변환한다."""
    # 챕터 분할: "# 01장." 또는 "## 01장." 또는 "# 1." 형태 (### 이하의 서브섹션 제외)
    chapter_blocks = re.split(
        r"\n(?=#{1,2}\s*(?:\d+장|\d+\.|\bChapter\b))", markdown_content.strip()
    )

    if (
        not chapter_blocks
        or len(chapter_blocks) == 1
        and not re.search(r"#{1,2}\s*(?:\d+장|\d+\.|\bChapter\b)", chapter_blocks[0])
    ):
        # 챕터 구분이 명시적이지 않은 경우 통째로 단일 챕터 처리
        sections = [_parse_single_chapter(topic_title, markdown_content)]
    else:
        sections = []
        for block in chapter_blocks:
            if block.strip():
                sections.append(_parse_single_chapter(topic_title, block))

    # source_markdown 은 Markdown 출력 시 '원본 그대로 내보내기'(손실 0)에 사용된다.
    # PDF/HTML 출력에는 영향이 없으며, content_hash 산출에서도 제외된다.
    return PracticalMaterialRequest(
        topic_title=topic_title, sections=sections, source_markdown=markdown_content
    )


def _parse_single_chapter(fallback_title: str, block: str) -> PracticalStudySection:
    lines = block.strip().splitlines()
    heading = fallback_title

    # 첫 헤딩을 챕터 제목으로 채택
    if lines and lines[0].startswith("#"):
        heading = re.sub(r"^#+\s*", "", lines[0]).strip()
        lines = lines[1:]

    content_text = "\n".join(lines)

    # 10개 섹션 분할 패턴
    sub_sections = re.split(r"\n(?=###?\s*)", "\n" + content_text)

    intro = ""
    objectives: list[str] = []
    architecture_comparison: list[ComparisonRow] = []
    concept_explanation = ""
    code_analysis = ""
    bug_box: list[BugBox] = []
    pro_tip = ""
    study_points: list[str] = []
    qna: list[QnAItem] = []
    glossary: list[GlossaryItem] = []
    official_links: list[str] = []

    for sub in sub_sections:
        sub_str = sub.strip()
        if not sub_str:
            continue

        header_match = re.match(r"^#+\s*(.*)", sub_str.splitlines()[0])
        header_text = header_match.group(1).strip() if header_match else ""
        body_lines = sub_str.splitlines()[1:] if header_match else sub_str.splitlines()
        body_text = "\n".join(body_lines).strip()

        # 키워드별 매핑
        if any(k in header_text for k in ["들어가며", "Intro", "소개"]):
            intro = body_text
        elif any(k in header_text for k in ["목표", "선수", "Objective"]):
            objectives = [
                re.sub(r"^[-*•\d.]+\s*", "", item).strip()
                for item in body_lines
                if item.strip() and re.match(r"^[-*•\d]", item.strip())
            ]
        elif any(k in header_text for k in ["비교", "아키텍처", "Architecture"]):
            architecture_comparison = _parse_comparison_table(body_lines)
        elif any(k in header_text for k in ["이론 설명", "개념 설명", "사전지식", "배경지식", "핵심 이론", "개념"]):
            concept_explanation = body_text
        elif any(k in header_text for k in ["코드", "분석", "Code"]):
            code_analysis = _extract_code_block(body_text)
        elif any(k in header_text for k in ["버그", "디버깅", "Bug", "문제"]):
            bug_box = _parse_bug_box(body_lines)
        elif any(k in header_text for k in ["팁", "Tip", "실무 연동"]):
            pro_tip = body_text
        elif any(k in header_text for k in ["심화", "Study", "포인트"]):
            study_points = [
                re.sub(r"^[-*•\d.]+\s*", "", item).strip()
                for item in body_lines
                if item.strip() and re.match(r"^[-*•\d]", item.strip())
            ]
        elif any(k in header_text for k in ["Q&A", "이해도", "질문"]):
            qna = _parse_qna_table(body_lines)
        elif any(k in header_text for k in ["용어", "Glossary"]):
            glossary = _parse_glossary(body_lines)
        elif any(k in header_text for k in ["링크", "공식", "Reference", "문서", "레퍼런스", "참고자료", "참고 자료", "URL"]):
            official_links = _parse_official_links(body_lines)
        elif not intro:
            intro = body_text  # 분류되지 않은 첫 본문은 intro로 간주

    return PracticalStudySection(
        heading=heading,
        intro=intro or "본 챕터의 실무 핵심 내용입니다.",
        objectives=objectives,
        architecture_comparison=architecture_comparison,
        concept_explanation=concept_explanation,
        code_analysis=code_analysis or "// 작성된 코드가 없습니다.",
        bug_box=bug_box,
        pro_tip=pro_tip or "실무 적용 시 예외 처리에 유의하세요.",
        study_points=study_points,
        qna=qna,
        glossary=glossary,
        official_links=official_links,
    )


def _extract_code_block(text: str) -> str:
    # re.findall 로 모든 코드 블록을 추출해 합친다.
    # re.search 는 첫 번째 블록만 반환해 나머지가 유실되는 버그가 있었음.
    matches = re.findall(r"```(?:\w+)?\n?(.*?)```", text, re.DOTALL)
    if matches:
        return "\n\n".join(m.strip() for m in matches)
    return text.strip()


def _parse_official_links(lines: list[str]) -> list[OfficialLink]:
    """공식 문서 링크를 (표시 텍스트, URL) 쌍으로 추출한다.

    다음 세 가지 형식을 모두 처리한다:
    - ``[텍스트](URL)`` 마크다운 링크 → text="텍스트", url=URL
    - ``텍스트: https://...`` 혼합 형식 → text="텍스트", url=URL
    - ``https://...`` 순수 URL → text=도메인명, url=URL
    """
    from urllib.parse import urlparse

    links: list[OfficialLink] = []
    for line in lines:
        raw = re.sub(r"^[-*•\d.]+\s*", "", line).strip()
        if not raw:
            continue
        # 1순위: [텍스트](URL) 마크다운 링크
        md_match = re.search(r"\[(.+?)\]\((https?://[^)]+)\)", raw)
        if md_match:
            links.append(
                OfficialLink(text=md_match.group(1).strip(), url=md_match.group(2).strip())
            )
            continue
        # 2순위: URL 이 포함된 행(순수 URL 또는 "텍스트: URL" 혼합)
        url_match = re.search(r"(https?://\S+)", raw)
        if url_match:
            url = url_match.group(1).rstrip(".,;)")
            text_part = raw[: url_match.start()].strip().rstrip(":- \t").strip()
            if text_part:
                text = text_part
            else:
                # 순수 URL → 도메인만 표시 텍스트로 사용
                parsed = urlparse(url)
                text = parsed.netloc or url
            links.append(OfficialLink(text=text, url=url))
    return links


def _parse_comparison_table(lines: list[str]) -> list[ComparisonRow]:
    rows: list[ComparisonRow] = []
    # 1차: | 파이프 테이블 형식
    for line in lines:
        if "|" in line and not re.match(r"^\s*\|?\s*:?-+:?\s*\|", line):
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if len(parts) >= 3 and parts[0] not in ["비교 항목", "항목", "Aspect"]:
                rows.append(ComparisonRow(aspect=parts[0], legacy=parts[1], modern=parts[2]))
    if rows:
        return rows
    # 2차: "- 항목: 기존 → 현대" 불릿 형식 폴백
    for line in lines:
        raw = re.sub(r"^[-*•\d.]+\s*", "", line).strip()
        colon_match = re.match(r"^(.+?)\s*:\s*(.+?)\s*(?:→|->|vs\.?|VS)\s*(.+)$", raw)
        if colon_match:
            rows.append(
                ComparisonRow(
                    aspect=colon_match.group(1).strip(),
                    legacy=colon_match.group(2).strip(),
                    modern=colon_match.group(3).strip(),
                )
            )
    return rows


def _parse_qna_table(lines: list[str]) -> list[QnAItem]:
    items: list[QnAItem] = []
    # 1차: | 파이프 테이블 형식
    for line in lines:
        if "|" in line and not re.match(r"^\s*\|?\s*:?-+:?\s*\|", line):
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if len(parts) >= 2 and parts[0] not in ["질문", "핵심 질문", "Question"]:
                items.append(QnAItem(question=parts[0], answer=parts[1]))
    if items:
        return items
    # 2차: "Q: ... / A: ..." 형식 폴백
    curr_q, curr_a = "", ""
    for line in lines:
        raw = line.strip()
        q_match = re.match(r"^\*{0,2}Q\s*[:.：]\*{0,2}\s*(.*)", raw, re.IGNORECASE)
        a_match = re.match(r"^\*{0,2}A\s*[:.：]\*{0,2}\s*(.*)", raw, re.IGNORECASE)
        if q_match:
            if curr_q and curr_a:
                items.append(QnAItem(question=curr_q, answer=curr_a))
            curr_q = q_match.group(1).strip()
            curr_a = ""
        elif a_match and curr_q:
            curr_a = a_match.group(1).strip()
    if curr_q and curr_a:
        items.append(QnAItem(question=curr_q, answer=curr_a))
    return items


def _parse_bug_box(lines: list[str]) -> list[BugBox]:
    """Bug Box 항목을 파싱한다.

    지원 형식:
    - 다중 행: ``[증상]`` / ``[원인]`` / ``[해결]`` 각 별도 행
    - 단일 행: ``[증상] ... / [원인] ... / [해결] ...`` 한 줄에 ``/`` 로 구분
    """
    bugs: list[BugBox] = []

    # 단일 행 형식 "[증상] ... / [원인] ... / [해결] ..." 을 개별 행으로 분리한다.
    # " / [" 를 기준으로 나눠 각 토큰이 독립 행처럼 처리되도록 한다.
    expanded: list[str] = []
    for line in lines:
        stripped = line.strip()
        if "[증상]" in stripped and ("[원인]" in stripped or "[해결]" in stripped):
            parts = re.split(r"\s*/\s*(?=\[)", stripped)
            expanded.extend(parts)
        else:
            expanded.append(line)

    curr_symptom, curr_cause, curr_solution = "", "", ""
    for line in expanded:
        line_str = line.strip()
        if "증상" in line_str:
            if curr_symptom:
                bugs.append(
                    BugBox(
                        symptom=curr_symptom, cause=curr_cause or "-", solution=curr_solution or "-"
                    )
                )
                curr_symptom, curr_cause, curr_solution = "", "", ""
            curr_symptom = re.sub(r"^.*?\[?증상\]?\s*:?", "", line_str).strip()
        elif "원인" in line_str:
            curr_cause = re.sub(r"^.*?\[?원인\]?\s*:?", "", line_str).strip()
        elif "해결" in line_str:
            curr_solution = re.sub(r"^.*?\[?해결\]?\s*:?", "", line_str).strip()
    if curr_symptom:
        bugs.append(
            BugBox(symptom=curr_symptom, cause=curr_cause or "-", solution=curr_solution or "-")
        )
    return bugs


def _parse_glossary(lines: list[str]) -> list[GlossaryItem]:
    items: list[GlossaryItem] = []
    for line in lines:
        raw = re.sub(r"^[-*•\d.]+\s*", "", line.strip())  # 불릿 마커 먼저 제거
        if not raw or ":" not in raw:
            continue
        parts = raw.split(":", maxsplit=1)
        term = re.sub(r"[*`_]", "", parts[0]).strip()  # ** 볼드 마커 제거
        definition = parts[1].strip() if len(parts) > 1 else ""
        if term:
            items.append(GlossaryItem(term=term, definition=definition))
    return items
