# VibeTutor MCP

> **내가 실제로 쓴 코드** 위에 학습 개념을 붙여 설명하는 AI 튜터 MCP 서버.
> 로컬 코드를 분석하여 일관된 양식의 **맞춤형 실습 교재(PDF)**를 자동 생성하고 검색 가능한 개인 학습 자산으로 누적합니다.

---

## 목차

- [주요 기능](#주요-기능)
- [요구 사항](#요구-사항)
- [설치 방법](#설치-방법)
  - [로컬 설치 (uv)](#로컬-설치-uv)
  - [Docker 설치](#docker-설치)
- [Claude / MCP 클라이언트 연동](#claude--mcp-클라이언트-연동)
- [사용법](#사용법)
  - [MCP 도구 · 리소스](#mcp-도구--리소스)
  - [환경 변수](#환경-변수)
- [프로젝트 구조](#프로젝트-구조)
- [개발 가이드](#개발-가이드)
- [알려진 제약 사항](#알려진-제약-사항)
- [라이선스](#라이선스)

---

## 주요 기능

| 기능 | 설명 |
|---|---|
| **맞춤형 교재 생성** | 로컬 코드를 AST로 스캔하여 실제 코드 예제가 삽입된 PDF 교재를 생성 |
| **표준 교재 양식 강제** | 마크다운 입력을 표준 양식으로 변환하여 누가/언제 만들어도 일관된 교재 출력 |
| **한글 PDF 출력** | Pretendard 폰트 임베딩으로 한글이 깨지지 않는 인쇄용 PDF |
| **학습 자산 인덱싱** | SQLite에 교재 메타데이터를 누적, 제목 부분일치로 검색 가능 |
| **재현성 보장** | 콘텐츠 해시(SHA-256)로 동일 입력 → 동일 PDF 보장 |
| **실패 진단** | 각 처리 단계(스캔 → 렌더 → PDF → 저장) 실패 시 단계·원인·힌트 제공 |

---

## 요구 사항

| 항목 | 버전 |
|---|---|
| Python | 3.11 이상 |
| [uv](https://docs.astral.sh/uv/) | 최신 권장 |
| [Docker](https://www.docker.com/get-started/) | Windows에서 PDF 생성 시 필수 |
| WeasyPrint 네이티브 의존성 | Pango / cairo / GDK-PixBuf |

> **⚠️ Windows 로컬 환경:** WeasyPrint가 GTK 네이티브 라이브러리를 요구하므로
> PDF 변환은 **Docker**를 통해서만 가능합니다. 린트·타입검사·테스트는 로컬에서 실행 가능합니다.

---

## 설치 방법

### 로컬 설치 (uv)

```cmd
:: 1. 저장소 클론
git clone https://github.com/<your-org>/vibetutor-mcp.git
cd vibetutor-mcp

:: 2. 의존성 설치 (.venv 자동 생성)
uv sync
```

### Docker 설치

모든 네이티브 의존성이 컨테이너에 포함되어 있어 OS에 상관없이 동일한 PDF를 생성합니다.

```cmd
:: 이미지 빌드
docker build -t vibetutor-mcp .

:: 한글 PDF 1장 생성 테스트 (output\ 폴더에 저장)
docker run --rm ^
  -e VIBETUTOR_PROJECT_ROOT=/app/src ^
  -v "%cd%\output":/app/output ^
  -v "%cd%\scripts":/app/scripts ^
  vibetutor-mcp /app/.venv/bin/python scripts/smoke_generate.py
```

---

## Claude / MCP 클라이언트 연동

VibeTutor MCP는 **stdio 전송**으로 동작합니다. Claude Desktop 또는 다른 MCP 클라이언트의 설정 파일에 아래 내용을 추가하세요.

### Claude Desktop (`claude_desktop_config.json`)

```json
{
  "mcpServers": {
    "vibetutor": {
      "command": "uv",
      "args": ["run", "--directory", "/절대경로/vibetutor-mcp", "vibetutor-mcp"],
      "env": {
        "VIBETUTOR_PROJECT_ROOT": "/분석할-프로젝트-루트-경로"
      }
    }
  }
}
```

> `VIBETUTOR_PROJECT_ROOT`를 교재에 포함할 코드가 있는 프로젝트 루트로 지정하세요.
> 지정하지 않으면 vibetutor-mcp 패키지 디렉터리를 스캔합니다.

### Docker로 서버 실행 시

```json
{
  "mcpServers": {
    "vibetutor": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "-v", "C:\\분석할\\프로젝트\\루트:/workspace",
        "-v", "C:\\원하는\\출력\\경로:/app/output",
        "-e", "VIBETUTOR_PROJECT_ROOT=/workspace",
        "vibetutor-mcp"
      ]
    }
  }
}
```

---

## 사용법

### MCP 도구 · 리소스

연동 후 Claude에서 아래 도구와 리소스를 사용할 수 있습니다.

#### Tool — `generate_tutor_material_from_markdown`

마크다운 텍스트를 입력받아 한글 PDF 교재를 생성합니다. 생성된 교재는 `output/` 폴더에 저장되고 SQLite에 메타데이터가 기록됩니다.

**사용 예시:**
```
여기서 채팅한 내용을 토대로 교재로 만들어줘
```

**출력 예시:**
```
교재 생성 완료 → output/asyncio_기초.pdf (id=42, hash=a1b2c3d4)
```

---

#### Tool — `search_material`

생성된 교재를 제목 키워드로 검색합니다.

**사용 예시:**
```
search_material(query="asyncio")
```

---

#### Resource — `vibetutor://materials`

저장된 모든 교재의 메타데이터 목록(JSON 배열)을 반환합니다.

#### Resource — `vibetutor://materials/{material_id}`

특정 교재의 상세 정보(JSON)를 반환합니다. 존재하지 않으면 `{}`를 반환합니다.

---

### 환경 변수

모든 경로 설정은 환경변수로 오버라이드할 수 있습니다. `.env` 파일도 지원합니다.

| 변수 | 기본값 | 설명 |
|---|---|---|
| `VIBETUTOR_PROJECT_ROOT` | 패키지 루트 | 코드 스캔 대상 프로젝트 경로 |
| `VIBETUTOR_OUTPUT_DIR` | `<root>/output` | PDF 및 DB 저장 디렉터리 |
| `VIBETUTOR_TEMPLATE_DIR` | `<root>/templates` | Jinja2 교재 템플릿 디렉터리 |
| `VIBETUTOR_FONT_DIR` | `<root>/templates/fonts` | WeasyPrint 한글 폰트 디렉터리 |
| `VIBETUTOR_DB_PATH` | `<root>/output/vibetutor.sqlite3` | SQLite DB 파일 경로 |

---

## 프로젝트 구조

```
vibetutor-mcp/
├── src/vibetutor_mcp/
│   ├── main.py                  # FastMCP 서버 엔트리포인트 (Composition Root)
│   ├── core/
│   │   ├── config.py            # 환경변수 기반 설정 (VIBETUTOR_*)
│   │   ├── exceptions.py        # 도메인 예외 (PipelineError 등)
│   │   └── security.py          # 경로 안전 검증 · 민감 파일 차단
│   ├── domain/material/         # 순수 Python 도메인 (프레임워크 의존 없음)
│   │   ├── model.py             # StudySection · MaterialRequest · StudyMaterial
│   │   ├── ports.py             # 인터페이스 (CodeScanner / MaterialRenderer / PdfExporter)
│   │   ├── repository.py        # Repository 인터페이스
│   │   ├── usecase.py           # GenerateTutorMaterialUseCase
│   │   ├── query.py             # Search · List · Get UseCase
│   │   └── hashing.py           # SHA-256 콘텐츠 해시
│   ├── data/material/           # 인터페이스 구현체
│   │   ├── scanner.py           # LocalCodeScanner (AST 코드 추출)
│   │   ├── renderer.py          # JinjaMaterialRenderer
│   │   ├── exporter.py          # WeasyPrintExporter (한글 PDF 변환)
│   │   ├── repository_impl.py   # SqliteMaterialRepository
│   │   └── db.py                # SQLAlchemy 엔티티
│   └── presentation/
│       ├── prompts/template.py  # @mcp.prompt study_material_template
│       ├── tools/               # @mcp.tool (generate · search · markdown)
│       └── resources/           # @mcp.resource vibetutor://materials
├── templates/
│   ├── material.html.j2         # 교재 Jinja2 템플릿
│   ├── styles/                  # tokens.css · components.css
│   └── fonts/                   # Pretendard TTF/OTF (SIL OFL 1.1)
├── tests/
│   ├── test_scaffolding.py      # 아키텍처 규칙 검증
│   ├── test_pipeline.py         # 단위 · 통합 테스트
│   ├── test_e2e.py              # 전구간 E2E + 재현성
│   ├── test_search_material.py  # 검색 테스트
│   └── test_resources.py        # Resource 테스트
├── scripts/
│   ├── smoke_generate.py        # MCP 없이 PDF 1장 실생성 확인 스크립트
│   └── smoke_practical.py       # 실전 교재 생성 확인 스크립트
├── Dockerfile
└── pyproject.toml
```

**아키텍처:** Clean Architecture — `Presentation → Domain ← Data`. Domain은 프레임워크 의존 없는 순수 Python입니다.

---

## 개발 가이드

```bash
# 정적 검증 (mypy · ruff · black · pytest)
uv run mypy src
uv run ruff check
uv run black --check src tests
uv run pytest

# Docker로 한글 PDF 실물 생성 확인 (CMD)
docker build -t vibetutor-mcp . && ^
docker run --rm ^
  -e VIBETUTOR_PROJECT_ROOT=/app/src ^
  -v "%cd%\output":/app/output ^
  -v "%cd%\scripts":/app/scripts ^
  vibetutor-mcp /app/.venv/bin/python scripts/smoke_generate.py
```

**브랜치 전략:** `develop` 통합 브랜치 → `feat/<설명>` 작업 브랜치 → PR(base: develop) → squash merge.
릴리스 시 `develop → main` PR + `v0.x.y` 태그.

---

## 알려진 제약 사항

- **Windows 로컬에서 PDF 변환 불가:** VibeTutor는 PDF 생성을 위해 WeasyPrint를 사용하는데, WeasyPrint는 내부적으로 GTK(Pango/cairo/GDK-PixBuf)라는 그래픽 렌더링 엔진에 의존합니다. 이 엔진은 Linux/macOS에는 기본 포함되어 있지만 Windows에는 존재하지 않아, Windows에서 직접 실행하면 PDF가 생성되지 않습니다. Dockerfile에는 이 의존성이 미리 설치되어 있으므로, Windows 사용자는 PDF 생성 시 Docker를 사용하세요.
- **동일 제목 재생성 제한:** 같은 제목의 교재가 이미 존재하면 `OverwriteError`가 발생합니다. 교재 버전 관리(덮어쓰기 없는 누적)는 포스트-MVP 예정입니다.
- **검색 범위:** 현재 제목 LIKE 부분일치만 지원합니다. 태그·개념 전문검색(SQLite FTS5)은 차기 버전에서 지원 예정입니다.

---

## 라이선스

이 프로젝트의 소스 코드는 **MIT License**를 따릅니다. 자세한 내용은 [`LICENSE`](LICENSE)를 참고하세요.

### 서드파티 폰트

`templates/fonts/`의 Pretendard 글꼴은 **SIL Open Font License 1.1**로 배포되며, PDF 교재의 한글 임베딩 폰트로 동봉됩니다.

- Pretendard © 2021 Kil Hyung-jin — <https://github.com/orioncactus/pretendard>
- 라이선스 전문: `templates/fonts/LICENSE.txt`
