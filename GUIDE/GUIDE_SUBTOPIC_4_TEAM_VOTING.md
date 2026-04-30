# 🗳️ 소주제 4: 팀 투표 & 히스토리 관리 — Claude Code 구현 가이드라인

> **목표**: 팀원 간 점심 투표 시스템과 방문 히스토리 관리를 구현하여,
> 팀 합의 시간을 단축하고 중복 방문을 방지하며, 최종 통합 추천 엔진을 완성합니다.

---

## 📋 목차

1. [사전 준비](#1-사전-준비)
2. [프로젝트 구조 확장](#2-프로젝트-구조-확장)
3. [Step 1 — 사용자 및 팀 모델 설계](#3-step-1--사용자-및-팀-모델-설계)
4. [Step 2 — 투표 시스템 구현](#4-step-2--투표-시스템-구현)
5. [Step 3 — 방문 히스토리 관리](#5-step-3--방문-히스토리-관리)
6. [Step 4 — 팀 선호도 학습 엔진](#6-step-4--팀-선호도-학습-엔진)
7. [Step 5 — 팀 점수 산출 및 통합 추천 엔진](#7-step-5--팀-점수-산출-및-통합-추천-엔진)
8. [Step 6 — WebSocket 실시간 투표 (선택)](#8-step-6--websocket-실시간-투표-선택)
9. [Step 7 — 테스트 및 검증](#9-step-7--테스트-및-검증)
10. [Step 8 — API 엔드포인트 확장](#10-step-8--api-엔드포인트-확장)
11. [Step 9 — 통합 파이프라인 최종 조립](#11-step-9--통합-파이프라인-최종-조립)
12. [트러블슈팅 가이드](#12-트러블슈팅-가이드)
13. [체크리스트](#13-체크리스트)

---

## 1. 사전 준비

### 1.1 소주제 4의 특성

소주제 1~3은 외부 API에서 데이터를 수집하는 구조였지만,
소주제 4는 **내부 사용자 행동 데이터**를 수집·분석하는 구조입니다.

| 구분 | 소주제 1~3 | 소주제 4 |
|------|----------|---------|
| 데이터 소스 | 외부 공공/민간 API | 내부 DB (사용자 입력) |
| 갱신 주기 | 시간/일 단위 스케줄링 | 실시간 이벤트 기반 |
| 핵심 로직 | 수집 → 변환 → 점수 산출 | 투표 → 집계 → 선호도 학습 |
| 난이도 | API 연동 | 동시성 제어, 상태 관리 |

### 1.2 핵심 비즈니스 규칙

투표 시스템의 비즈니스 규칙을 먼저 정의합니다:

| 규칙 | 설명 |
|------|------|
| 투표 시간 | 매일 오전 10:00 ~ 11:30 (점심 전까지) |
| 투표 방식 | 팀원 1인당 1표 (변경 가능, 마감 전까지) |
| 최소 참여 | 팀원의 50% 이상 투표 시 결과 확정 가능 |
| 동점 처리 | 최근 방문일이 더 오래된 음식점 우선 |
| 중복 방지 | 최근 3영업일 내 방문한 음식점은 추천 하향 |
| 거부권 | 특정 음식점 "오늘은 안 돼요" 기능 |

### 1.3 추가 의존성

```
requirements.txt에 추가:
- websockets==13.1 (실시간 투표용, 선택)
- python-dateutil==2.9.0 (영업일 계산)
```

---

## 2. 프로젝트 구조 확장

### Claude Code 프롬프트

```
기존 프로젝트 구조에 소주제 4 관련 파일들을 추가해줘.

추가할 파일:
- pipeline/collectors/vote_collector.py          # 투표 수집 및 관리
- pipeline/transformers/team_scorer.py            # 팀 선호도 분석 및 점수 산출
- pipeline/transformers/visit_tracker.py          # 방문 히스토리 관리
- engine/recommender.py                           # 통합 추천 엔진 (최종 조립)
- database/models.py에 User, Team, Vote, VisitHistory 모델 추가
- tests/test_vote_collector.py
- tests/test_team_scorer.py
- tests/test_visit_tracker.py
- tests/test_recommender.py                       # 통합 추천 엔진 테스트
```

---

## 3. Step 1 — 사용자 및 팀 모델 설계

### Claude Code 프롬프트

```
database/models.py에 소주제 4 관련 모델들을 추가해줘.
SQLAlchemy 2.0 스타일(Mapped, mapped_column)을 사용해줘.

Team 모델:
- id: String(50), PK (예: "dev-team-1")
- name: String(100), NOT NULL (예: "개발1팀")
- created_at: DateTime

User 모델:
- id: String(50), PK (예: "user-kim")
- name: String(50), NOT NULL (예: "김민수")
- team_id: String(50), FK → teams.id
- avatar_emoji: String(10), default="🧑‍💻"
- dislike_categories: String(200), NULLABLE
  (쉼표 구분, 예: "중식,양식")
- allergy_info: String(200), NULLABLE
  (예: "갑각류,땅콩")
- is_active: Boolean, default=True
- created_at: DateTime

Vote 모델:
- id: Integer, PK, autoincrement
- vote_date: Date, NOT NULL, index=True
- user_id: String(50), FK → users.id
- restaurant_id: String, FK → restaurants.id
- created_at: DateTime
- updated_at: DateTime, onupdate=now
- UniqueConstraint: (vote_date, user_id)
  → 하루에 1인 1표, 변경 시 update

VoteSession 모델:
- id: Integer, PK, autoincrement
- vote_date: Date, NOT NULL, UNIQUE
- team_id: String(50), FK → teams.id
- status: String(20), default="open"
  (open / closed / finalized)
- open_at: DateTime
- close_at: DateTime, NULLABLE
- winner_restaurant_id: String, NULLABLE, FK → restaurants.id
- total_votes: Integer, default=0
- created_at: DateTime

VisitHistory 모델:
- id: Integer, PK, autoincrement
- visit_date: Date, NOT NULL, index=True
- team_id: String(50), FK → teams.id
- restaurant_id: String, FK → restaurants.id
- participant_count: Integer
- avg_satisfaction: Float, NULLABLE
- created_at: DateTime

Veto 모델 (거부권):
- id: Integer, PK, autoincrement
- veto_date: Date, NOT NULL
- user_id: String(50), FK → users.id
- restaurant_id: String, FK → restaurants.id
- reason: String(200), NULLABLE
- UniqueConstraint: (veto_date, user_id, restaurant_id)

모든 모델에 relationship 설정 포함.
Team ↔ User (1:N), User ↔ Vote (1:N),
VoteSession ↔ Vote (1:N via vote_date) 관계 설정해줘.
```

---

## 4. Step 2 — 투표 시스템 구현

### Claude Code 프롬프트

```
pipeline/collectors/vote_collector.py를 구현해줘.

VoteManager 클래스:

1. open_session(team_id: str, vote_date: date = None) -> VoteSession:
   투표 세션을 개시. 이미 해당 날짜에 세션이 있으면 기존 세션 반환.
   vote_date가 None이면 오늘 날짜 사용.
   status를 "open"으로 설정.

2. cast_vote(user_id: str, restaurant_id: str,
             vote_date: date = None) -> dict:
   투표 행사.
   반환: {"status": "created" | "updated", "vote": Vote}

   규칙:
   - 해당 날짜의 세션이 "open" 상태인지 확인 → 아니면 에러
   - 이미 투표했으면 restaurant_id를 업데이트 (변경 허용)
   - 거부권(Veto)이 걸린 음식점에 투표하면 경고 메시지 반환
     (투표 자체는 허용하되 경고)

3. cast_veto(user_id: str, restaurant_id: str,
             reason: str = None, veto_date: date = None) -> Veto:
   특정 음식점에 거부권 행사.
   "오늘은 여기 안 가고 싶어요" 기능.

4. get_current_status(team_id: str, vote_date: date = None) -> dict:
   현재 투표 현황 조회.
   반환:
   {
     "vote_date": "2026-04-05",
     "status": "open",
     "team_members": 5,
     "voted_count": 3,
     "participation_rate": 60.0,
     "votes": [
       {"user_name": "김민수", "avatar": "🧑‍💻",
        "restaurant_name": "한솥도시락", "voted_at": "10:15"},
       {"user_name": "이수진", "avatar": "👩‍💼",
        "restaurant_name": "한솥도시락", "voted_at": "10:22"},
       {"user_name": "박준혁", "avatar": "👨‍🔬",
        "restaurant_name": "서브웨이", "voted_at": "10:30"},
     ],
     "not_voted": ["정하은", "최동원"],
     "vetoed": [
       {"restaurant_name": "맥도날드", "veto_by": "이수진", "reason": "어제 먹었어요"}
     ],
     "tally": [
       {"restaurant_id": "123", "restaurant_name": "한솥도시락", "votes": 2},
       {"restaurant_id": "456", "restaurant_name": "서브웨이", "votes": 1},
     ]
   }

5. close_session(team_id: str, vote_date: date = None) -> dict:
   투표 마감 및 결과 확정.

   확정 로직:
   a. 참여율 50% 미만이면 → 경고 + 현재 결과로 강제 확정 또는 재투표 요청
   b. 1위가 단독이면 → 해당 음식점으로 확정
   c. 동점이면 → 최근 방문일이 더 오래된 음식점 선택
   d. 그래도 동점이면 → 랜덤 선택

   반환:
   {
     "winner": {"restaurant_id": "123", "restaurant_name": "한솥도시락",
                "votes": 3, "tiebreak_reason": None},
     "total_votes": 4,
     "participation_rate": 80.0,
     "finalized_at": "2026-04-05T11:30:00"
   }

   확정 후 VoteSession.status를 "finalized"로 변경.
   winner_restaurant_id 저장.

6. get_vote_history(team_id: str, days: int = 30) -> list[dict]:
   최근 N일간의 투표 결과 이력.

에러 처리, 로깅, 타입 힌트, docstring 포함해줘.
```

---

## 5. Step 3 — 방문 히스토리 관리

### Claude Code 프롬프트

```
pipeline/transformers/visit_tracker.py를 구현해줘.

VisitTracker 클래스:

1. record_visit(team_id: str, restaurant_id: str,
                visit_date: date, participant_count: int,
                satisfaction_scores: list[int] = None) -> VisitHistory:
   팀의 음식점 방문 기록 저장.
   satisfaction_scores가 있으면 평균 계산하여 avg_satisfaction에 저장.

2. get_recent_visits(team_id: str, days: int = 10) -> list[dict]:
   최근 N일간(영업일 기준) 방문 기록 조회.
   반환: [{"date": "2026-04-04", "restaurant_name": "맥도날드",
           "participants": 4, "satisfaction": 3.8}, ...]

3. get_visit_frequency(team_id: str, days: int = 30) -> dict:
   음식점별 방문 빈도 분석.
   반환:
   {
     "한솥도시락": {"count": 5, "last_visit": "2026-04-03",
                    "avg_satisfaction": 4.1, "days_since": 2},
     "서브웨이": {"count": 3, "last_visit": "2026-03-28",
                  "avg_satisfaction": 3.7, "days_since": 8},
     ...
   }

4. get_overvisited(team_id: str, threshold: int = 4,
                   days: int = 20) -> list[str]:
   최근 N영업일 내 threshold회 이상 방문한 음식점 ID 리스트.
   "또 여기야?" 방지용.

5. get_days_since_last_visit(team_id: str,
                              restaurant_id: str) -> int | None:
   특정 음식점의 마지막 방문 이후 경과 영업일 수.
   방문 기록이 없으면 None.

6. calculate_freshness_score(team_id: str,
                              restaurant_id: str) -> int:
   방문 신선도 점수 (0~100).
   - 방문 기록 없음 → 100 (완전 새로운 곳)
   - 10영업일 이상 경과 → 90
   - 5~9영업일 경과 → 70
   - 3~4영업일 경과 → 40
   - 1~2영업일 경과 → 10
   - 오늘 방문 → 0

7. get_never_visited(team_id: str,
                     all_restaurant_ids: list[str]) -> list[str]:
   한 번도 방문하지 않은 음식점 ID 리스트.
   "새로운 곳 도전" 추천용.

python-dateutil의 영업일 계산 함수 사용.
공휴일은 일단 제외하고 월~금만 영업일로 계산 (Phase 2에서 공휴일 추가 가능).

타입 힌트, docstring, 로깅 포함해줘.
```

---

## 6. Step 4 — 팀 선호도 학습 엔진

### Claude Code 프롬프트

```
pipeline/transformers/team_scorer.py를 구현해줘.

TeamPreferenceAnalyzer 클래스:

1. analyze_team_preference(team_id: str, days: int = 60) -> dict:
   팀의 장기 선호도 분석.

   반환:
   {
     "favorite_categories": [
       {"category": "한식", "visit_pct": 45.0, "avg_satisfaction": 4.2},
       {"category": "일식", "visit_pct": 20.0, "avg_satisfaction": 4.5},
       ...
     ],
     "favorite_restaurants": [
       {"name": "한솥도시락", "visits": 8, "avg_satisfaction": 4.1},
       ...
     ],
     "avoided_restaurants": [
       {"name": "맥도날드", "last_veto_count": 3, "avg_satisfaction": 2.8},
     ],
     "preferred_price_range": {"min": 7000, "max": 10000, "avg": 8500},
     "preferred_distance": {"max": 350, "avg": 220},
     "variety_score": 72,  # 0~100, 높을수록 다양하게 먹음
   }

2. calculate_variety_score(team_id: str, days: int = 20) -> int:
   다양성 점수 산출 (0~100).
   최근 N영업일 중 고유 음식점 수 / 총 방문 수 × 100.
   예: 15일 중 12곳 방문 → 80점, 15일 중 5곳만 반복 → 33점.

3. predict_team_preference(team_id: str,
                            restaurant_id: str) -> int:
   특정 음식점에 대한 팀 선호 예측 점수 (0~100).

   계산 요소:
   - 해당 카테고리의 과거 만족도 (가중 40%)
   - 과거 방문 만족도 (있으면 가중 30%, 없으면 카테고리로 대체)
   - 가격대 선호 부합도 (가중 15%)
   - 거리 선호 부합도 (가중 15%)

4. get_team_mood(team_id: str) -> str:
   최근 투표 패턴과 만족도로 팀의 식사 '분위기' 판단.
   - "모험적": variety_score > 70 + 최근 새 음식점 방문 많음
   - "보수적": variety_score < 40 + 같은 곳 반복 방문
   - "불만족": 최근 평균 만족도 < 3.0
   - "만족": 최근 평균 만족도 >= 4.0
   - "보통": 그 외

타입 힌트, docstring, 로깅 포함해줘.
```

---

## 7. Step 5 — 팀 점수 산출 및 통합 추천 엔진

### 7.1 팀 점수 산출 프롬프트

```
pipeline/transformers/team_scorer.py에
TeamRecommendScorer 클래스를 추가해줘.

TeamRecommendScorer:

1. calculate_team_score(team_id: str, restaurant_id: str,
                        vote_status: dict) -> int:
   특정 음식점의 팀 점수 산출 (0~100).

   구성 요소:
   a. 투표 점수 (가중 50%):
      - 현재 투표 수 기반: votes=0 → 0, 1표 → 40, 2표 → 65, 3표+ → 85
      - 거부권 있으면: -30

   b. 방문 신선도 (가중 25%):
      - VisitTracker.calculate_freshness_score() 사용

   c. 팀 선호 예측 (가중 25%):
      - TeamPreferenceAnalyzer.predict_team_preference() 사용

   team_score = vote_score*0.5 + freshness*0.25 + preference*0.25

2. rank_for_team(team_id: str, restaurants: list[dict],
                 vote_status: dict) -> list[dict]:
   전체 음식점에 team_score를 부여하고 내림차순 정렬.

타입 힌트 포함해줘.
```

### 7.2 통합 추천 엔진 프롬프트 (최종 조립)

```
engine/recommender.py를 구현해줘. 이 파일이 4개 소주제 전체를 통합하는 최종 엔진이야.

LunchRecommender 클래스:

1. __init__(self, session, team_id: str, user_id: str):
   DB 세션, 팀 ID, 사용자 ID로 초기화.
   내부적으로 각 소주제의 scorer를 인스턴스화.

2. get_recommendations(top_n: int = 5) -> list[dict]:
   종합 추천 리스트 반환.

   처리 흐름:
   a. 활성 음식점 목록 조회 (소주제 1)
   b. 현재 날씨 조회 및 날씨 점수 산출 (소주제 2)
   c. 사용자의 주간 영양 이력 기반 영양 점수 산출 (소주제 3)
   d. 현재 투표 현황 및 팀 점수 산출 (소주제 4)
   e. 4개 점수의 가중합으로 종합 점수 산출

   가중치:
   WEIGHTS = {
       "distance": 0.3,
       "weather": 0.2,
       "nutrition": 0.2,
       "team": 0.3,
   }

   composite_score = (
       distance_score * 0.3 +
       weather_score * 0.2 +
       nutrition_score * 0.2 +
       team_score * 0.3
   )

   반환:
   [
     {
       "rank": 1,
       "restaurant_id": "123",
       "restaurant_name": "한솥도시락",
       "category": "한식",
       "distance_m": 120,
       "composite_score": 82,
       "scores": {
         "distance": 100,
         "weather": 75,
         "nutrition": 68,
         "team": 85
       },
       "highlights": [
         "🏃 가장 가까운 음식점 (120m)",
         "🗳️ 팀원 3명이 투표",
         "🥩 이번 주 부족한 단백질 보충에 좋아요"
       ],
       "warnings": [
         "⚠️ 나트륨이 다소 높을 수 있어요"
       ]
     },
     ...
   ]

3. _generate_highlights(restaurant: dict, scores: dict,
                         weather: dict, diagnosis: dict) -> list[str]:
   각 음식점별 추천 포인트를 자연어로 생성.
   최대 3개까지.

4. _generate_warnings(restaurant: dict, scores: dict,
                       diagnosis: dict) -> list[str]:
   주의사항 생성. 최대 2개까지.

5. explain_recommendation(restaurant_id: str) -> dict:
   특정 음식점의 추천 이유를 상세 설명.
   4개 축별 점수와 근거를 포함.

타입 힌트, docstring, 로깅 포함해줘.
```

---

## 8. Step 6 — WebSocket 실시간 투표 (선택)

### Claude Code 프롬프트

```
이 Step은 선택 사항이야. MVP 이후 Phase 2에서 구현해도 돼.
하지만 구조만 잡아두면 좋을 것 같아.

api/ws_vote.py를 구현해줘.
FastAPI의 WebSocket을 사용한 실시간 투표 업데이트.

VoteWebSocket:

1. WebSocket 엔드포인트: /ws/vote/{team_id}
   - 클라이언트 연결 시 현재 투표 현황 전송
   - 투표 발생 시 연결된 모든 클라이언트에 broadcast
   - 투표 마감 시 최종 결과 broadcast 후 연결 종료

2. ConnectionManager 클래스:
   - active_connections를 team_id별로 관리
   - connect(websocket, team_id): 연결 추가
   - disconnect(websocket, team_id): 연결 제거
   - broadcast(team_id, message): 팀 전체에 메시지 전송

3. 메시지 형식:
   클라이언트 → 서버:
   {"type": "vote", "user_id": "user1", "restaurant_id": "123"}
   {"type": "veto", "user_id": "user1", "restaurant_id": "456"}

   서버 → 클라이언트:
   {"type": "vote_update", "data": {현재 투표 현황}}
   {"type": "vote_finalized", "data": {최종 결과}}
   {"type": "error", "message": "투표 시간이 아닙니다"}

기본적인 에러 처리와 연결 관리 포함해줘.
Phase 2에서 Redis Pub/Sub으로 확장 가능한 구조로 설계해줘.
```

---

## 9. Step 7 — 테스트 및 검증

### 9.1 투표 시스템 테스트 프롬프트

```
tests/test_vote_collector.py에 VoteManager의 테스트를 작성해줘.

인메모리 SQLite DB 사용. conftest.py에 User/Team/Restaurant seed 데이터 포함.

seed 데이터:
- Team: {"id": "team1", "name": "개발1팀"}
- Users: 5명 (user1~user5)
- Restaurants: 소주제 1에서 사용한 12개 음식점

테스트 케이스:
1. test_open_session: 세션 개시 및 status="open" 확인
2. test_open_session_duplicate: 같은 날 중복 개시 → 기존 세션 반환
3. test_cast_vote_new: 첫 투표 → status="created"
4. test_cast_vote_update: 투표 변경 → status="updated"
5. test_cast_vote_closed_session: 마감된 세션에 투표 → 에러
6. test_cast_veto: 거부권 행사 및 조회
7. test_get_current_status: 3명 투표 후 현황 정확히 반환
8. test_close_session_clear_winner: 단독 1위 확정
9. test_close_session_tiebreak: 동점 시 최근 방문일 기준 확정
10. test_close_session_low_participation: 참여율 50% 미만 경고
11. test_vote_on_vetoed_restaurant: 거부권 음식점 투표 시 경고

각 테스트에 적절한 setup/teardown 포함해줘.
```

### 9.2 방문 히스토리 테스트 프롬프트

```
tests/test_visit_tracker.py에 VisitTracker의 테스트를 작성해줘.

테스트 케이스:
1. test_record_visit: 방문 기록 저장 및 조회
2. test_record_visit_with_satisfaction: 만족도 점수 평균 계산
3. test_get_recent_visits: 최근 10영업일 방문 기록 조회
4. test_get_visit_frequency: 음식점별 빈도 분석
5. test_get_overvisited: 4회 이상 방문 음식점 추출
6. test_freshness_score_never_visited: 미방문 → 100점
7. test_freshness_score_yesterday: 어제 방문 → 10점
8. test_freshness_score_week_ago: 5영업일 전 → 70점
9. test_get_never_visited: 미방문 음식점 리스트

날짜 관련 테스트에서 freezegun 또는 unittest.mock.patch로
datetime.today()를 고정해줘.
```

### 9.3 통합 추천 엔진 테스트 프롬프트

```
tests/test_recommender.py에 LunchRecommender의 통합 테스트를 작성해줘.

이 테스트는 4개 소주제를 모두 통합한 최종 테스트야.

테스트 시나리오:
1. test_get_recommendations_basic:
   - 12개 음식점, 날씨 mock, 영양 mock, 투표 3건
   - 종합 점수 기반 top 5 추천 결과 확인
   - 1위의 composite_score가 2위보다 높은지

2. test_composite_score_calculation:
   - distance=100, weather=80, nutrition=60, team=90
   - composite = 100*0.3 + 80*0.2 + 60*0.2 + 90*0.3 = 85
   - 정확한 가중합 계산 확인

3. test_highlights_generation:
   - 가장 가까운 음식점 → "가장 가까운 음식점" 하이라이트 포함
   - 투표 1위 → "팀원 N명이 투표" 하이라이트 포함

4. test_warnings_generation:
   - 나트륨 과다 주간 + 고나트륨 메뉴 → 경고 포함

5. test_veto_impact:
   - 거부권 걸린 음식점의 team_score가 하락하는지

mock은 각 소주제의 scorer를 patch해서 고정 점수를 반환하도록 설정.
```

---

## 10. Step 8 — API 엔드포인트 확장

### Claude Code 프롬프트

```
api/main.py에 소주제 4 및 통합 추천 관련 엔드포인트를 추가해줘.

투표 관련:
1. POST /api/vote/session
   - 투표 세션 개시
   - Body: {"team_id": "team1"}

2. POST /api/vote/cast
   - 투표 행사
   - Body: {"user_id": "user1", "restaurant_id": "123"}

3. POST /api/vote/veto
   - 거부권 행사
   - Body: {"user_id": "user1", "restaurant_id": "456", "reason": "어제 먹었어요"}

4. GET /api/vote/status?team_id=team1
   - 현재 투표 현황 조회

5. POST /api/vote/close
   - 투표 마감 및 결과 확정
   - Body: {"team_id": "team1"}

6. GET /api/vote/history?team_id=team1&days=30
   - 투표 결과 이력

히스토리 관련:
7. GET /api/history/visits?team_id=team1&days=10
   - 최근 방문 기록

8. GET /api/history/frequency?team_id=team1
   - 음식점별 방문 빈도

9. GET /api/history/preference?team_id=team1
   - 팀 선호도 분석 결과

통합 추천:
10. GET /api/recommend?team_id=team1&user_id=user1&top_n=5
    - 4개 축 통합 최종 추천 (이 프로젝트의 핵심 엔드포인트!)
    - 응답: composite_score + 4개 개별 점수 + highlights + warnings

11. GET /api/recommend/{restaurant_id}/explain?team_id=team1&user_id=user1
    - 특정 음식점의 추천 이유 상세 설명

Pydantic 응답 모델 정의 포함.
CORS 미들웨어 확인.
각 엔드포인트에 적절한 HTTP 상태 코드 (201, 400, 404, 409 등) 처리.
```

---

## 11. Step 9 — 통합 파이프라인 최종 조립

### Claude Code 프롬프트

```
pipeline/scheduler.py를 최종 업데이트해줘.

전체 프로젝트의 파이프라인을 하나로 조립하는 최종 오케스트레이터야.

LunchOptimizerPipeline 클래스:

1. run_daily_pipeline() -> dict:
   매일 오전 9:30에 실행되는 일일 파이프라인.
   - Step 1: RestaurantPipeline.run_pipeline() (음식점 갱신)
   - Step 2: WeatherPipeline.run_pipeline() (날씨 수집)
   - Step 3: 영양 캐시 갱신 (새 음식점에 대한 매핑)
   - Step 4: VoteManager.open_session() (투표 세션 자동 개시)
   - 각 단계 소요 시간 측정 및 로깅

2. run_hourly_pipeline() -> dict:
   매시간 실행되는 파이프라인.
   - 날씨 데이터 갱신만 수행

3. run_vote_close() -> dict:
   매일 오전 11:30에 실행.
   - 투표 미마감 세션 자동 마감
   - 결과 확정 후 VisitHistory에 기록

4. start_all_schedulers():
   APScheduler로 3개 스케줄을 등록.
   - daily: CronTrigger(hour=9, minute=30)
   - hourly: CronTrigger(minute=0)
   - vote_close: CronTrigger(hour=11, minute=30)

5. get_pipeline_status() -> dict:
   각 파이프라인의 최근 실행 시각, 성공 여부, 소요 시간 반환.

main 블록:
  argparse로 실행 모드 선택:
  --daily: 일일 파이프라인 1회 실행
  --hourly: 시간별 파이프라인 1회 실행
  --schedule: 전체 스케줄러 시작
  --status: 파이프라인 상태 확인

에러 처리, 로깅, 그레이스풀 셧다운 포함해줘.
```

---

## 12. 트러블슈팅 가이드

### 자주 발생하는 문제와 Claude Code 해결 프롬프트

**문제 1: 하루에 동일 사용자가 2표 이상 등록됨**

```
UniqueConstraint(vote_date, user_id)가 있는데도
같은 사용자가 같은 날 2개 레코드가 생겨.
upsert 로직에서 기존 투표를 UPDATE하지 않고 INSERT를 시도하는 건 아닌지 확인해줘.
session.merge() 또는 INSERT ON CONFLICT UPDATE를 사용하도록 수정해줘.
```

**문제 2: 동점 처리 시 방문 이력이 없는 음식점**

```
동점 상황에서 최근 방문일 기준으로 처리하는데,
두 음식점 모두 방문 기록이 없어서 비교가 안 돼.
방문 기록 없음은 "가장 오래전 방문"으로 취급해서
미방문 음식점을 우선하도록 수정해줘.
그래도 동점이면 랜덤 선택 + 로깅.
```

**문제 3: 투표 시간 외 투표 시도**

```
투표 시간(10:00~11:30) 외에도 투표가 되고 있어.
VoteManager.cast_vote()에서 현재 시각을 확인하고,
시간 외 투표는 거부하는 로직을 추가해줘.
단, 관리자 권한으로 시간 제한을 무시할 수 있는 옵션도 포함해줘.
설정: VOTE_START_HOUR=10, VOTE_END_HOUR=11, VOTE_END_MINUTE=30
```

**문제 4: 만족도 기록 누락으로 선호도 분석 왜곡**

```
만족도 점수를 안 남기는 팀원이 많아서
avg_satisfaction이 왜곡돼.
만족도가 NULL인 기록은 평균 계산에서 제외하고,
기록률이 50% 미만이면 "데이터 부족" 경고를 표시해줘.
```

**문제 5: 통합 추천에서 특정 축의 점수가 항상 0**

```
team_score가 항상 0으로 나와.
투표가 없는 상태에서 team_score 기본값이 0이라
다른 축의 점수가 아무리 높아도 0.3 가중치만큼 손해를 봐.
투표가 없을 때는 team_score를 50(중립값)으로 설정하고,
가중치를 나머지 축에 재분배하는 로직을 추가해줘.
예: 투표 없음 → weights = {distance: 0.4, weather: 0.3, nutrition: 0.3, team: 0.0}
```

---

## 13. 체크리스트

### 구현 완료 확인

```
소주제 4 및 통합 추천 엔진의 구현 상태를 점검해줘.
아래 체크리스트 항목별로 현재 상태를 확인하고,
미완료 항목이 있으면 구현해줘.
```

**DB 모델:**
- [ ] Team, User, Vote, VoteSession, VisitHistory, Veto 모델 정의
- [ ] 모든 FK relationship 및 UniqueConstraint 설정
- [ ] seed 데이터 스크립트 (팀 1개, 팀원 5명)

**투표 시스템:**
- [ ] `VoteManager.open_session()` 세션 개시
- [ ] `cast_vote()` 투표 행사 (신규/변경 구분)
- [ ] `cast_veto()` 거부권 행사
- [ ] `get_current_status()` 현재 투표 현황 (참여율, 집계, 미투표자)
- [ ] `close_session()` 투표 마감 및 결과 확정
- [ ] 동점 처리 로직 (최근 방문일 기준 → 랜덤)
- [ ] 참여율 50% 미만 경고
- [ ] 거부권 경고 메시지

**방문 히스토리:**
- [ ] `VisitTracker.record_visit()` 방문 기록 저장
- [ ] `get_visit_frequency()` 음식점별 빈도 분석
- [ ] `calculate_freshness_score()` 방문 신선도 점수 (0~100)
- [ ] `get_overvisited()` 과다 방문 음식점 탐지
- [ ] `get_never_visited()` 미방문 음식점 리스트
- [ ] 영업일(월~금) 기준 계산

**팀 선호도:**
- [ ] `TeamPreferenceAnalyzer.analyze_team_preference()` 장기 선호도
- [ ] `calculate_variety_score()` 다양성 점수
- [ ] `predict_team_preference()` 선호 예측
- [ ] `get_team_mood()` 팀 분위기 판단

**팀 점수 산출:**
- [ ] `TeamRecommendScorer.calculate_team_score()` 투표+신선도+선호 합산
- [ ] 투표 없을 때 기본값 처리 (50 또는 가중치 재분배)

**통합 추천 엔진:**
- [ ] `LunchRecommender.get_recommendations()` 4축 가중합 산출
- [ ] highlights 자연어 생성 (최대 3개)
- [ ] warnings 자연어 생성 (최대 2개)
- [ ] `explain_recommendation()` 상세 설명

**통합 파이프라인:**
- [ ] 일일 파이프라인 (오전 9:30): 음식점 + 날씨 + 영양 + 투표세션
- [ ] 시간별 파이프라인: 날씨 갱신
- [ ] 투표 마감 파이프라인 (오전 11:30)
- [ ] APScheduler 3개 스케줄 등록

**API 엔드포인트:**
- [ ] 투표 관련 6개 엔드포인트
- [ ] 히스토리 관련 3개 엔드포인트
- [ ] 통합 추천 2개 엔드포인트 (핵심!)
- [ ] CORS, Pydantic 모델, 에러 코드 처리

**테스트:**
- [ ] vote_collector 테스트 11건
- [ ] visit_tracker 테스트 9건
- [ ] recommender 통합 테스트 5건
- [ ] 전체 테스트 통과 (`pytest tests/ -v`)

---

## 부록: 프로젝트 최종 완성 후 할 일

### 전체 소주제 통합 검증 프롬프트

```
4개 소주제가 모두 완성됐어.
전체 프로젝트의 통합 테스트를 실행하고,
다음 항목들을 최종 점검해줘:

1. 모든 테스트가 통과하는지 (pytest tests/ -v --tb=short)
2. API 서버를 띄우고 핵심 엔드포인트 3개를 curl로 테스트:
   - GET /api/recommend?team_id=team1&user_id=user1&top_n=5
   - GET /api/vote/status?team_id=team1
   - GET /api/nutrition/diagnosis?user_id=user1
3. 코드 린트 통과 (ruff check .)
4. README.md의 시작 가이드대로 실행했을 때 정상 동작하는지
5. .env.example에 모든 필수 환경변수가 포함됐는지
6. requirements.txt에 모든 의존성이 포함됐는지

문제가 있으면 수정하고, 최종 커밋 메시지도 작성해줘:
"feat: complete lunch optimizer pipeline with 4 sub-topics"
```

### 향후 확장 아이디어

| Phase | 기능 | 설명 |
|-------|------|------|
| Phase 2 | Slack/Teams 봇 | 투표 알림 및 결과 공유 자동화 |
| Phase 2 | Redis 캐싱 | API 응답 캐싱 및 WebSocket Pub/Sub |
| Phase 2 | 공휴일 처리 | 한국 공휴일 DB 연동하여 영업일 정확도 향상 |
| Phase 3 | ML 추천 | 협업 필터링으로 개인별 선호 예측 |
| Phase 3 | 사진 리뷰 | 식사 사진 업로드 및 팀 갤러리 |
| Phase 4 | Docker 배포 | docker-compose로 원클릭 배포 |
| Phase 4 | Streamlit 대시보드 | 데이터 분석가용 대안 인터페이스 |

---

<div align="center">

**🎉 4개 소주제가 모두 완성되었습니다!**

**거리 + 날씨 + 영양 + 팀 선호 = 오늘의 완벽한 점심**

*"오늘 뭐 먹지?" 이제 데이터가 답합니다.*

</div>
