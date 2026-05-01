---
marp: true
theme: default
paginate: true
style: |
  section {
    font-family: 'Pretendard', 'Noto Sans KR', sans-serif;
    font-size: 22px;
  }
  h1 { color: #1a73e8; border-bottom: 2px solid #1a73e8; padding-bottom: 8px; }
  h2 { color: #333; }
  code { background: #f0f4ff; padding: 2px 6px; border-radius: 4px; }
  table { font-size: 19px; }
  .cols { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
---

# 팀 점심 메뉴 추천 챗봇

**AI 기반 점심 추천 서비스 구현 프로젝트**

---

## 목차

1. 프로젝트 개요
2. 기술 스택
3. 시스템 아키텍처
4. 주요 구현 — Repository Pattern
5. DB 설계 (10개 테이블)
6. 챗봇 파이프라인
7. 성능 최적화
8. 테스트 결과
9. Git 브랜치 전략
10. 향후 개선 방향

---

## 1. 프로젝트 개요

> **"매일 점심 뭐 먹을지 고민하는 팀을 위한 AI 추천 챗봇"**

### 주요 기능
- 자연어로 점심 메뉴 추천 요청
- 날씨 · 영양 · 팀 투표 현황을 반영한 개인화 추천
- 실시간 스트리밍 응답 (SSE)
- 식사 기록 / 투표 / 거부권 등록

### 개발 범위
| Phase | 내용 |
|-------|------|
| Phase 0 | FastAPI + React + Gemini 기본 챗봇 |
| Phase 1 | SQLite DB + Repository Pattern 연동 |
| 성능 개선 | 병렬 쿼리 + TTL 캐시 |

---

## 2. 기술 스택

| 영역 | 기술 |
|------|------|
| **Backend** | FastAPI, Python 3.14, SQLAlchemy 2.0 |
| **Database** | SQLite (개발) → PostgreSQL/MySQL (운영 전환 가능) |
| **Frontend** | React 18, Vite, SSE Streaming |
| **AI** | Google Gemini 2.5 Flash Lite |
| **테스트** | pytest (28개 테스트) |
| **버전 관리** | Git Flow (main → develop → feature/*) |

---

## 3. 시스템 아키텍처

```
[React Frontend]
      │  SSE Streaming
      ▼
[FastAPI Backend]
      │
      ├─ IntentClassifier  ← 키워드 기반 의도 분류 (12종)
      │
      ├─ ContextBuilder    ← DB에서 필요한 데이터만 조회
      │       └─ ThreadPoolExecutor (병렬 쿼리)
      │
      ├─ LLMClient (Gemini / OpenAI / Claude)
      │
      └─ ToolExecutor      ← 투표·식사기록 DB 쓰기
            │
[Repository Layer]         ← DATA_SOURCE로 구현체 교체
            │
     SQLite / API Stub
```

---

## 4. 주요 구현 — Repository Pattern

### 왜 Repository Pattern?

- **현재**: SQLite 로컬 DB
- **미래**: Kakao Places API, 기상청 API

비즈니스 로직은 그대로 두고 **데이터 소스만 교체**할 수 있도록 설계

```
DATA_SOURCE=sqlite  →  SQLiteRestaurantRepo
DATA_SOURCE=api     →  KakaoRestaurantRepo (API 스텁)
```

### 구조
```
data/repositories/
  base.py                    ← 4개 추상 기반 클래스 (ABC)
  factory.py                 ← 환경변수로 구현체 선택
  sqlite/restaurant_repo.py  ← SQLite 구현
  api/restaurant_repo.py     ← API 스텁 (미래 확장)
```

---

## 5. DB 설계 — 10개 테이블

```
restaurants     : 식당 정보 (place_id, 위치, 평점)
weather_logs    : 날씨 기록 (온도, 습도, 날씨 상태)
nutrition_info  : 카테고리별 평균 영양 정보
─────────────────────────────────────────────
teams           : 팀 정보 (위치 기준)
users           : 사용자 (팀에 소속)
─────────────────────────────────────────────
meal_history    : 개인 식사 기록 (만족도 포함)
vote_sessions   : 팀 투표 세션
votes           : 개별 투표 (1인 1표 UniqueConstraint)
visit_history   : 팀 방문 이력
vetoes          : 거부권 (먹기 싫은 식당 등록)
```

**Seed Data**: 식당 20개 · 날씨 7일 · 영양 12종 · 팀원 5명 · 식사기록 25건

---

## 6. 챗봇 파이프라인

```
사용자 메시지
    │
    ▼
[Intent 분류]  ─── 12가지 의도 분류 (키워드 규칙 기반)
    │               RECOMMEND / QUERY_WEATHER / ACTION_VOTE ...
    ▼
[Context 빌드] ─── 의도에 맞는 DB 데이터만 선택 조회
    │               날씨 + 식당목록 + 투표현황 + 식사기록 (병렬)
    ▼
[LLM 호출]    ─── Gemini API (system prompt + context + history)
    │
    ▼
[SSE 스트리밍] ─── 토큰 단위로 즉시 클라이언트에 전달
```

**핵심**: 전체 응답을 기다리지 않고 **첫 토큰부터 즉시 출력** → 체감 속도 향상

---

## 7. 성능 최적화

### 시도한 방법 2가지

#### ① 병렬 Context 쿼리 (ThreadPoolExecutor)

```python
# 4개 독립 쿼리를 동시에 실행
f_weather = self._pool.submit(self._weather_repo.get_latest_cached)
f_history = self._pool.submit(self._nutrition_repo.get_meal_history, ...)
f_recs    = self._pool.submit(self._restaurant_repo.get_nearby, ...)
f_votes   = self._pool.submit(self._team_repo.get_vote_results, ...)
```

**결과**: SQLite에서는 효과 미미 (쿼리 1개 < 1ms) → **외부 API 전환 시 최대 75% 단축**

---

## 7. 성능 최적화 (계속)

#### ② TTL 캐시 (날씨 · 식당 목록)

```python
class TTLCache:
    def get(self, key): ...   # 만료 확인 후 반환
    def set(self, key, value): ...
    def invalidate(self, key=None): ...
```

| 대상 | TTL | 근거 |
|------|-----|------|
| 날씨 (`weather_logs`) | **10분** | 기상 데이터 갱신 주기 |
| 식당 목록 (`get_nearby`) | **1시간** | 위치·영업시간 변경 드묾 |
| 식사기록 / 투표 | **캐시 안 함** | 실시간 반영 필요 |

**벤치마크 결과** (Context 빌드 기준):

| | 평균 | p95 |
|--|:--:|:--:|
| 캐시 없음 (기준) | 4.08ms | 5.03ms |
| 캐시 적용 (웜) | **2.81ms** | **3.35ms** |
| 개선율 | **-31%** | **-33%** |

---

## 8. 테스트 결과

```
tests/
  test_chatbot_core.py   — 챗봇 핵심 로직 (7개)
  test_repositories.py   — Repository + 캐시 동작 (10개)
  test_seed.py           — Seed 데이터 정합성 (5개)
  test_base_repos.py     — ABC 추상 클래스 검증 (1개)
─────────────────────────────────────────────
합계: 28개 테스트 / 28개 통과
```

**캐시 테스트 포함 항목:**
- 두 번째 호출 시 캐시 히트 확인
- `invalidate()` 후 DB 재조회 확인
- `category` 파라미터별 캐시 키 분리 확인

---

## 9. Git 브랜치 전략 (Git Flow)

```
main ──────────────────────────── (안정 배포 버전)
  └─ develop ────────────────────  (통합 브랜치)
         └─ feature/sqlite-seed-db (기능 개발 → develop 머지 완료)
```

### 커밋 컨벤션
```
feat:  새 기능
fix:   버그 수정
perf:  성능 개선
test:  테스트 추가/수정
```

**GitHub**: `bell-0925/food_-recomendation-ChatBot`

---

## 10. 향후 개선 방향

| 우선순위 | 항목 | 기대 효과 |
|:--------:|------|---------|
| ★★★ | 실제 날씨 API 연동 (OpenWeatherMap) | 실시간 날씨 반영 |
| ★★★ | Kakao Places API 연동 | 실제 주변 식당 검색 |
| ★★☆ | Intent 분류기 LLM 기반으로 교체 | 자연어 이해 정확도 향상 |
| ★★☆ | 개인화 기능 (Phase 3) | 취향 기반 추천 |
| ★☆☆ | Docker 배포 (Phase 4) | 운영 환경 구축 |

> API 연동 시 **병렬 쿼리 + TTL 캐시**가 실질적 효과를 냄

---

# 감사합니다

**프로젝트 구조 요약**

```
mini_project_13/
├─ api/          FastAPI 엔드포인트
├─ chatbot/      Intent · Context · LLM · Tools
├─ data/
│   ├─ cache.py              TTL 캐시 유틸
│   ├─ repositories/         Repository Pattern
│   └─ seed/                 가상 데이터 생성
├─ ui/react-chat/            React 프론트엔드
└─ tests/        28개 테스트
```
