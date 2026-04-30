# 🍽️ 소주제 1: 주변 음식점 데이터 수집 — Claude Code 구현 가이드라인

> **목표**: Claude Code를 활용하여 카카오맵 API 기반 주변 음식점 데이터 수집 파이프라인을
> 단계별로 구현합니다. 자연어 프롬프트만으로 프로젝트 초기화부터 테스트까지 완성합니다.

---

## 📋 목차

1. [사전 준비](#1-사전-준비)
2. [프로젝트 초기화](#2-프로젝트-초기화)
3. [Step 1 — 카카오맵 API 연동 모듈 구현](#3-step-1--카카오맵-api-연동-모듈-구현)
4. [Step 2 — 데이터 정제 및 거리 점수 산출](#4-step-2--데이터-정제-및-거리-점수-산출)
5. [Step 3 — DB 스키마 설계 및 적재](#5-step-3--db-스키마-설계-및-적재)
6. [Step 4 — 스케줄러 및 자동 갱신](#6-step-4--스케줄러-및-자동-갱신)
7. [Step 5 — 테스트 및 검증](#7-step-5--테스트-및-검증)
8. [Step 6 — 대시보드 연동용 API 엔드포인트](#8-step-6--대시보드-연동용-api-엔드포인트)
9. [트러블슈팅 가이드](#9-트러블슈팅-가이드)
10. [체크리스트](#10-체크리스트)

---

## 1. 사전 준비

### 1.1 필수 환경

| 항목 | 요구사항 |
|------|---------|
| Claude Code | Claude Pro($20/월) 이상 구독 필요 |
| Node.js | 18.x 이상 (Claude Code 설치용) |
| Python | 3.10 이상 |
| OS | macOS 13+, Ubuntu 20.04+, 또는 WSL이 설치된 Windows 10+ |
| API 키 | 카카오 REST API 키 (Kakao Developers에서 발급) |

### 1.2 Claude Code 설치

```bash
# macOS / Linux
curl -fsSL https://claude.ai/install.sh | bash

# Windows (CMD)
iwr https://claude.ai/install.ps1 -useb | iex

# 설치 확인
claude --version
```

### 1.3 카카오 API 키 발급

1. [Kakao Developers](https://developers.kakao.com/) 접속 및 로그인
2. "내 애플리케이션" → "애플리케이션 추가하기"
3. 앱 이름: `lunch-optimizer` 입력
4. "앱 키" 탭에서 **REST API 키** 복사
5. "플랫폼" 탭에서 Web 플랫폼 등록 (도메인: `http://localhost`)

### 1.4 사용할 API 엔드포인트

| API | 엔드포인트 | 용도 |
|-----|-----------|------|
| 카테고리 검색 | `GET /v2/local/search/category.json` | 음식점 카테고리(FD6)로 주변 검색 |
| 키워드 검색 | `GET /v2/local/search/keyword.json` | 특정 키워드로 음식점 검색 |

**카테고리 검색 주요 파라미터:**

```
category_group_code: FD6 (음식점)
x: 경도 (longitude)
y: 위도 (latitude)
radius: 검색 반경 (미터, 최대 20000)
page: 페이지 번호 (1~45)
size: 한 페이지 결과 수 (1~15)
sort: 정렬 기준 (distance | accuracy)
```

**응답 예시:**

```json
{
  "documents": [
    {
      "id": "12345678",
      "place_name": "한솥도시락 강남점",
      "category_name": "음식점 > 한식 > 도시락",
      "phone": "02-1234-5678",
      "address_name": "서울 강남구 역삼동 123-45",
      "road_address_name": "서울 강남구 테헤란로 123",
      "x": "127.0276368",
      "y": "37.4979502",
      "distance": "150",
      "place_url": "http://place.map.kakao.com/12345678"
    }
  ],
  "meta": {
    "total_count": 45,
    "pageable_count": 45,
    "is_end": false
  }
}
```

---

## 2. 프로젝트 초기화

### 2.1 디렉토리 생성 및 Claude Code 실행

```bash
# 프로젝트 루트 생성
mkdir -p lunch-optimizer && cd lunch-optimizer

# Claude Code 실행
claude
```

### 2.2 CLAUDE.md 작성 프롬프트

Claude Code 세션에서 아래 프롬프트를 입력하여 프로젝트 설정 파일을 생성합니다.

```
프로젝트 CLAUDE.md 파일을 생성해줘. 이 프로젝트는 "직장인 점심 최적화 파이프라인"이야.
다음 정보를 포함해줘:

- 프로젝트명: lunch-optimizer
- 언어: Python 3.10+
- 주요 의존성: requests, pandas, sqlalchemy, fastapi, apscheduler, pytest
- 코딩 규칙: PEP 8, 타입 힌트 필수, docstring Google 스타일
- 빌드 명령: pip install -r requirements.txt
- 테스트 명령: pytest tests/ -v
- 린트 명령: ruff check .
- 환경변수: .env 파일 사용 (python-dotenv)
- DB: SQLite (개발), PostgreSQL (운영)
```

### 2.3 프로젝트 구조 생성 프롬프트

```
다음 디렉토리 구조로 프로젝트를 초기화해줘.
빈 __init__.py 파일과 requirements.txt도 생성해줘.

lunch-optimizer/
├── CLAUDE.md
├── .env.example
├── .gitignore
├── requirements.txt
├── pipeline/
│   ├── __init__.py
│   ├── collectors/
│   │   ├── __init__.py
│   │   └── restaurant_collector.py
│   ├── transformers/
│   │   ├── __init__.py
│   │   └── distance_scorer.py
│   ├── loaders/
│   │   ├── __init__.py
│   │   └── db_loader.py
│   └── scheduler.py
├── database/
│   ├── __init__.py
│   ├── models.py
│   └── connection.py
├── api/
│   ├── __init__.py
│   └── main.py
├── config/
│   ├── __init__.py
│   └── settings.py
└── tests/
    ├── __init__.py
    ├── test_collector.py
    ├── test_scorer.py
    └── test_loader.py

requirements.txt에는 다음 패키지를 포함해줘:
requests==2.32.3
pandas==2.2.3
sqlalchemy==2.0.36
fastapi==0.115.6
uvicorn==0.34.0
apscheduler==3.11.0
python-dotenv==1.0.1
pytest==8.3.4
httpx==0.28.1
ruff==0.8.6
```

---

## 3. Step 1 — 카카오맵 API 연동 모듈 구현

### 3.1 설정 모듈 프롬프트

```
config/settings.py 파일을 구현해줘.

.env 파일에서 다음 환경변수를 읽어오는 Settings 클래스를 만들어줘:
- KAKAO_REST_API_KEY: 카카오 REST API 키
- OFFICE_LAT: 사무실 위도 (기본값: 37.5665)
- OFFICE_LNG: 사무실 경도 (기본값: 126.9780)
- SEARCH_RADIUS: 검색 반경 미터 (기본값: 500)
- DB_URL: 데이터베이스 URL (기본값: sqlite:///lunch_optimizer.db)

python-dotenv를 사용하고, 타입 힌트를 포함해줘.
싱글턴 패턴으로 settings 인스턴스를 모듈 레벨에서 생성해줘.
```

### 3.2 음식점 수집기 프롬프트

```
pipeline/collectors/restaurant_collector.py를 구현해줘.

RestaurantCollector 클래스를 만들어줘. 다음 기능이 필요해:

1. __init__: api_key, lat, lng, radius를 받아 초기화
2. _request_kakao_api(page: int) -> dict:
   - 카카오 로컬 API의 카테고리 검색 엔드포인트 호출
   - category_group_code: "FD6" (음식점)
   - x, y, radius, page, size=15, sort="distance"
   - 헤더: Authorization: KakaoAK {api_key}
   - 요청 실패 시 최대 3회 재시도 (exponential backoff)
   - 응답을 dict로 반환

3. collect_all() -> list[dict]:
   - 전체 페이지를 순회하며 모든 음식점 수집
   - meta.is_end가 True이거나 page가 45를 초과하면 중단
   - API 호출 간 0.3초 sleep (rate limiting 방지)
   - 수집된 전체 documents 리스트 반환
   - 진행 상황 로깅 (f"Page {page}: {len(docs)}건 수집")

4. collect_by_keyword(keyword: str) -> list[dict]:
   - 키워드 검색 API로 특정 음식점 검색
   - 예: "서브웨이", "맥도날드" 등 체인점 검색용

에러 처리:
- requests.exceptions.RequestException 처리
- API 응답 status_code != 200일 때 로깅 후 빈 리스트 반환
- logging 모듈 사용 (logger = logging.getLogger(__name__))

타입 힌트와 Google 스타일 docstring을 포함해줘.
```

### 3.3 테스트 프롬프트

```
tests/test_collector.py에 RestaurantCollector의 단위 테스트를 작성해줘.

unittest.mock.patch를 사용해서 실제 API 호출 없이 테스트해야 해.

테스트 케이스:
1. test_request_kakao_api_success: 정상 응답 시 dict 반환 확인
2. test_request_kakao_api_failure: 500 에러 시 빈 dict 반환 확인
3. test_collect_all_single_page: is_end=True인 단일 페이지 응답 처리
4. test_collect_all_multi_page: 여러 페이지 순회 후 전체 결과 병합
5. test_collect_all_empty: 결과가 0건일 때 빈 리스트 반환

mock 응답 fixture를 별도 함수로 분리해줘.
```

---

## 4. Step 2 — 데이터 정제 및 거리 점수 산출

### 4.1 데이터 변환기 프롬프트

```
pipeline/transformers/distance_scorer.py를 구현해줘.

RestaurantTransformer 클래스를 만들어줘:

1. transform(raw_data: list[dict]) -> pd.DataFrame:
   카카오 API의 raw 응답 리스트를 정제된 DataFrame으로 변환.

   변환 규칙:
   - id: 그대로 유지 (str)
   - name: place_name (str)
   - category: category_name에서 "음식점 > " 이후 첫 번째 카테고리 추출
     예: "음식점 > 한식 > 도시락" → "한식"
   - sub_category: category_name에서 세 번째 카테고리 추출 (없으면 None)
     예: "음식점 > 한식 > 도시락" → "도시락"
   - address: road_address_name (없으면 address_name)
   - phone: phone (빈 문자열이면 None)
   - lat: y를 float으로 변환
   - lng: x를 float으로 변환
   - distance_m: distance를 int로 변환
   - place_url: place_url (str)
   - collected_at: 현재 시각 (datetime)

   중복 제거: id 기준 drop_duplicates
   정렬: distance_m 오름차순

2. calculate_distance_score(distance_m: int) -> int:
   거리 기반 점수 산출 (0~100)
   - 0~100m: 100점
   - 101~200m: 85점
   - 201~300m: 70점
   - 301~400m: 50점
   - 401m 이상: 30점

3. enrich_with_scores(df: pd.DataFrame) -> pd.DataFrame:
   DataFrame에 distance_score 컬럼을 추가하여 반환

4. classify_menu_type(category: str, sub_category: str | None) -> str:
   카테고리를 기반으로 메뉴 타입 분류
   - "한식" & "국수/칼국수" → "면류"
   - "한식" & "국/탕/찌개" → "국물"
   - "한식" & "죽" → "죽"
   - "일식" & "초밥/롤" → "초밥"
   - "양식" & "햄버거" → "버거"
   - 그 외 → 카테고리 그대로 반환

타입 힌트, docstring, 로깅 포함해줘.
```

### 4.2 테스트 프롬프트

```
tests/test_scorer.py에 RestaurantTransformer의 테스트를 작성해줘.

테스트 케이스:
1. test_transform_basic: 카카오 API 형식의 dict 리스트가 올바른 DataFrame으로 변환되는지
2. test_transform_category_parsing: "음식점 > 한식 > 도시락" → category="한식", sub_category="도시락"
3. test_transform_deduplication: 같은 id의 중복 데이터가 제거되는지
4. test_distance_score_boundaries: 각 거리 구간별 점수가 올바른지
5. test_classify_menu_type: 카테고리-서브카테고리 조합별 메뉴 타입 분류

mock 데이터를 pytest fixture로 정의해줘.
```

---

## 5. Step 3 — DB 스키마 설계 및 적재

### 5.1 DB 모델 프롬프트

```
database/models.py를 구현해줘. SQLAlchemy ORM 모델을 정의해줘.

Restaurant 모델:
- id: String, PK (카카오 place id)
- name: String(100), NOT NULL
- category: String(50)
- sub_category: String(50), NULLABLE
- menu_type: String(50)
- address: String(200)
- phone: String(20), NULLABLE
- lat: Float
- lng: Float
- distance_m: Integer
- distance_score: Integer
- place_url: String(300)
- indoor: Boolean, default=True
- price_avg: Integer, NULLABLE
- rating: Float, NULLABLE
- visit_count: Integer, default=0
- last_visit_date: Date, NULLABLE
- is_active: Boolean, default=True
- collected_at: DateTime
- updated_at: DateTime, onupdate=현재시각

database/connection.py:
- get_engine() 함수: settings.DB_URL로 engine 생성
- get_session() 함수: sessionmaker로 세션 팩토리 생성
- init_db() 함수: Base.metadata.create_all로 테이블 생성

SQLAlchemy 2.0 스타일(Mapped, mapped_column)을 사용해줘.
```

### 5.2 데이터 적재기 프롬프트

```
pipeline/loaders/db_loader.py를 구현해줘.

RestaurantLoader 클래스:

1. __init__(self, session): SQLAlchemy 세션을 받아 초기화

2. upsert_restaurants(df: pd.DataFrame) -> dict:
   DataFrame의 음식점 데이터를 DB에 upsert (있으면 업데이트, 없으면 삽입)
   - 반환: {"inserted": 5, "updated": 3, "skipped": 0}
   - 업데이트 시 distance_m, distance_score, collected_at만 갱신
   - name, category 등 기본 정보는 최초 삽입 시에만 저장

3. deactivate_missing(active_ids: list[str]) -> int:
   현재 API에서 조회되지 않는 음식점의 is_active를 False로 변경
   반환: 비활성화된 건수

4. get_active_restaurants() -> list[Restaurant]:
   is_active=True인 음식점 목록 조회, distance_m 오름차순 정렬

5. get_statistics() -> dict:
   통계 반환: {"total": 45, "active": 42, "categories": {"한식": 20, ...}}

트랜잭션 관리(commit/rollback), 로깅 포함해줘.
```

---

## 6. Step 4 — 스케줄러 및 자동 갱신

### 6.1 파이프라인 오케스트레이터 프롬프트

```
pipeline/scheduler.py를 구현해줘.

RestaurantPipeline 클래스를 만들어서 수집→변환→적재 전체 흐름을 관리해줘.

1. run_pipeline() -> dict:
   전체 파이프라인 실행 (한 번 실행)
   - Step 1: RestaurantCollector.collect_all()
   - Step 2: RestaurantTransformer.transform() → enrich_with_scores()
   - Step 3: RestaurantLoader.upsert_restaurants()
   - Step 4: RestaurantLoader.deactivate_missing()
   - 결과 로깅 및 반환
   - 실행 시간 측정 (time.perf_counter)
   - 에러 발생 시 전체 트랜잭션 롤백

2. start_scheduler():
   APScheduler를 사용해 매일 오전 10시에 run_pipeline 실행
   - trigger: CronTrigger(hour=10, minute=0)
   - 즉시 1회 실행 옵션 포함
   - 그레이스풀 셧다운 처리

3. main 블록:
   argparse로 --once (1회 실행) / --schedule (스케줄러 모드) 선택
   예: python -m pipeline.scheduler --once

에러 처리, 로깅 포함해줘.
```

---

## 7. Step 5 — 테스트 및 검증

### 7.1 통합 테스트 프롬프트

```
tests/test_loader.py에 DB 적재 통합 테스트를 작성해줘.

SQLite 인메모리 DB를 사용해서 실제 DB 없이 테스트해야 해.

테스트 케이스:
1. test_upsert_insert: 새로운 음식점 삽입 시 inserted 카운트 확인
2. test_upsert_update: 기존 음식점 업데이트 시 updated 카운트 확인
3. test_deactivate_missing: 사라진 음식점 비활성화 확인
4. test_get_active_restaurants: 활성 음식점만 조회되는지 확인
5. test_full_pipeline_flow: 수집→변환→적재 전체 흐름 통합 테스트
   (collector는 mock, 나머지는 실제 동작)

pytest fixture로 인메모리 DB 세션을 생성해줘.
conftest.py에 공용 fixture를 분리해줘.
```

### 7.2 테스트 실행 프롬프트

```
전체 테스트를 실행하고 결과를 확인해줘.
실패하는 테스트가 있으면 원인을 분석하고 수정해줘.
테스트 커버리지도 확인해줘.

명령어: pytest tests/ -v --tb=short
```

---

## 8. Step 6 — 대시보드 연동용 API 엔드포인트

### 8.1 FastAPI 서버 프롬프트

```
api/main.py에 FastAPI 서버를 구현해줘.

엔드포인트:

1. GET /api/restaurants
   - 활성 음식점 목록 조회
   - Query params: category(선택), min_score(선택), limit(기본 50)
   - 응답: distance_score 포함된 음식점 리스트 (JSON)

2. GET /api/restaurants/{restaurant_id}
   - 특정 음식점 상세 조회
   - 404 처리

3. GET /api/restaurants/stats
   - 전체 통계 조회 (카테고리별 개수, 평균 거리, 평균 점수 등)

4. POST /api/pipeline/run
   - 수동으로 파이프라인 1회 실행 트리거
   - 결과 반환 (inserted, updated 건수)

5. GET /api/health
   - 헬스체크 (DB 연결 상태, 최근 수집 시각)

Pydantic v2 모델로 요청/응답 스키마를 정의해줘.
CORS 미들웨어를 추가해줘 (React 대시보드 연동용).
```

### 8.2 서버 실행 확인 프롬프트

```
FastAPI 서버를 실행하고, /docs 엔드포인트에서 Swagger UI가
정상적으로 표시되는지 확인해줘.
각 엔드포인트를 curl로 테스트하는 명령어도 알려줘.

실행: uvicorn api.main:app --reload --port 8000
```

---

## 9. 트러블슈팅 가이드

### 자주 발생하는 문제와 Claude Code 해결 프롬프트

**문제 1: 카카오 API 인증 실패 (401)**

```
카카오 API 호출 시 401 Unauthorized 에러가 발생해.
Authorization 헤더 형식을 확인하고 수정해줘.
.env 파일의 API 키 형식도 검증해줘.
```

**문제 2: API Rate Limiting (429)**

```
카카오 API에서 429 Too Many Requests가 발생해.
재시도 로직에 exponential backoff을 추가하고,
요청 간 sleep 시간을 조절해줘.
일일 요청 한도(10만 건)를 넘지 않도록 카운터도 추가해줘.
```

**문제 3: 한글 인코딩 문제**

```
API 응답의 한글 데이터가 깨져서 저장돼.
응답 인코딩을 UTF-8로 명시적으로 처리하고,
DB 저장 시에도 인코딩 문제가 없는지 확인해줘.
```

**문제 4: 카테고리 파싱 에러**

```
일부 음식점의 category_name이 "음식점 > 카페"처럼
2단계만 있어서 sub_category 파싱 시 IndexError가 발생해.
방어 코드를 추가해줘.
```

**문제 5: DB 마이그레이션 필요**

```
Restaurant 모델에 새 컬럼 rating_count를 추가했는데
기존 DB와 스키마가 맞지 않아.
Alembic을 설정하고 마이그레이션 스크립트를 생성해줘.
```

---

## 10. 체크리스트

### 구현 완료 확인

```
이 프로젝트의 소주제 1 구현 상태를 점검해줘.
아래 체크리스트 항목별로 현재 상태를 확인하고,
미완료 항목이 있으면 구현해줘.
```

- [ ] `.env.example` 파일에 필요한 환경변수가 모두 정의됨
- [ ] `config/settings.py`에서 환경변수를 정상적으로 로드함
- [ ] `RestaurantCollector.collect_all()`이 카카오 API를 호출하여 전체 페이지 수집
- [ ] API 호출 실패 시 재시도 로직 동작 (최대 3회, exponential backoff)
- [ ] API Rate Limiting 방지를 위한 sleep 적용
- [ ] `RestaurantTransformer.transform()`이 raw 데이터를 정제된 DataFrame으로 변환
- [ ] 카테고리 파싱이 2단계/3단계 모두 처리됨
- [ ] 거리 점수 산출 로직이 구간별로 정확히 동작
- [ ] 메뉴 타입 분류 로직이 주요 카테고리를 커버함
- [ ] `Restaurant` ORM 모델이 정의됨 (SQLAlchemy 2.0 스타일)
- [ ] DB 테이블 자동 생성 (`init_db`)
- [ ] Upsert 로직이 삽입/업데이트를 올바르게 구분
- [ ] 사라진 음식점 비활성화 처리
- [ ] 파이프라인 오케스트레이터가 수집→변환→적재를 순차 실행
- [ ] APScheduler로 매일 자동 실행 설정
- [ ] FastAPI 엔드포인트 5개 구현 및 Swagger 확인
- [ ] CORS 미들웨어 설정
- [ ] 단위 테스트 (collector, transformer, loader) 각 5건 이상
- [ ] 전체 테스트 통과 (`pytest tests/ -v`)
- [ ] `.gitignore`에 `.env`, `__pycache__`, `*.db` 포함

---

## 부록: Claude Code 효율적 사용 팁

### 프롬프트 전략

**구체적으로 지시하기**: "음식점 수집기 만들어줘"보다 위 가이드처럼 클래스명, 메서드명, 파라미터, 반환 타입까지 명시하면 훨씬 정확한 결과를 얻을 수 있습니다.

**단계적으로 진행하기**: 한 번에 전체를 요청하지 말고, Step 1 → 테스트 → Step 2 → 테스트 순서로 진행하면 각 단계의 품질을 보장할 수 있습니다.

**think hard 활용하기**: 복잡한 설계 결정이 필요할 때는 `think hard about...` 프롬프트로 Claude Code에게 깊은 분석을 요청하세요.

### 유용한 Claude Code 명령어

| 명령어 | 용도 |
|--------|------|
| `/clear` | 컨텍스트 초기화 (토큰 절약) |
| `/cost` | 현재 세션 토큰 사용량 확인 |
| `/compact` | 대화 요약 후 컨텍스트 압축 |
| `Shift+Tab` | Plan Mode 전환 (코드 실행 없이 계획만 수립) |

### 다음 단계

소주제 1 구현이 완료되면, 같은 패턴으로 소주제 2(날씨 연동), 소주제 3(영양 분석), 소주제 4(팀 투표)를 순차적으로 구현할 수 있습니다. 각 소주제는 독립적인 collector → transformer → loader 구조를 따르며, 최종적으로 통합 추천 엔진에서 합산됩니다.

---

<div align="center">

**이 가이드를 따라 Claude Code와 함께 첫 번째 파이프라인을 완성하세요!**

</div>
