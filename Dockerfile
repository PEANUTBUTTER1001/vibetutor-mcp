# VibeTutor MCP — WeasyPrint 네이티브 의존성을 컨테이너 경계에 고정 (재현성 확보)
FROM python:3.11-slim

# WeasyPrint 런타임 네이티브 의존성 (Pango / cairo / GDK-PixBuf 계열)
# 누락 시 PDF 변환이 실패하므로 빌드 단계에서 고정한다.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libgdk-pixbuf-2.0-0 \
        libcairo2 \
        libffi8 \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# uv 설치 (의존성/락 관리)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 1) 의존성 레이어 (소스보다 먼저 복사해 캐시 활용)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# 2) 애플리케이션 소스 + 교재 템플릿/폰트
# README.md 는 pyproject 의 `readme` 필드가 참조하므로 프로젝트 빌드 전에 함께 복사한다.
COPY README.md ./
COPY src ./src
COPY templates ./templates
RUN uv sync --frozen --no-dev

# 한글 폰트는 templates/fonts/ 에 임베딩용으로 동봉되며,
# WeasyPrint 가 base_url 로 참조한다. (DESIGN.md §6)
ENV VIBETUTOR_TEMPLATE_DIR=/app/templates \
    VIBETUTOR_FONT_DIR=/app/templates/fonts \
    VIBETUTOR_OUTPUT_DIR=/app/output \
    VIBETUTOR_DB_PATH=/app/output/vibetutor.sqlite3 \
    VIBETUTOR_PROJECT_ROOT=/workspace

# MCP 서버 실행 (기본 stdio 전송)
CMD ["uv", "run", "--no-dev", "vibetutor-mcp"]
