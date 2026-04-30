# Mini 프로젝트 기능 명세서 — 종합 인덱스

본 문서 시리즈는 **Mini**(구 Phase 11) 점심 최적화 시스템의 모든 기능을 8개 영역으로 분할 기술한 기술 명세서입니다. 각 문서는 독립적으로 읽을 수 있도록 구성되어 있으며, 상호 참조는 본 인덱스를 통해 연결됩니다.

---

## 문서 목록

| # | 제목 | 핵심 내용 |
|---|---|---|
| **01** | **시스템 개요 및 아키텍처** | 토폴로지, 데이터 흐름, 기술 스택 매트릭스, 코드 메트릭 |
| **02** | **대시보드 7페이지 기능 명세** | Dashboard / Discover / Weather / Nutrition / Vote / Concierge / Insights |
| **03** | **백엔드 데이터 파이프라인 및 추천 엔진** | 4 Collectors (Kakao/KMA/식약처/AirKorea), 4축 스코어링 |
| **04** | **API 명세 (lunch-api 45 + nlp-api 18)** | 모든 엔드포인트 시그니처 + 호출 흐름 다이어그램 |
| **05** | **NLP MVP 모듈 (Phase 5)** | A1 Sentiment / B1 Menu Norm / D3 RAG / D5 NLG |
| **06** | **NLP Research + Tool Calling (Phase 6/7)** | A2 ABSA / B2 NER / E1 CF + 8 Tool Functions |
| **07** | **데이터 모델 명세** | 13개 SQLAlchemy 테이블 + 인덱스 + 라이프사이클 |
| **08** | **인프라 및 배포** | Docker Compose / Dockerfile / CI-CD / 운영 절차 |

---

## 빠른 진입 가이드

### 처음 보는 사람
**01 → 02 → 03 → 04** 순서 권장. 시스템 개요와 사용자 기능, 백엔드 처리, API 호출 패턴까지 일괄 이해 가능.

### 백엔드 개발자
**01 → 03 → 04 → 07** — 데이터 파이프라인 / API / DB 모델 중심.

### 프론트엔드 개발자
**01 → 02 → 04** — 7개 페이지 + 호출하는 API 시그니처.

### NLP / ML 엔지니어
**01 → 05 → 06 → 07** — MVP 모듈, Research 모델, 데이터 스키마.

### DevOps / 인프라 담당
**01 → 08 → 03 (스케줄러 부분)** — 배포, CI/CD, 컨테이너.

---

## 핵심 사실 요약

### 시스템
- **컨테이너 4개**: `mini-web` (3000), `mini-lunch-api` (8000), `mini-nlp-api` (8001), `mini-ollama` (11434)
- **이미지 빌드 합계**: ~4.3GB (lunch 603MB + nlp 3.43GB + web 282MB)
- **영속 볼륨**: 5개 (mini-db, mini-logs, mini-chroma, mini-hf, mini-ollama-models)

### 코드
- **소스 파일**: ~238개 / **총 라인**: ~26,500
- **API 엔드포인트**: lunch 45 + nlp 18 = **63개**
- **DB 테이블**: 13개 (코어 11 + 보조 2)
- **자동화 테스트**: ~88 pytest + Tool Calling 23 + web CI

### 기술 스택 (대표)
- Frontend: Next.js 16.2.1, React 19.2.4, Tailwind v4, TanStack Query 5.96, Recharts 3.8, Leaflet 1.9
- Backend: FastAPI 0.115, SQLAlchemy 2.0, APScheduler 3.11, Pandas 2.2
- NLP: transformers 4.44, chromadb 0.5, sentence-transformers 3.0, ollama 0.3, KcELECTRA / ko-sroberta / KoELECTRA / qwen2.5:7b
- Infra: Docker Compose v5.1.2, GitHub Actions, ruff, pre-commit, detect-secrets

### 핵심 알고리즘
- **4축 종합 스코어**: distance(0.3) + weather(0.2) + nutrition(0.2) + team(0.3)
- **메뉴 정규화 캐스케이드**: 규칙 → Levenshtein → Sentence-BERT
- **RAG**: ChromaDB 3-collection (meal_history / nutrition_info / restaurants) + Ollama qwen2.5:7b
- **환각 방지 3중**: RAG context 강제 / prompt 가드 / output validation

---

## 문서 작성 메타데이터

- **작성일**: 2026-04-27
- **프로젝트 단계**: Phase 7 완료 (~96% 진척)
- **작성 도구**: Markdown 원본 + npx md-to-pdf (puppeteer/headless Chrome)
- **PDF 폰트**: Apple SD Gothic Neo / Noto Sans CJK KR (한글)
- **PDF 사양**: A4, 여백 18/14mm, 배경 인쇄 ON

---

## 라이선스 / 출처

본 명세서는 Mini 프로젝트 내부 문서이며, 외부 공유 시에는 다음을 함께 표기 권장:
- 코드 라이선스 (해당 시)
- 외부 API 라이선스 (Kakao, 공공데이터 등 — 「08. 인프라」 §11 참고)
- HuggingFace 모델 라이선스

---

> 모든 문서의 PDF 버전은 `pdf/docs/specs/` 디렉터리에 동일 파일명으로 보관됩니다.
