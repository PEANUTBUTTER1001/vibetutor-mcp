"""프로젝트 공통 예외.

파일시스템/검증 실패는 조용히 넘기지 않고 명시적 예외로 중단한다(생성물 안정성 1순위).
"""

from __future__ import annotations


class VibeTutorError(Exception):
    """VibeTutor 도메인 공통 베이스 예외."""


class OverwriteError(VibeTutorError):
    """이미 존재하는 PDF 를 덮어쓰려 할 때 발생(덮어쓰기 방지)."""


class PermissionDeniedError(VibeTutorError):
    """출력 경로가 없거나 쓰기 권한이 없을 때 발생(권한 검증)."""
