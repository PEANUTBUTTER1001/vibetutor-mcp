# vibetutor-mcp

개인 AI튜터 MCP: 코딩 컨텍스트와 로컬 파일을 기반으로 구조화된 실습 교재를 자동 생성

## 아키텍처

Clean Architecture (Presentation → Domain ← Data). 자세한 규칙은 `AGENTS.md`,
코드 패턴은 `SKILLS.md`, 교재 디자인은 `DESIGN.md` 를 참조한다.

```
src/vibetutor_mcp/
  presentation/   @mcp.prompt / @mcp.tool (얇은 어댑터)
  domain/         model / repository / ports / usecase (순수 Python)
  data/           SQLAlchemy / Jinja2 / WeasyPrint / 파일시스템 구현체
  core/           config, exceptions
  main.py         FastMCP 엔트리포인트 (Composition Root)
templates/        교재 Jinja2 템플릿 + styles + fonts (Pretendard 임베딩)
tests/            pytest
```

## 개발 (uv)

```bash
uv sync                       # 의존성 설치 (.venv 생성)
uv run mypy src               # 타입 검사 (strict)
uv run ruff check             # 린트
uv run black --check src tests
uv run pytest                 # 테스트
```

## 실행

```bash
uv run vibetutor-mcp          # MCP 서버 (stdio)
```

## Docker

WeasyPrint 네이티브 의존성(Pango/cairo/GDK-PixBuf)을 컨테이너 경계에 고정한다.

```bash
docker build -t vibetutor-mcp .
```

## 라이선스

이 프로젝트의 소스 코드는 MIT License 를 따른다. (루트 `LICENSE` 참고)

### 서드파티 폰트

`templates/fonts/` 의 Pretendard 글꼴은 SIL Open Font License 1.1 로 배포되며,
PDF 교재의 한글 임베딩 폰트로 동봉된다.

- Pretendard © 2021 Kil Hyung-jin — https://github.com/orioncactus/pretendard
- Reserved Font Name: "Pretendard"
- 라이선스 전문: `templates/fonts/LICENSE.txt`
