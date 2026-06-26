"""애플리케이션 설정 (Composition Root 주입용).

출력 디렉터리·폰트 경로·DB 경로·템플릿 경로·스캔 대상 루트를 코드에 하드코딩하지
않고 환경변수(``VIBETUTOR_*``)에서 주입한다. 경로 기본값은 패키지 위치 기준의
프로젝트 루트로 해석한다.
"""

from __future__ import annotations

from functools import cached_property
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# 프로젝트 루트: <root>/src/vibetutor_mcp/core/config.py → parents[3] == <root>
_PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """환경변수 기반 설정. 접두사 ``VIBETUTOR_`` 로 오버라이드 가능."""

    model_config = SettingsConfigDict(env_prefix="VIBETUTOR_", env_file=".env", extra="ignore")

    template_dir: str = Field(default=str(_PROJECT_ROOT / "templates"))
    font_dir: str = Field(default=str(_PROJECT_ROOT / "templates" / "fonts"))
    output_dir: str = Field(default=str(_PROJECT_ROOT / "output"))
    db_path: str = Field(default=str(_PROJECT_ROOT / "output" / "vibetutor.sqlite3"))
    project_root: str = Field(default=str(_PROJECT_ROOT))

    @cached_property
    def session_factory(self) -> sessionmaker[Session]:
        """SQLite 세션 팩토리. DB 파일 디렉터리는 호출 시 보장한다."""
        db_file = Path(self.db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)
        engine = create_engine(f"sqlite:///{db_file}", future=True)
        return sessionmaker(bind=engine, future=True)
