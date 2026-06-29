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


class PipelineError(VibeTutorError):
    """교재 생성 파이프라인 실패를 단계(stage)·사유(reason)·힌트(hint)와 함께 전달한다.

    어떤 단계(scan/hash/render/export/persist)에서, 왜 실패했고, 사용자가 무엇을
    하면 되는지를 구조화해 담는다(SRS FR-14). Presentation 어댑터는 이 정보를 그대로
    구조화 메시지로 변환해 반환한다.
    """

    def __init__(self, stage: str, reason: str, hint: str) -> None:
        self.stage = stage
        self.reason = reason
        self.hint = hint
        super().__init__(f"[{stage}] {reason} (hint: {hint})")
