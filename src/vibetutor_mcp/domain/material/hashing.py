"""교재 콘텐츠 해시(재현성) 순수 함수.

동일한 입력(보강이 끝난 ``MaterialRequest``)에 대해 항상 동일한 ``content_hash`` 를
산출하여 재현성을 보장한다(SRS NFR-10). 표지 ``작성일자`` 같은 비결정적 값(렌더 시점
날짜)은 해시 입력에서 제외하므로, 같은 콘텐츠는 생성 날짜와 무관하게 같은 해시를 갖는다.

이 모듈은 순수 Python(``hashlib``/``json``)만 사용하며 프레임워크 의존성이 없다.
"""

from __future__ import annotations

import hashlib
import json

from .model import MaterialRequest

# 해시 입력으로 사용할 섹션 필드(순서·집합 고정 → 직렬화 결정성 보장).
_SECTION_FIELDS: tuple[str, ...] = (
    "heading",
    "concept_explanation",
    "code_example",
    "exercises",
    "code_source",
)


def compute_content_hash(request: MaterialRequest) -> str:
    """교재 요청을 정규(canonical) JSON 으로 직렬화해 SHA-256 16진 해시를 반환한다.

    ``ensure_ascii=False`` 로 한글을 원형 유지하고, ``sort_keys=True`` 와 고정
    구분자로 직렬화하여 같은 콘텐츠가 항상 동일한 바이트열·해시를 갖도록 한다.
    """
    payload = {
        "topic_title": request.topic_title,
        "sections": [
            {field: getattr(section, field) for field in _SECTION_FIELDS}
            for section in request.sections
        ],
    }
    blob = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()
