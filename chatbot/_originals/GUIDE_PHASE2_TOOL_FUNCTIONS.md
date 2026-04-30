# 🔧 Phase 2: 8개 Tool Function 연결 — Claude Code 구현 가이드라인

> **목표**: Phase 1에서 만든 챗봇 코어에 소주제 1~4 파이프라인을 연결하여,
> 사용자의 자연어 질문이 실제 데이터 조회·행동 실행으로 이어지는 완전한 RAG 챗봇을 완성합니다.

---

## 📋 목차

1. [Phase 2 개요 및 목표](#1-phase-2-개요-및-목표)
2. [프로젝트 구조 확장](#2-프로젝트-구조-확장)
3. [Step 1 — Tool 정의 스키마 작성](#3-step-1--tool-정의-스키마-작성)
4. [Step 2 — Tool Executor 구현 (8개 함수)](#4-step-2--tool-executor-구현-8개-함수)
5. [Step 3 — Intent → Tool 라우팅 로직](#5-step-3--intent--tool-라우팅-로직)
6. [Step 4 — RAG Context Builder 고도화](#6-step-4--rag-context-builder-고도화)
7. [Step 5 — Tool Calling 루프 구현](#7-step-5--tool-calling-루프-구현)
8. [Step 6 — 프롬프트 기반 Tool Fallback](#8-step-6--프롬프트-기반-tool-fallback)
9. [Step 7 — Tool 결과 포맷터](#9-step-7--tool-결과-포맷터)
10. [Step 8 — API 및 UI 업데이트](#10-step-8--api-및-ui-업데이트)
11. [Step 9 — 통합 테스트](#11-step-9--통합-테스트)
12. [트러블슈팅 가이드](#12-트러블슈팅-가이드)
13. [체크리스트](#13-체크리스트)

---

## 1. Phase 2 개요 및 목표

### 1.1 Phase 1 → Phase 2 변화

| 항목 | Phase 1 | Phase 2 |
|------|---------|---------|
| LLM 역할 | 시스템 프롬프트 기반 자유 응답 | Tool 호출 기반 데이터 연동 응답 |
| 데이터 소스 | 하드코딩된 예시 데이터 | 소주제 1~4 실시간 DB 조회 |
| 행동 실행 | 불가능 | 투표/기록/거부권 등 DB 쓰기 |
| 컨텍스트 | 고정 시스템 프롬프트 | Intent별 동적 RAG 컨텍스트 |
| 정확도 | 일반적 추천 | 개인화 추천 (영양/선호 반영) |

### 1.2 8개 Tool Function 요약

| # | Tool 이름 | 소주제 | 종류 | 설명 |
|---|----------|--------|------|------|
| T1 | `get_lunch_recommendations` | 통합 | 읽기 | 4축 종합 추천 |
| T2 | `get_current_weather` | 소주제2 | 읽기 | 현재 날씨+미세먼지 |
| T3 | `get_nutrition_diagnosis` | 소주제3 | 읽기 | 주간 영양 진단 |
| T4 | `get_restaurant_info` | 소주제1+3 | 읽기 | 음식점 상세 정보 |
| T5 | `cast_vote` | 소주제4 | 쓰기 | 투표 행사 |
| T6 | `get_vote_status` | 소주제4 | 읽기 | 투표 현황 조회 |
| T7 | `record_meal` | 소주제3+4 | 쓰기 | 식사 기록 저장 |
| T8 | `get_visit_history` | 소주제4 | 읽기 | 방문 이력 조회 |

### 1.3 핵심 설계 원칙

**두 가지 Tool 호출 방식을 모두 구현합니다:**

- **방식 A — Native Function Calling**: Ollama의 `tools` 파라미터를 사용. Qwen3.5, Gemma4 등 지원 모델에서 사용.
- **방식 B — 프롬프트 기반 Fallback**: Tool Calling을 지원하지 않는 모델을 위해, 시스템 프롬프트에 Tool 목록을 텍스트로 정의하고 LLM 응답에서 `[TOOL: name(args)]` 패턴을 파싱.

런타임에 모델의 Tool Calling 지원 여부를 감지하여 자동으로 방식을 전환합니다.

---

## 2. 프로젝트 구조 확장

### Claude Code 프롬프트

```
Phase 1에서 만든 chatbot/ 디렉토리를 Phase 2 구조로 확장해줘.

수정/추가할 파일:
chatbot/
├── tools.py                    # 확장: 8개 Tool 정의 + ToolExecutor
├── tool_definitions.py         # 신규: Ollama 형식 Tool 스키마
├── tool_router.py              # 신규: Intent → Tool 매핑 로직
├── tool_formatter.py           # 신규: Tool 결과 → LLM 친화 텍스트
├── tool_fallback.py            # 신규: 프롬프트 기반 Tool 파싱
├── context_builder.py          # 확장: Tool 결과 기반 동적 컨텍스트
├── core.py                     # 확장: Tool Calling 루프 통합
└── prompts/
    ├── system.md               # 확장: Tool 설명 추가
    └── tool_prompt.md          # 신규: 프롬프트 기반 Tool용 프롬프트

tests/
├── test_tool_definitions.py    # 신규
├── test_tool_executor.py       # 신규
├── test_tool_router.py         # 신규
├── test_tool_formatter.py      # 신규
├── test_tool_fallback.py       # 신규
├── test_phase2_integration.py  # 신규: 전체 흐름 통합 테스트
└── fixtures/
    └── mock_pipeline_data.py   # 신규: 테스트용 mock 데이터 모음
```

---

## 3. Step 1 — Tool 정의 스키마 작성

### Claude Code 프롬프트

```
chatbot/tool_definitions.py를 구현해줘.

Ollama의 tools 파라미터에 전달할 8개 Tool의 스키마를 정의해줘.
각 Tool의 name, description, parameters를 JSON Schema 형식으로 작성.

중요: description은 LLM이 "이 Tool을 언제 호출해야 하는지"를
판단하는 데 핵심적인 역할을 하므로, 최대한 구체적으로 작성해줘.

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_lunch_recommendations",
            "description": (
                "오늘의 날씨, 사용자의 주간 영양 섭취 이력, "
                "팀원 투표 현황, 음식점 거리를 종합 분석하여 "
                "최적의 점심 음식점을 순위별로 추천합니다. "
                "사용자가 '추천해줘', '오늘 뭐 먹지?', '점심 메뉴 알려줘' 등의 "
                "추천 요청을 할 때 호출합니다."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "top_n": {
                        "type": "integer",
                        "description": "추천 개수 (기본값: 5, 최대: 10)",
                        "default": 5
                    },
                    "category": {
                        "type": "string",
                        "description": "카테고리 필터. 한식, 일식, 양식, 중식, 동남아 중 하나. 사용자가 특정 카테고리를 언급한 경우에만 설정.",
                        "enum": ["한식", "일식", "양식", "중식", "동남아"]
                    },
                    "max_distance": {
                        "type": "integer",
                        "description": "최대 거리 제한(미터). 사용자가 '가까운 곳', '근처' 등을 언급한 경우 200으로 설정."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_weather",
            "description": (
                "현재 사무실 주변의 기온, 습도, 강수확률, 하늘상태, "
                "미세먼지 농도를 조회합니다. "
                "사용자가 '날씨', '비', '미세먼지', '기온' 등을 "
                "언급하거나, 날씨 기반 추천이 필요할 때 호출합니다."
            ),
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_nutrition_diagnosis",
            "description": (
                "사용자의 이번 주 점심 식사 영양 섭취를 분석합니다. "
                "칼로리, 탄수화물, 단백질, 지방, 나트륨의 일별 섭취량과 "
                "주간 평균을 계산하고, 부족/과다 영양소를 진단합니다. "
                "사용자가 '영양', '칼로리', '단백질', '이번 주 상태', "
                "'건강' 등을 언급할 때 호출합니다."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "사용자 ID"
                    }
                },
                "required": ["user_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_restaurant_info",
            "description": (
                "특정 음식점의 상세 정보를 조회합니다. "
                "거리, 카테고리, 추정 영양정보(칼로리/탄/단/지), "
                "방문 횟수, 최근 방문일, 각 축별 점수를 포함합니다. "
                "사용자가 특정 음식점 이름을 언급하며 정보를 물어볼 때 호출합니다."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "restaurant_name": {
                        "type": "string",
                        "description": "음식점 이름 (예: 한솥도시락, 서브웨이, 명동칼국수)"
                    }
                },
                "required": ["restaurant_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "cast_vote",
            "description": (
                "점심 투표를 행사합니다. 하루에 1인 1표이며, "
                "마감 전까지 변경이 가능합니다. "
                "사용자가 '투표', '한 표', '거기로 할게' 등을 "
                "특정 음식점과 함께 언급할 때 호출합니다."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "투표하는 사용자 ID"
                    },
                    "restaurant_name": {
                        "type": "string",
                        "description": "투표할 음식점 이름"
                    }
                },
                "required": ["user_id", "restaurant_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_vote_status",
            "description": (
                "현재 팀의 점심 투표 현황을 조회합니다. "
                "누가 어디에 투표했는지, 몇 명이 투표했는지, "
                "현재 1위 음식점이 어디인지를 포함합니다. "
                "사용자가 '투표 현황', '누가 투표', '몇 표' 등을 언급할 때 호출합니다."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "team_id": {
                        "type": "string",
                        "description": "팀 ID"
                    }
                },
                "required": ["team_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "record_meal",
            "description": (
                "식사 기록을 저장합니다. 어떤 음식점에서 식사했는지와 "
                "선택적으로 만족도(1~5점)를 기록합니다. "
                "사용자가 '먹었어', '다녀왔어', '기록해줘', 'N점 줄게' 등을 "
                "음식점 이름과 함께 언급할 때 호출합니다."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "사용자 ID"
                    },
                    "restaurant_name": {
                        "type": "string",
                        "description": "식사한 음식점 이름"
                    },
                    "satisfaction": {
                        "type": "integer",
                        "description": "만족도 점수 (1~5). 사용자가 언급한 경우에만 설정.",
                        "minimum": 1,
                        "maximum": 5
                    }
                },
                "required": ["user_id", "restaurant_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_visit_history",
            "description": (
                "팀의 최근 음식점 방문 기록을 조회합니다. "
                "어떤 음식점을 언제 방문했는지, 만족도는 어땠는지를 포함합니다. "
                "사용자가 '최근에 뭐 먹었지', '지난번', '히스토리' 등을 언급할 때 호출합니다."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "team_id": {
                        "type": "string",
                        "description": "팀 ID"
                    },
                    "days": {
                        "type": "integer",
                        "description": "조회 기간 (일 수, 기본값: 7)",
                        "default": 7
                    }
                },
                "required": ["team_id"]
            }
        }
    }
]

또한 유틸리티 함수도 추가해줘:

def get_tool_by_name(name: str) -> dict | None:
    TOOL_DEFINITIONS에서 이름으로 Tool 검색.

def get_all_tool_names() -> list[str]:
    전체 Tool 이름 목록 반환.

def get_read_tools() -> list[dict]:
    읽기 전용 Tool만 반환 (get_* 계열).

def get_write_tools() -> list[dict]:
    쓰기 Tool만 반환 (cast_vote, record_meal).

타입 힌트, docstring 포함해줘.
```

---

## 4. Step 2 — Tool Executor 구현 (8개 함수)

### Claude Code 프롬프트

```
chatbot/tools.py를 Phase 2 수준으로 확장해줘.

ToolExecutor 클래스:

기존 소주제 1~4의 코드를 import하여 각 Tool을 실제 실행하는 클래스.
각 메서드는 Tool의 arguments를 받아 파이프라인 코드를 호출하고,
결과를 dict로 반환해.

1. __init__(self, db_session, user_id: str, team_id: str):
   DB 세션, 현재 사용자 ID, 팀 ID로 초기화.
   내부적으로 각 소주제의 loader/scorer를 lazy 초기화:
   - self._recommender = None  (처음 호출 시 생성)
   - self._weather_loader = None
   - self._nutrition_loader = None
   - self._vote_manager = None
   - self._visit_tracker = None

2. execute(tool_name: str, arguments: dict) -> dict:
   tool_name에 따라 해당 메서드를 라우팅.
   실행 시간을 측정하여 로깅.
   에러 발생 시 {"success": False, "error": "메시지"}를 반환.

3. _exec_get_lunch_recommendations(top_n=5, category=None, max_distance=None) -> dict:
   engine/recommender.py의 LunchRecommender.get_recommendations() 호출.
   
   반환:
   {
     "success": True,
     "recommendations": [
       {
         "rank": 1,
         "name": "명동칼국수",
         "category": "한식",
         "distance_m": 320,
         "composite_score": 82,
         "scores": {"distance": 70, "weather": 75, "nutrition": 68, "team": 85},
         "highlights": ["팀원 3명 투표", "단백질 보충에 좋아요"],
         "calories": 550,
         "protein": 20
       },
       ...
     ],
     "weather_summary": "기온 12°C, 흐림",
     "nutrition_summary": "이번 주 단백질 부족"
   }

4. _exec_get_current_weather() -> dict:
   pipeline/loaders/db_loader.py의 WeatherLoader.get_latest_weather() 호출.
   최신 데이터가 1시간 이상 오래되었으면 WeatherPipeline을 즉시 실행.
   
   반환:
   {
     "success": True,
     "temp": 12.5,
     "humidity": 55,
     "sky": "흐림",
     "pop": 30,
     "pm10": 45,
     "pm25": 22,
     "dust_grade": "보통",
     "tips": ["쌀쌀한 날씨에는 국물류를 추천합니다"]
   }

5. _exec_get_nutrition_diagnosis(user_id: str) -> dict:
   NutritionDiagnostic.diagnose_weekly() 호출.
   
   반환:
   {
     "success": True,
     "overall_status": "주의",
     "overall_score": 72,
     "recorded_days": 3,
     "avg_calories": 607,
     "nutrients": {
       "protein": {"status": "부족", "avg": 18.5, "target": 28},
       "carbs": {"status": "과다", "avg": 95.0, "target": 85},
       "fat": {"status": "적정", "avg": 20.0, "target": 18},
       "sodium": {"status": "과다", "avg": 1200, "max": 800}
     },
     "recommendations": ["단백질 섭취를 늘려보세요", "나트륨 주의"]
   }

6. _exec_get_restaurant_info(restaurant_name: str) -> dict:
   음식점명으로 DB 검색 (퍼지 매칭 포함).
   RestaurantLoader + NutritionLoader 조합.
   
   반환:
   {
     "success": True,
     "found": True,
     "name": "한솥도시락",
     "category": "한식",
     "distance_m": 120,
     "scores": {"distance": 100, "weather": 60, "nutrition": 55, "composite": 72},
     "nutrition": {"calories": 650, "protein": 25, "carbs": 90, "fat": 18},
     "visit_count": 12,
     "last_visit": "2026-04-03",
     "avg_satisfaction": 4.1
   }
   
   음식점을 찾지 못한 경우:
   {"success": True, "found": False, "message": "'스시로'와(과) 유사한 음식점을 찾지 못했습니다", "suggestions": ["스시로(350m)", "회전초밥(420m)"]}

7. _exec_cast_vote(user_id: str, restaurant_name: str) -> dict:
   음식점명을 ID로 변환 후 VoteManager.cast_vote() 호출.
   
   반환:
   {
     "success": True,
     "action": "created",  # 또는 "updated"
     "restaurant_name": "한솥도시락",
     "current_tally": [
       {"name": "한솥도시락", "votes": 3},
       {"name": "서브웨이", "votes": 1}
     ],
     "participation": "4/5명 투표 (80%)"
   }
   
   투표 시간 외:
   {"success": False, "error": "투표 시간(10:00~11:30)이 아닙니다"}

8. _exec_get_vote_status(team_id: str) -> dict:
   VoteManager.get_current_status() 호출.
   
   반환:
   {
     "success": True,
     "status": "open",
     "voted": [
       {"name": "김민수", "restaurant": "한솥도시락", "time": "10:15"},
       {"name": "이수진", "restaurant": "한솥도시락", "time": "10:22"}
     ],
     "not_voted": ["박준혁", "정하은", "최동원"],
     "tally": [{"name": "한솥도시락", "votes": 2}],
     "participation": "2/5명 (40%)"
   }

9. _exec_record_meal(user_id: str, restaurant_name: str, satisfaction: int = None) -> dict:
   MealTracker.record_meal() + VisitTracker.record_visit() 호출.
   영양 정보 자동 매핑 포함.
   
   반환:
   {
     "success": True,
     "restaurant_name": "서브웨이",
     "nutrition_recorded": {"calories": 380, "protein": 24, "carbs": 48, "fat": 14},
     "satisfaction": 4,
     "weekly_update": "이번 주 4일째 기록! 평균 칼로리 567kcal",
     "nutrition_comment": "단백질 24g으로 이번 주 부족분을 잘 보충했어요!"
   }

10. _exec_get_visit_history(team_id: str, days: int = 7) -> dict:
    VisitTracker.get_recent_visits() 호출.
    
    반환:
    {
      "success": True,
      "visits": [
        {"date": "2026-04-04", "restaurant": "맥도날드", "satisfaction": 3.5},
        {"date": "2026-04-03", "restaurant": "한솥도시락", "satisfaction": 4.2},
        ...
      ],
      "total_visits": 5,
      "unique_restaurants": 4,
      "most_frequent": "한솥도시락 (2회)"
    }

11. _resolve_restaurant_name(name: str) -> tuple[str, str] | None:
    음식점 이름을 DB에서 검색하여 (id, 정확한_이름) 반환.
    정확 매칭 우선 → 부분 매칭 → 퍼지 매칭(80%+).
    못 찾으면 None 반환.

각 메서드에서 파이프라인 모듈이 아직 구현되지 않은 경우를 대비하여
try-except로 ImportError를 처리하고 mock 데이터를 반환하는
_get_mock_response(tool_name) fallback도 포함해줘.

로깅: 각 Tool 실행 시작/완료/실패를 INFO/ERROR로 로깅.
실행 시간(ms) 측정.
타입 힌트, docstring 포함해줘.
```

---

## 5. Step 3 — Intent → Tool 라우팅 로직

### Claude Code 프롬프트

```
chatbot/tool_router.py를 구현해줘.

ToolRouter 클래스:

사용자의 Intent 분류 결과를 기반으로
어떤 Tool을 어떤 순서로 호출해야 하는지 결정하는 라우터.

1. route(intent_result: dict, user_id: str, team_id: str) -> list[dict]:
   Intent에 따라 호출할 Tool과 arguments를 결정.
   반환: [{"tool_name": "...", "arguments": {...}}, ...]
   
   여러 Tool을 순차 호출해야 하는 경우도 있으므로 리스트로 반환.

라우팅 규칙:

RECOMMEND:
  → [{"tool_name": "get_lunch_recommendations", "arguments": {"top_n": 5}}]

RECOMMEND_CONDITIONAL:
  entities에서 조건 추출:
  - category가 있으면 → arguments에 category 추가
  - "가까운", "근처" → max_distance=200
  - "단백질", "건강" → 먼저 get_nutrition_diagnosis 호출 후 추천
  
  예: "가까운 한식집 추천" →
  [{"tool_name": "get_lunch_recommendations",
    "arguments": {"top_n": 5, "category": "한식", "max_distance": 200}}]
  
  예: "단백질 많은 곳" →
  [{"tool_name": "get_nutrition_diagnosis", "arguments": {"user_id": "..."}},
   {"tool_name": "get_lunch_recommendations", "arguments": {"top_n": 5}}]

QUERY_RESTAURANT:
  → [{"tool_name": "get_restaurant_info",
      "arguments": {"restaurant_name": entities["restaurant_name"]}}]

QUERY_WEATHER:
  → [{"tool_name": "get_current_weather", "arguments": {}}]

QUERY_NUTRITION:
  → [{"tool_name": "get_nutrition_diagnosis",
      "arguments": {"user_id": user_id}}]

QUERY_VOTE:
  → [{"tool_name": "get_vote_status",
      "arguments": {"team_id": team_id}}]

QUERY_HISTORY:
  → [{"tool_name": "get_visit_history",
      "arguments": {"team_id": team_id, "days": 7}}]

ACTION_VOTE:
  → [{"tool_name": "cast_vote",
      "arguments": {"user_id": user_id,
                     "restaurant_name": entities["restaurant_name"]}}]

ACTION_RECORD:
  → [{"tool_name": "record_meal",
      "arguments": {"user_id": user_id,
                     "restaurant_name": entities["restaurant_name"],
                     "satisfaction": entities.get("satisfaction")}}]

FOLLOWUP:
  → 이전 추천 결과에서 number_ref에 해당하는 음식점을 찾아
     get_restaurant_info를 호출.
  
  예: "2번째 거 상세 알려줘" →
  last_recommendations에서 2번째 음식점 이름 추출 →
  [{"tool_name": "get_restaurant_info",
    "arguments": {"restaurant_name": "서브웨이"}}]

CHITCHAT:
  → [] (Tool 호출 불필요)

2. _inject_defaults(tool_calls: list[dict], user_id, team_id) -> list[dict]:
   각 Tool의 arguments에 user_id/team_id가 필요한데 빠져있으면 자동 주입.

타입 힌트, docstring 포함해줘.
```

---

## 6. Step 4 — RAG Context Builder 고도화

### Claude Code 프롬프트

```
chatbot/context_builder.py를 Phase 2 수준으로 확장해줘.

Phase 1에서는 시스템 프롬프트만 조립했지만,
Phase 2에서는 Tool 실행 결과를 LLM 컨텍스트에 주입하는 역할도 담당해.

ContextBuilder에 다음 메서드를 추가/수정해줘:

1. build_tool_context(tool_results: list[dict]) -> str:
   여러 Tool의 실행 결과를 하나의 컨텍스트 문자열로 조립.
   
   예:
   "[데이터 조회 결과]

   ▶ 오늘의 추천 (get_lunch_recommendations)
   1. 명동칼국수 | 320m | 종합82점 | 한식/국물 | 550kcal
      → 팀원 3명 투표, 단백질 보충에 좋아요
   2. 서브웨이 | 180m | 종합78점 | 양식/샌드위치 | 380kcal
      → 가장 가까운 고단백 메뉴
   ...

   ▶ 현재 날씨 (get_current_weather)
   기온 12°C | 흐림 | 강수확률 30% | 미세먼지 보통

   ▶ 영양 상태 (get_nutrition_diagnosis)
   종합: 주의 (72점) | 단백질 부족 | 나트륨 과다

   위 데이터를 바탕으로 사용자에게 자연스럽게 답변해주세요.
   데이터를 그대로 나열하지 말고, 핵심만 간결하게 전달하세요."

2. build_action_context(tool_result: dict) -> str:
   쓰기 Tool(투표, 기록) 실행 결과를 컨텍스트로 변환.
   
   예:
   "[행동 실행 결과]
   투표 완료: 한솥도시락에 투표했습니다.
   현재 투표 현황: 한솥 3표, 서브웨이 1표 (4/5명 참여)
   
   이 결과를 사용자에게 확인해주고, 추가 행동을 제안해주세요."

3. enrich_system_prompt(base_prompt: str, tool_context: str) -> str:
   기본 시스템 프롬프트에 Tool 결과 컨텍스트를 결합.
   토큰 수를 체크하여 컨텍스트가 너무 길면 요약 버전을 사용.

4. _summarize_recommendations(recommendations: list[dict]) -> str:
   추천 결과를 LLM이 이해하기 쉬운 간결한 텍스트로 변환.
   이름 | 거리 | 점수 | 한줄 이유 형식.

5. _summarize_diagnosis(diagnosis: dict) -> str:
   영양 진단 결과를 1~2줄로 요약.
   예: "이번 주 3일 기록, 단백질 부족(18g/28g), 나트륨 과다"

타입 힌트, docstring 포함해줘.
```

---

## 7. Step 5 — Tool Calling 루프 구현

### Claude Code 프롬프트

```
chatbot/core.py를 Phase 2 수준으로 확장해줘.

LunchChatbot 클래스의 chat() 및 chat_stream() 메서드를
Tool Calling 루프가 포함된 버전으로 업그레이드.

핵심 변경:

1. chat(user_message: str) -> str:
   전체 흐름:
   
   a. 사용자 메시지를 히스토리에 추가
   b. IntentClassifier로 Intent 분류
   c. ToolRouter로 호출할 Tool 목록 결정
   d. 각 Tool을 ToolExecutor로 순차 실행
   e. Tool 결과를 ContextBuilder로 컨텍스트 조립
   f. 시스템 프롬프트 + 컨텍스트 + 히스토리로 메시지 구성
   g. OllamaChat.chat() 호출
   h. 응답에 추가 tool_calls가 있으면 실행 후 재호출 (최대 3회)
   i. 최종 응답을 히스토리에 추가
   j. 추천 결과가 있으면 last_recommendations에 저장
   k. 응답 반환
   
   tool_calls 재호출 루프:
   max_iterations = 3
   for i in range(max_iterations):
       response = ollama.chat(messages, tools=TOOL_DEFINITIONS)
       if response has tool_calls:
           for tool_call in response.tool_calls:
               result = executor.execute(tool_call.name, tool_call.arguments)
               messages.append({"role": "tool", "content": json.dumps(result)})
       else:
           break  # 더 이상 Tool 호출 없으면 루프 종료
   
   최종 응답 = response.message.content

2. chat_stream(user_message: str) -> Generator[str, None, None]:
   스트리밍 버전. 핵심 차이:
   
   - Tool 실행은 스트리밍 시작 전에 모두 완료
   - Tool 결과를 컨텍스트에 포함한 상태에서 스트리밍 시작
   - 스트리밍 중에는 추가 Tool 호출 없음
   
   흐름:
   a~e: chat()과 동일 (비스트리밍)
   f. "데이터를 조회하고 있어요..." 같은 중간 상태 yield (선택)
   g. 컨텍스트가 완성되면 chat_stream()으로 최종 응답 스트리밍
   h. 전체 응답 텍스트를 누적하여 히스토리에 추가

3. _detect_tool_calling_support() -> bool:
   현재 Ollama 모델이 native tool calling을 지원하는지 확인.
   방법: tools 파라미터를 포함한 테스트 요청을 보내고,
         tool_calls 응답이 오면 True, 아니면 False.
   결과를 캐싱하여 재확인 방지.

4. _use_fallback_if_needed(user_message, intent, tool_calls) -> str:
   Native Tool Calling이 안 되면 프롬프트 기반 Fallback으로 전환.
   (Step 6에서 상세 구현)

tool 실행 중 에러 발생 시:
- 해당 Tool 결과를 {"error": "..."} 로 표시
- 나머지 Tool은 계속 실행
- LLM에게 에러 사실을 전달하여 적절히 안내하도록 함

로깅: 전체 파이프라인 실행 시간, Tool별 실행 시간, 총 LLM 호출 횟수.
타입 힌트, docstring 포함해줘.
```

---

## 8. Step 6 — 프롬프트 기반 Tool Fallback

### Claude Code 프롬프트

```
chatbot/tool_fallback.py를 구현해줘.

PromptBasedToolCaller 클래스:

Native Function Calling을 지원하지 않는 모델을 위한 대안 방식.
시스템 프롬프트에 Tool 사용법을 텍스트로 정의하고,
LLM 응답에서 Tool 호출 패턴을 파싱하여 실행.

1. get_tool_prompt() -> str:
   Tool 사용법을 설명하는 프롬프트 텍스트 반환.
   
   반환 내용 예시:
   """
   ## 사용 가능한 도구
   아래 도구를 사용하여 실제 데이터를 조회하거나 행동을 실행할 수 있습니다.
   도구가 필요하면 반드시 아래 형식으로 호출하세요:
   
   [TOOL_CALL]
   name: 도구이름
   args: {"param1": "value1", "param2": "value2"}
   [/TOOL_CALL]
   
   사용 가능한 도구 목록:
   - get_lunch_recommendations: 종합 점심 추천 (top_n, category, max_distance)
   - get_current_weather: 현재 날씨 조회 (파라미터 없음)
   - get_nutrition_diagnosis: 주간 영양 진단 (user_id)
   - get_restaurant_info: 음식점 상세 정보 (restaurant_name)
   - cast_vote: 투표 행사 (user_id, restaurant_name)
   - get_vote_status: 투표 현황 (team_id)
   - record_meal: 식사 기록 (user_id, restaurant_name, satisfaction)
   - get_visit_history: 방문 이력 (team_id, days)
   
   중요: 도구 호출 후 그 결과를 기다리지 말고,
   "[도구 결과 대기 중]"이라고만 쓰세요.
   결과는 시스템이 자동으로 제공합니다.
   """

2. parse_tool_calls(response_text: str) -> list[dict]:
   LLM 응답 텍스트에서 [TOOL_CALL]...[/TOOL_CALL] 패턴을 파싱.
   
   파싱 대상 예시:
   "오늘 점심을 추천해드릴게요! 먼저 데이터를 조회할게요.
   
   [TOOL_CALL]
   name: get_lunch_recommendations
   args: {"top_n": 5, "category": "한식"}
   [/TOOL_CALL]
   
   [도구 결과 대기 중]"
   
   반환:
   [{"tool_name": "get_lunch_recommendations",
     "arguments": {"top_n": 5, "category": "한식"}}]
   
   파싱 실패 시 빈 리스트 반환.

3. build_result_injection(tool_name: str, result: dict) -> str:
   Tool 실행 결과를 LLM에게 재전달할 메시지 형식으로 구성.
   
   반환:
   "[TOOL_RESULT]
   tool: get_lunch_recommendations
   result: {결과 JSON}
   [/TOOL_RESULT]
   
   위 결과를 바탕으로 사용자에게 자연스럽게 답변해주세요."

4. should_use_fallback(model_name: str) -> bool:
   모델이 native tool calling을 지원하는지 판단.
   알려진 지원 모델 목록:
   - qwen3.5 계열: 지원
   - gemma4 계열: 지원
   - llama3 계열: 부분 지원
   - mistral 계열: 부분 지원
   모델명이 목록에 없으면 True (fallback 사용).

정규식은 re 모듈 사용.
JSON 파싱 실패 시 방어 코드 포함.
타입 힌트, docstring 포함해줘.
```

---

## 9. Step 7 — Tool 결과 포맷터

### Claude Code 프롬프트

```
chatbot/tool_formatter.py를 구현해줘.

ToolResultFormatter 클래스:

Tool의 raw 실행 결과를 LLM이 자연어로 전환하기 좋은
구조화된 텍스트로 변환하는 역할.

1. format(tool_name: str, result: dict) -> str:
   tool_name에 따라 적절한 포맷팅 메서드를 호출.

2. _format_recommendations(result: dict) -> str:
   예:
   "추천 결과 (5개):
   1. 명동칼국수 (320m, 82점) - 한식/국물, 550kcal, 단백질 20g
      ✅ 팀원 3명 투표 ✅ 단백질 보충
   2. 서브웨이 (180m, 78점) - 양식/샌드위치, 380kcal, 단백질 24g
      ✅ 가장 가까운 고단백
   3. 한솥도시락 (120m, 75점) - 한식/밥류, 650kcal
      ✅ 팀 인기 1위
   현재 날씨: 12°C 흐림 | 영양: 단백질 부족"

3. _format_weather(result: dict) -> str:
   예:
   "현재 날씨: 기온 12°C, 흐림, 강수확률 30%
   미세먼지: PM10 45(보통), PM2.5 22(보통)
   팁: 쌀쌀한 날씨에는 국물류를 추천합니다"

4. _format_nutrition(result: dict) -> str:
   예:
   "이번 주 영양 진단 (3일 기록):
   종합: 주의 (72/100점)
   - 칼로리: 607kcal (적정 ✅)
   - 단백질: 18.5g (부족 ⚠️, 목표 28g)
   - 탄수화물: 95g (과다 ⚠️, 목표 85g)
   - 나트륨: 1,200mg (과다 🔴, 최대 800mg)
   추천: 단백질 섭취를 늘려보세요"

5. _format_restaurant_info(result: dict) -> str:
6. _format_vote_result(result: dict) -> str:
7. _format_vote_status(result: dict) -> str:
8. _format_meal_record(result: dict) -> str:
9. _format_visit_history(result: dict) -> str:

각 포맷터는:
- 핵심 정보만 추출 (LLM에게 너무 많은 데이터를 주면 오히려 품질 저하)
- 이모지로 상태 표시 (✅ 좋음, ⚠️ 주의, 🔴 나쁨)
- success=False인 경우 에러 메시지를 사용자 친화적으로 변환

10. format_multiple(results: list[tuple[str, dict]]) -> str:
    여러 Tool 결과를 하나의 텍스트로 합침.
    results: [(tool_name, result), ...]
    각 결과 사이에 빈 줄 구분.

타입 힌트, docstring 포함해줘.
```

---

## 10. Step 8 — API 및 UI 업데이트

### 10.1 FastAPI 업데이트 프롬프트

```
api/chat_router.py를 Phase 2 수준으로 업데이트해줘.

변경 사항:

1. POST /api/chat 응답에 메타데이터 추가:
   {
     "reply": "...",
     "metadata": {
       "intent": "RECOMMEND",
       "tools_used": [
         {"name": "get_lunch_recommendations", "execution_time_ms": 245},
         {"name": "get_current_weather", "execution_time_ms": 120}
       ],
       "total_time_ms": 3200,
       "model": "qwen3.5:7b",
       "tokens_used": 1850
     }
   }

2. GET /api/chat/stream의 SSE에 Tool 실행 상태 이벤트 추가:
   data: {"type": "tool_start", "tool": "get_lunch_recommendations"}
   data: {"type": "tool_done", "tool": "get_lunch_recommendations", "time_ms": 245}
   data: {"type": "thinking", "content": "데이터를 분석하고 있어요..."}
   data: {"type": "token", "content": "오"}
   data: {"type": "token", "content": "늘"}
   ...
   data: {"type": "done", "metadata": {...}}

   이렇게 하면 React UI에서 Tool 실행 중에
   "🔍 음식점 데이터 조회 중..." 같은 로딩 표시가 가능.

3. GET /api/tools
   사용 가능한 Tool 목록과 설명 반환 (디버깅/문서화용).
```

### 10.2 React UI 업데이트 프롬프트

```
React 채팅 UI를 Phase 2 수준으로 업데이트해줘.

변경 사항:

1. useChat 훅에 toolStatus 상태 추가:
   - Tool 실행 중일 때 "🔍 날씨 데이터 조회 중..." 표시
   - 여러 Tool 순차 실행 시 진행 상황 표시

2. SSE 파싱에 tool_start/tool_done/thinking 이벤트 처리 추가:
   - tool_start: 로딩 인디케이터 + Tool 이름 표시
   - tool_done: 체크마크로 전환
   - thinking: "분석 중..." 텍스트 표시
   - token: 기존 스트리밍 텍스트 누적

3. MessageBubble에 메타데이터 표시 (접기/펼치기):
   - 사용된 Tool 목록
   - 응답 시간
   - 모델명

4. RestaurantCard 컴포넌트 구현 (추천 결과 시 표시):
   - 음식점명, 카테고리 배지, 거리, 종합 점수
   - 4축 점수 미니 바 차트
   - "투표하기" 버튼 (클릭 시 투표 메시지 자동 전송)
   - "상세보기" 버튼 (클릭 시 상세 질문 전송)

5. 투표 현황 미니 위젯:
   - 채팅 상단에 현재 투표 현황 바 차트 표시
   - 실시간 업데이트 (투표 시 자동 갱신)
```

---

## 11. Step 9 — 통합 테스트

### Claude Code 프롬프트

```
tests/test_phase2_integration.py에 Phase 2 전체 통합 테스트를 작성해줘.

Ollama는 mock, DB는 인메모리 SQLite, 파이프라인 데이터는 fixtures/mock_pipeline_data.py에서 로드.

tests/fixtures/mock_pipeline_data.py:
- MOCK_RESTAURANTS: 12개 음식점 dict 리스트
- MOCK_WEATHER: 날씨 정보 dict
- MOCK_NUTRITION_DIAGNOSIS: 영양 진단 결과 dict
- MOCK_VOTE_STATUS: 투표 현황 dict
- MOCK_VISIT_HISTORY: 방문 이력 리스트
- MOCK_RECOMMENDATIONS: 종합 추천 결과 리스트

테스트 시나리오:

Tool Definitions:
1. test_tool_definitions_count: 8개 Tool이 정의되어 있는지
2. test_tool_definitions_schema: 각 Tool의 name, description, parameters 존재 확인
3. test_get_read_tools: 읽기 Tool 6개 반환
4. test_get_write_tools: 쓰기 Tool 2개 반환

ToolExecutor:
5. test_execute_recommendations: get_lunch_recommendations 실행 → 추천 리스트 반환
6. test_execute_weather: get_current_weather 실행 → 날씨 정보 반환
7. test_execute_nutrition: get_nutrition_diagnosis 실행 → 진단 결과 반환
8. test_execute_restaurant_info_found: 존재하는 음식점 → found=True
9. test_execute_restaurant_info_not_found: 없는 음식점 → found=False, suggestions 포함
10. test_execute_cast_vote: 투표 실행 → action="created" + 현황 반환
11. test_execute_record_meal: 기록 실행 → 영양 정보 + 주간 업데이트
12. test_execute_visit_history: 이력 조회 → visits 리스트 반환
13. test_execute_unknown_tool: 존재하지 않는 Tool → error 반환
14. test_resolve_restaurant_fuzzy: "한솥" → "한솥도시락" 매칭

ToolRouter:
15. test_route_recommend: RECOMMEND → get_lunch_recommendations
16. test_route_conditional_category: RECOMMEND_CONDITIONAL + category="한식" → 카테고리 필터
17. test_route_conditional_nutrition: RECOMMEND_CONDITIONAL + "단백질" → diagnosis + recommendations
18. test_route_vote: ACTION_VOTE + restaurant_name → cast_vote
19. test_route_record: ACTION_RECORD + satisfaction=4 → record_meal
20. test_route_followup: FOLLOWUP + number_ref=2 → get_restaurant_info(2번째 음식점)
21. test_route_chitchat: CHITCHAT → 빈 리스트

ToolResultFormatter:
22. test_format_recommendations: 추천 결과 → 순위+이름+점수 텍스트
23. test_format_weather: 날씨 → 기온+하늘+미세먼지 텍스트
24. test_format_nutrition: 진단 → 상태+부족/과다 텍스트
25. test_format_error: success=False → 사용자 친화적 에러 메시지

PromptBasedToolCaller:
26. test_parse_tool_call_single: [TOOL_CALL]...[/TOOL_CALL] 1개 파싱
27. test_parse_tool_call_multiple: [TOOL_CALL] 2개 연속 파싱
28. test_parse_tool_call_invalid: 잘못된 형식 → 빈 리스트
29. test_parse_tool_call_invalid_json: args가 유효한 JSON이 아닌 경우

전체 흐름 (End-to-End):
30. test_e2e_recommend_flow:
    "오늘 뭐 먹지?" 입력 →
    Intent=RECOMMEND →
    ToolRouter=[get_lunch_recommendations] →
    ToolExecutor 실행 →
    ToolFormatter 포맷 →
    ContextBuilder 조립 →
    Ollama mock 응답 →
    최종 응답에 음식점명 포함 확인

31. test_e2e_vote_flow:
    "한솥에 투표할게" 입력 →
    Intent=ACTION_VOTE →
    ToolRouter=[cast_vote] →
    ToolExecutor 실행 →
    DB에 투표 레코드 확인 →
    최종 응답에 "투표 완료" 포함

32. test_e2e_nutrition_query:
    "이번 주 영양 어때?" 입력 →
    Intent=QUERY_NUTRITION →
    진단 결과 반환 →
    "단백질 부족" 등 키워드 포함

33. test_e2e_followup:
    첫 대화에서 5개 추천 받은 후 →
    "2번째 거 상세" 입력 →
    2번째 음식점의 상세 정보 반환

34. test_e2e_fallback_mode:
    Native Tool Calling 비활성화 상태에서
    프롬프트 기반 fallback이 정상 동작하는지

각 테스트에 적절한 mock/fixture 사용.
pytest.mark.parametrize로 다양한 입력 테스트.
```

---

## 12. 트러블슈팅 가이드

**문제 1: Ollama Tool Calling에서 한글 arguments가 깨짐**

```
Ollama의 tool_calls 응답에서 restaurant_name이 한글인데 깨져서 나와.
Ollama가 반환하는 tool_calls의 arguments가 JSON string인 경우
json.loads() 시 encoding 문제가 있을 수 있어.
ensure_ascii=False 설정으로 직렬화/역직렬화를 통일해줘.
```

**문제 2: Tool Calling 무한 루프**

```
LLM이 계속 같은 Tool을 반복 호출하면서 무한 루프에 빠져.
max_iterations=3 제한이 있는데도 같은 Tool을 3번 호출해.
"이미 호출한 Tool은 재호출하지 마세요"라는 규칙을
시스템 프롬프트에 추가하고,
이미 호출된 tool_name을 tracking하여 중복 호출을 코드 레벨에서도 차단해줘.
```

**문제 3: LLM이 Tool을 호출하지 않고 직접 답변함**

```
"오늘 추천해줘"라고 했는데 LLM이 Tool을 호출하지 않고
자기가 만들어낸 가짜 음식점을 추천해.
시스템 프롬프트에 다음 규칙을 강화해줘:
"음식점 정보, 날씨, 영양, 투표 데이터는 반드시 Tool을 통해 조회하세요.
자체적으로 음식점 이름이나 영양 정보를 생성하지 마세요.
Tool 없이는 추천할 수 없다고 안내하세요."

추가로 IntentClassifier + ToolRouter의 규칙 기반 라우팅을
Native Tool Calling보다 우선하는 "Guided Tool Calling" 방식을 적용해줘:
1. IntentClassifier가 RECOMMEND로 분류
2. ToolRouter가 호출할 Tool을 결정
3. Tool을 먼저 실행하여 결과를 확보
4. 결과를 컨텍스트에 포함하여 LLM에게 "이 데이터로 답변 생성해줘"로 요청
이렇게 하면 LLM이 Tool을 호출할지 말지 판단하는 것이 아니라,
시스템이 먼저 Tool을 실행하고 LLM은 결과 해석만 담당하게 돼.
```

**문제 4: 음식점명 매칭 실패**

```
사용자가 "한솥"이라고 줄여서 말하면 "한솥도시락"을 못 찾아.
_resolve_restaurant_name()의 매칭 로직을 강화해줘:
1. 정확 매칭: "한솥도시락" == "한솥도시락"
2. 포함 매칭: "한솥" in "한솥도시락" → True
3. 초성 매칭: "ㅎㅅ" → "한솥" (선택, Phase 3)
4. 퍼지 매칭: fuzzywuzzy ratio > 60
실패 시 유사 음식점 이름을 suggestions에 포함해줘.
```

**문제 5: 쓰기 Tool 실행 후 확인 없이 바로 완료됨**

```
"투표할게"라고만 했는데 어떤 음식점인지 안 물어보고 에러가 나.
쓰기 Tool(cast_vote, record_meal)은 필수 파라미터가 없으면
LLM에게 "어떤 음식점에 투표하시겠어요?"라고 되묻도록 해줘.
ToolRouter에서 필수 파라미터 검증 후,
누락 시 Tool 호출 대신 {"action": "ask_missing", "missing": ["restaurant_name"]}을 반환.
```

---

## 13. 체크리스트

### 구현 완료 확인

```
Phase 2의 구현 상태를 점검해줘.
아래 체크리스트 항목별로 현재 상태를 확인하고,
미완료 항목이 있으면 구현해줘.
```

**Tool 정의:**
- [ ] `tool_definitions.py`에 8개 Tool 스키마 정의
- [ ] 각 Tool의 description이 LLM 판단에 충분히 구체적
- [ ] parameters의 type/enum/required 올바르게 설정
- [ ] `get_tool_by_name`, `get_read_tools`, `get_write_tools` 유틸리티

**Tool Executor:**
- [ ] `_exec_get_lunch_recommendations` → LunchRecommender 연동
- [ ] `_exec_get_current_weather` → WeatherLoader 연동
- [ ] `_exec_get_nutrition_diagnosis` → NutritionDiagnostic 연동
- [ ] `_exec_get_restaurant_info` → RestaurantLoader + NutritionLoader 연동
- [ ] `_exec_cast_vote` → VoteManager 연동 + 투표 시간 검증
- [ ] `_exec_get_vote_status` → VoteManager 연동
- [ ] `_exec_record_meal` → MealTracker + VisitTracker 연동
- [ ] `_exec_get_visit_history` → VisitTracker 연동
- [ ] `_resolve_restaurant_name` 퍼지 매칭 (정확/포함/fuzzy)
- [ ] 각 Tool 실행 시간 측정 및 로깅
- [ ] 파이프라인 미구현 시 mock fallback 동작

**Tool Router:**
- [ ] 12가지 Intent → Tool 매핑 규칙 정의
- [ ] 조건부 추천 시 다중 Tool 순차 호출 (diagnosis → recommendations)
- [ ] FOLLOWUP 시 이전 추천 결과에서 음식점명 추출
- [ ] 필수 파라미터 누락 시 되묻기 처리
- [ ] user_id/team_id 자동 주입

**Tool Calling 루프:**
- [ ] Native Function Calling 모드 동작 (Qwen3.5/Gemma4)
- [ ] tool_calls 응답 파싱 → Tool 실행 → 결과 재주입 → 재호출
- [ ] 최대 3회 반복 제한
- [ ] 중복 Tool 호출 방지

**Fallback:**
- [ ] 프롬프트 기반 Tool 프롬프트 (`tool_prompt.md`)
- [ ] `[TOOL_CALL]...[/TOOL_CALL]` 파싱 (정규식)
- [ ] `[TOOL_RESULT]` 형식 결과 주입
- [ ] 모델별 자동 방식 전환 (`should_use_fallback`)

**Formatter:**
- [ ] 8개 Tool별 포맷 함수 구현
- [ ] 에러 결과 사용자 친화적 변환
- [ ] 다중 결과 합산 (`format_multiple`)

**Context Builder:**
- [ ] Tool 결과 기반 동적 컨텍스트 조립
- [ ] 읽기 Tool 결과 → 추천/조회 컨텍스트
- [ ] 쓰기 Tool 결과 → 행동 완료 컨텍스트
- [ ] 토큰 수 초과 시 자동 요약

**API/UI:**
- [ ] POST /api/chat 응답에 metadata (tools_used, time_ms)
- [ ] SSE에 tool_start/tool_done/thinking 이벤트 추가
- [ ] React: Tool 실행 중 로딩 인디케이터
- [ ] React: RestaurantCard 컴포넌트 (투표/상세 버튼)

**테스트:**
- [ ] Tool Definitions 테스트 4건
- [ ] ToolExecutor 테스트 10건
- [ ] ToolRouter 테스트 7건
- [ ] ToolFormatter 테스트 4건
- [ ] ToolFallback 테스트 4건
- [ ] E2E 통합 테스트 5건
- [ ] 전체 테스트 통과 (`pytest tests/ -v`)

---

<div align="center">

**8개 Tool이 연결되면, 챗봇은 진짜 데이터로 말합니다.**

*"오늘 뭐 먹지?" → 파이프라인 4개 가동 → 맞춤 추천 완성*

*다음 단계: Phase 3 — 멀티턴 대화 고도화 + 개인화*

</div>
