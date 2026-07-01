"""교재 콘텐츠 해시(재현성) 순수 함수.

동일한 교재 콘텐츠(보강이 끝난 ``PracticalMaterialRequest``)에 대해 항상 동일한
``content_hash`` 를 산출하여 재현성을 보장한다(SRS NFR-10). 표지 ``작성일자`` 같은
비결정적 값과, '출력 방법' 메타데이터(``format``·``source_markdown``)는 해시 입력에서
제외한다. 따라서 같은 콘텐츠는 생성 날짜·출력 포맷과 무관하게 같은 해시(=콘텐츠 동일성
식별자)를 갖는다.

이 모듈은 순수 Python(``hashlib``/``json``)만 사용하며 프레임워크 의존성이 없다.
"""

from __future__ import annotations

import hashlib
import json

from .model import PracticalMaterialRequest

# 콘텐츠 동일성과 무관한 '출력 방법' 필드(해시에서 제외).
_NON_CONTENT_FIELDS = {"format", "source_markdown"}


def compute_content_hash(request: PracticalMaterialRequest) -> str:
    """교재 요청을 정규(canonical) JSON 으로 직렬화해 SHA-256 16진 해시를 반환한다."""
    payload = request.model_dump(exclude=_NON_CONTENT_FIELDS)
    blob = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()
