# 🚀 Phase 1: 점심 추천 챗봇 구현 — Claude Code 가이드라인

> ⚠️ **Track A (Streamlit) 완전 제거됨** — 구현 대상에서 삭제.
>
> ⚠️ **Ollama 제거됨 → 외부 LLM API 로 전환**:
> - 기본: `gemini-2.5-flash` (Google)
> - 대안 A: `gpt-4o-mini` (OpenAI)
> - 대안 B: `claude-haiku-3-5` (Anthropic)
>
> ChatBOT 은 **선택적 추가 기능** 이며, **메인 언어 처리 축은 [`../NLP/`](../NLP/README.md)** 입니다.
> Phase 1 은 NLP MVP Step 1~4 완료 후 착수 권장.
>
> ---
>
> **목표**: Gemini 2.5 Flash 기반 점심 추천 챗봇을 **React + FastAPI** 로 구현합니다.
> **Track B (React + FastAPI)** 단일 경로로 진행 ✅

---

## 📋 목차

1. [사전 준비 및 LLM API 설정](#1-사전-준비-및-llm-api-설정)
2. [프로젝트 구조](#2-프로젝트-구조)
3. [Step 1 — 챗봇 코어 엔진](#3-step-1--챗봇-코어-엔진)
4. [Step 2 — LLM API 클라이언트 (멀티 프로바이더)](#4-step-2--llm-api-클라이언트-멀티-프로바이더)
5. [Step 3 — Tool Functions 래퍼](#5-step-3--tool-functions-래퍼)
6. [Step 4 — FastAPI 채팅 백엔드](#6-step-4--fastapi-채팅-백엔드)
7. [Step 5 — React 채팅 프론트엔드](#7-step-5--react-채팅-프론트엔드)
8. [Step 6 — 테스트 및 검증](#8-step-6--테스트-및-검증)
9. [트러블슈팅 가이드](#9-트러블슈팅-가이드)
10. [체크리스트](#10-체크리스트)

---

## 1. 사전 준비 및 LLM API 설정

### 1.1 API 키 발급

| 프로바이더 | 발급 URL | 무료 티어 |
|-----------|---------|---------|
| **Gemini** (기본) | https://aistudio.google.com/apikey | ✅ 있음 |
| OpenAI (대안 A) | https://platform.openai.com/api-keys | ❌ 없음 |
| Claude (대안 B) | https://console.anthropic.com/ | ❌ 없음 |

### 1.2 환경변수 설정

```bash
# env.env 파일에 설정 (사용할 프로바이더 하나 이상 필수)
GEMINI_API_KEY=your-gemini-api-key
OPENAI_API_KEY=your-openai-api-key      # 선택
ANTHROPIC_API_KEY=your-anthropic-api-key # 선택

# 사용할 프로바이더 지정
LLM_PROVIDER=gemini          # gemini | openai | claude
LLM_MODEL=gemini-2.5-flash   # 각 프로바이더의 모델명

CHATBOT_MAX_HISTORY=10
CHATBOT_SYSTEM_PROMPT_PATH=chatbot/prompts/system.md
```

### 1.3 패키지 설치 및 연결 확인

```bash
# 패키지 설치
pip install google-genai openai anthropic python-dotenv

# requirements.txt에 추가할 항목
# google-genai>=1.0.0
# openai>=1.0.0
# anthropic>=0.25.0
# python-dotenv==1.0.1

# 연결 확인 스크립트 실행
python scripts/check_llm_api.py
```

### 1.4 Claude Code 프롬프트 — 환경 설정

```
프로젝트 루트에 chatbot 관련 의존성을 추가해줘.

requirements.txt에 추가:
- google-genai>=1.0.0
- openai>=1.0.0
- anthropic>=0.25.0
- python-dotenv==1.0.1

env.env.example에 추가:
- GEMINI_API_KEY=
- OPENAI_API_KEY=
- ANTHROPIC_API_KEY=
- LLM_PROVIDER=gemini
- LLM_MODEL=gemini-2.5-flash
- CHATBOT_MAX_HISTORY=10

API 연결을 확인하는 스크립트를 만들어줘:
scripts/check_llm_api.py
- 설정된 LLM_PROVIDER에 따라 API 연결 확인
- 간단한 테스트 메시지 전송 ("안녕, 오늘 점심 추천해줘")
- 응답 시간 측정
- 3개 프로바이더 모두 키가 있으면 순서대로 테스트
```

---

## 2. 프로젝트 구조

### Claude Code 프롬프트

```
기존 lunch-optimizer 프로젝트에 챗봇 관련 디렉토리를 추가해줘.

추가할 구조:
lunch-optimizer/
├── chatbot/
│   ├── __init__.py
│   ├── core.py                  # 챗봇 메인 로직
│   ├── llm_client.py            # LLM API 클라이언트 (멀티 프로바이더)
│   ├── tools.py                 # Tool Functions 래퍼
│   ├── intent.py                # Intent 분류기
│   ├── context_builder.py       # RAG 컨텍스트 조립
│   ├── history.py               # 대화 히스토리 관리
│   └── prompts/
│       └── system.md            # 시스템 프롬프트
│
├── ui/
│   └── react-chat/              # React 프론트엔드
│       ├── package.json
│       ├── src/
│       │   ├── App.jsx
│       │   ├── components/
│       │   │   ├── ChatWindow.jsx
│       │   │   ├── MessageBubble.jsx
│       │   │   ├── InputBar.jsx
│       │   │   ├── QuickActions.jsx
│       │   │   └── RestaurantCard.jsx
│       │   ├── hooks/
│       │   │   └── useChat.js
│       │   └── services/
│       │       └── chatApi.js
│       └── index.html
│
├── api/
│   └── chat_router.py           # FastAPI 채팅 엔드포인트
│
├── tests/
│   ├── test_chatbot_core.py
│   ├── test_llm_client.py
│   └── test_tools.py
│
└── scripts/
    └── check_llm_api.py
```

---

## 4. Step 1 — 챗봇 코어 엔진 (공통)

### 4.1 시스템 프롬프트 파일

```
chatbot/prompts/system.md를 작성해줘.

아래 내용을 포함하되, 마크다운 파일로 저장해서
Python에서 읽어와 사용하는 구조로 만들어줘:

---
당신은 "점심 도우미"입니다. 직장인 팀의 점심 식사를 도와주는 친근한 AI 어시스턴트입니다.

## 역할
- 오늘의 날씨, 사용자의 영양 상태, 팀원들의 투표를 종합하여 최적의 점심을 추천합니다
- 투표, 식사 기록, 거부권 등의 행동을 대화로 수행할 수 있게 돕습니다
- 한국어로 친근하게 답변하되, 중요한 정보는 빠뜨리지 않습니다

## 행동 규칙
1. 추천 시 반드시 종합 점수와 추천 이유를 함께 제공하세요
2. 영양 조언은 권고 수준으로, 의학적 진단은 하지 마세요
3. 투표/기록 등의 행동은 사용자의 명시적 요청 시에만 실행하세요
4. 이전 대화 맥락을 기억하고, 대명사("그거", "거기")를 이해하세요
5. 답변은 간결하게 하되 이모지를 적절히 사용하세요
6. 음식점 추천은 최대 5개까지만 제공하세요
7. 점심과 무관한 질문에는 부드럽게 점심 주제로 유도하세요

## 응답 형식
- 추천 시: 순위 + 음식점명 + 거리 + 한줄 이유
- 정보 조회 시: 핵심 수치 + 간단한 해석
- 행동 실행 시: 완료 확인 + 현재 상태 요약
---
```

### 4.2 Intent 분류기

```
chatbot/intent.py를 구현해줘.

IntentClassifier 클래스:

사용자 메시지를 분석하여 Intent를 분류하는 역할이야.
Phase 1에서는 LLM 호출 없이 키워드 규칙 기반으로 분류하고,
Phase 2에서 LLM 기반으로 업그레이드할 수 있는 구조로 설계해줘.

Intent 유형 (Enum으로 정의):
- RECOMMEND: 점심 추천 요청
- RECOMMEND_CONDITIONAL: 조건부 추천 (날씨, 영양, 카테고리 등)
- QUERY_RESTAURANT: 특정 음식점 정보 조회
- QUERY_WEATHER: 날씨 정보 조회
- QUERY_NUTRITION: 영양 상태 조회
- QUERY_VOTE: 투표 현황 조회
- QUERY_HISTORY: 방문 이력 조회
- ACTION_VOTE: 투표 실행
- ACTION_RECORD: 식사 기록 실행
- ACTION_VETO: 거부권 실행
- FOLLOWUP: 이전 대화 참조 ("2번째 거", "그거 말고")
- CHITCHAT: 일반 대화 / 인사

classify(message: str) -> dict:
  반환:
  {
    "intent": Intent.RECOMMEND_CONDITIONAL,
    "confidence": 0.9,
    "entities": {
      "category": "한식",          # 추출된 카테고리 (있으면)
      "restaurant_name": None,     # 추출된 음식점명 (있으면)
      "condition": "비 오는 날",    # 추출된 조건 (있으면)
      "number_ref": None,          # "2번째" 같은 숫자 참조 (있으면)
      "satisfaction": None,        # 만족도 점수 (있으면)
    }
  }

키워드 규칙 예시:
- "추천", "뭐 먹", "뭐 먹을", "점심", "메뉴" → RECOMMEND
- "추천" + ("한식"|"일식"|"양식"|"가까운"|"단백질"|"비"|"따뜻") → RECOMMEND_CONDITIONAL
- "투표", "한 표" + 음식점명 → ACTION_VOTE
- "먹었어", "기록", "점 줄게" + 음식점명 → ACTION_RECORD
- "날씨", "비", "미세먼지", "기온" → QUERY_WEATHER
- "영양", "칼로리", "단백질", "이번 주" → QUERY_NUTRITION
- "투표 현황", "누가 투표" → QUERY_VOTE
- "최근", "지난번", "히스토리" → QUERY_HISTORY
- "1번", "2번째", "그거", "다른 거" → FOLLOWUP
- "안녕", "고마워", "ㅋㅋ" → CHITCHAT

음식점명 추출은 DB에서 음식점 이름 목록을 로드한 후
메시지에서 매칭하는 방식으로 구현해줘.

타입 힌트, docstring, 로깅 포함해줘.
```

### 4.3 대화 히스토리 관리

```
chatbot/history.py를 구현해줘.

ChatHistory 클래스:

1. __init__(self, max_turns: int = 10):
   최대 저장 턴 수 설정

2. add_user_message(content: str) -> None:
   사용자 메시지 추가

3. add_assistant_message(content: str) -> None:
   어시스턴트 응답 추가

4. add_tool_result(tool_name: str, result: dict) -> None:
   Tool 호출 결과를 내부적으로 저장 (LLM에게 전달용)

5. get_messages() -> list[dict]:
   Ollama API 형식의 메시지 리스트 반환
   [{"role": "system", "content": "..."},
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}]

6. get_last_recommendations() -> list[dict] | None:
   가장 최근 추천 결과를 반환 (FOLLOWUP 처리용)

7. trim(max_turns: int = None) -> None:
   시스템 프롬프트는 유지하면서 오래된 대화만 삭제

8. clear() -> None:
   대화 히스토리 초기화 (시스템 프롬프트 유지)

9. get_token_estimate() -> int:
   대략적인 토큰 수 추정 (한글 1글자 ≈ 2토큰 기준)
   4096 토큰 초과 시 자동 trim 트리거

타입 힌트 포함해줘.
```

### 4.4 컨텍스트 빌더

```
chatbot/context_builder.py를 구현해줘.

ContextBuilder 클래스:

이 클래스는 사용자의 Intent에 따라 필요한 데이터를 파이프라인 DB에서 조회하고,
LLM에게 전달할 컨텍스트 문자열을 조립하는 역할이야.

1. build_context(intent: dict, user_id: str, team_id: str) -> str:
   Intent에 따라 필요한 데이터만 선택적으로 조회하여 컨텍스트 생성.

   RECOMMEND/RECOMMEND_CONDITIONAL:
   - 현재 날씨 요약 (1줄)
   - 사용자 영양 상태 요약 (1줄)
   - 팀 투표 현황 요약 (1줄)
   - TOP 5 추천 음식점 목록 (JSON 형식)

   QUERY_WEATHER:
   - 상세 날씨 정보 + 점심 팁

   QUERY_NUTRITION:
   - 주간 영양 진단 결과 전체

   QUERY_VOTE:
   - 상세 투표 현황 (팀원별)

   QUERY_RESTAURANT:
   - 해당 음식점 상세 정보 + 영양 정보

   CHITCHAT / FOLLOWUP:
   - 컨텍스트 불필요, 빈 문자열 반환

2. _format_recommendations(recommendations: list[dict]) -> str:
   추천 결과를 LLM이 이해하기 쉬운 텍스트로 포맷팅.
   예:
   "[추천 데이터]
   1. 명동칼국수 | 320m | 종합82점 | 날씨75 영양68 팀85 | 한식/국물 | 550kcal
   2. 서브웨이 | 180m | 종합78점 | 날씨60 영양82 팀65 | 양식/샌드위치 | 380kcal
   ..."

   LLM은 이 데이터를 기반으로 자연어 응답을 생성함.
   데이터만 전달하고 응답 형식은 LLM에게 맡기는 것이 핵심.

3. build_system_prompt(user_name: str, team_name: str) -> str:
   system.md를 읽어와 동적 변수(날짜, 시각, 사용자명)를 치환.

파이프라인 DB 조회는 기존 소주제 1~4의 loader/scorer 클래스를 import해서 사용.
조회 실패 시 graceful fallback (해당 축 데이터 없이 진행).
타입 힌트, docstring, 로깅 포함해줘.
```

---

## 4. Step 2 — LLM API 클라이언트 (멀티 프로바이더)

### Claude Code 프롬프트

```
chatbot/llm_client.py를 구현해줘.

환경변수 LLM_PROVIDER (gemini | openai | claude) 에 따라
자동으로 적절한 클라이언트를 선택하는 멀티 프로바이더 구조로 만들어줘.

─────────────────────────────────────
BaseLLMClient (추상 기반 클래스):
─────────────────────────────────────
공통 인터페이스 정의.

1. chat(messages: list[dict], tools: list = None) -> str:
   메시지 전송 및 전체 응답 반환.

2. chat_stream(messages: list[dict]) -> Generator[str, None, None]:
   스트리밍 모드. 토큰 단위로 yield.
   React SSE와 호환되는 형식.

3. is_available() -> bool:
   API 키 유효성 및 연결 확인.

─────────────────────────────────────
GeminiClient(BaseLLMClient):  ← 기본
─────────────────────────────────────
google-genai SDK 사용.

__init__:
  GEMINI_API_KEY, LLM_MODEL (기본 gemini-2.5-flash) 로드.
  google.genai.Client 초기화.

chat(messages, tools=None):
  messages를 Gemini 형식(types.Content)으로 변환.
  tools가 있으면 types.Tool로 래핑하여 전달.
  tool_calls 응답이 있으면 재귀적으로 처리 후 최종 텍스트 반환.

chat_stream(messages):
  client.models.generate_content_stream() 사용.
  각 청크의 text를 yield.

_convert_messages(messages: list[dict]) -> list[types.Content]:
  {"role": "user", "content": "..."} 형식을
  types.Content(role="user", parts=[types.Part(text="...")]) 로 변환.
  role="system"은 config의 system_instruction으로 분리.
  role="tool"은 types.Part(function_response=...) 로 변환.

─────────────────────────────────────
OpenAIClient(BaseLLMClient):  ← 대안 A
─────────────────────────────────────
openai SDK 사용.

__init__:
  OPENAI_API_KEY, LLM_MODEL (기본 gpt-4o-mini) 로드.
  openai.OpenAI 클라이언트 초기화.

chat(messages, tools=None):
  client.chat.completions.create() 호출.
  tools가 있으면 OpenAI tool_choice="auto" 모드.
  tool_calls 응답 처리 후 최종 텍스트 반환.

chat_stream(messages):
  stream=True 옵션 사용.
  delta.content 를 yield.

─────────────────────────────────────
ClaudeClient(BaseLLMClient):  ← 대안 B
─────────────────────────────────────
anthropic SDK 사용.

__init__:
  ANTHROPIC_API_KEY, LLM_MODEL (기본 claude-haiku-3-5-20251001) 로드.
  anthropic.Anthropic 클라이언트 초기화.

chat(messages, tools=None):
  client.messages.create() 호출.
  system 메시지 분리 처리 (Claude는 system 파라미터 별도).
  tool_use 블록 처리.

chat_stream(messages):
  with client.messages.stream() 사용.
  text_stream 이터레이터로 yield.

─────────────────────────────────────
get_llm_client() -> BaseLLMClient:  ← 팩토리 함수
─────────────────────────────────────
LLM_PROVIDER 환경변수에 따라 적절한 클라이언트 반환.
기본값: GeminiClient.

사용 예:
  client = get_llm_client()
  response = client.chat(messages, tools=TOOLS)

에러 처리:
- API 키 미설정 시 → "GEMINI_API_KEY 환경변수를 설정해주세요" 명확한 안내
- Rate limit (429) → 지수 백오프 재시도 (최대 3회)
- 타임아웃 (30초) → 재시도 1회 후 실패
- 각 프로바이더의 에러를 통일된 LLMError 예외로 래핑

로깅: 프로바이더명, 모델명, 응답 시간(ms), 토큰 사용량 로깅.
타입 힌트, docstring 포함해줘.
```

---

## 6. Step 3 — Tool Functions 래퍼 (공통)

### Claude Code 프롬프트

```
chatbot/tools.py를 구현해줘.

이 파일은 기존 소주제 1~4의 코드를 챗봇용 Tool Function으로 래핑하는 역할이야.

TOOL_DEFINITIONS: list[dict]
  Ollama에게 전달할 tool 정의 목록.
  각 tool의 name, description, parameters를 정의.
  (이전 상세 계획서의 8개 Tool 정의를 그대로 사용)

ToolExecutor 클래스:

1. __init__(self, session):
   DB 세션을 받아 각 소주제의 loader/scorer를 초기화.

2. execute(tool_name: str, arguments: dict) -> dict:
   tool_name에 해당하는 함수를 실행하고 결과를 dict로 반환.

   라우팅:
   - "get_lunch_recommendations" → LunchRecommender.get_recommendations()
   - "get_current_weather" → WeatherLoader.get_latest_weather()
   - "get_nutrition_diagnosis" → NutritionDiagnostic.diagnose_weekly()
   - "get_restaurant_info" → RestaurantLoader + NutritionLoader 조합
   - "cast_vote" → VoteManager.cast_vote()
   - "get_vote_status" → VoteManager.get_current_status()
   - "record_meal" → MealTracker.record_meal()
   - "get_visit_history" → VisitTracker.get_recent_visits()

   반환 dict는 LLM이 이해할 수 있는 평문 형식으로 변환.
   예: {"result": "투표 완료", "details": {"restaurant": "한솥", "total_votes": 3}}

3. _format_for_llm(tool_name: str, raw_result: any) -> dict:
   각 Tool의 raw 결과를 LLM 친화적 dict로 변환.
   복잡한 객체는 핵심 필드만 추출하여 평탄화.

4. get_tool_definitions() -> list[dict]:
   TOOL_DEFINITIONS 반환.

각 Tool 실행 시 에러가 발생하면:
- 에러를 로깅하고
- {"error": "음식점 정보를 조회할 수 없습니다"} 형태로 반환
- LLM이 에러 메시지를 자연어로 전달하도록 함

타입 힌트, docstring, 로깅 포함해줘.
```

### 챗봇 코어 조립

```
chatbot/core.py를 구현해줘.

LunchChatbot 클래스:
이 파일이 모든 컴포넌트를 조립하는 메인 클래스야.

1. __init__(self, user_id: str, team_id: str):
   - OllamaChat 초기화
   - ChatHistory 초기화 (시스템 프롬프트 로드)
   - ContextBuilder 초기화
   - IntentClassifier 초기화
   - ToolExecutor 초기화
   - DB 세션 생성

2. chat(user_message: str) -> str:
   전체 챗봇 파이프라인 실행 (비스트리밍).

   흐름:
   a. 사용자 메시지를 히스토리에 추가
   b. Intent 분류
   c. Intent에 따라 Context 빌드
   d. Context를 포함한 메시지 리스트 구성
   e. Ollama 호출
   f. Tool Call이 있으면 실행 후 재호출
   g. 최종 응답을 히스토리에 추가
   h. 응답 반환

3. chat_stream(user_message: str) -> Generator[str, None, None]:
   스트리밍 버전의 chat.
   Streamlit과 FastAPI SSE 양쪽에서 사용.
   
   주의: 스트리밍 모드에서는 Tool Calling이 어려우므로,
   Tool 실행은 스트리밍 시작 전에 완료하고,
   Tool 결과를 컨텍스트에 포함한 상태에서 스트리밍 시작.

   흐름:
   a~d: chat()과 동일
   e. Tool이 필요하면 비스트리밍으로 먼저 실행
   f. Tool 결과를 컨텍스트에 추가
   g. 최종 응답을 스트리밍으로 생성
   h. 전체 응답을 히스토리에 추가

4. reset() -> None:
   대화 초기화.

타입 힌트, docstring, 로깅 포함해줘.
```

---

## 7. Step 4A — Streamlit 채팅 UI

### Claude Code 프롬프트

```
ui/streamlit_app.py를 구현해줘.

Streamlit 채팅 인터페이스를 구현해줘. st.chat_input과 st.chat_message를 사용.

구조:
1. 페이지 설정:
   - page_title="오늘 뭐 먹지?"
   - page_icon="🍱"
   - layout="wide"

2. 사이드바:
   - 사용자 선택 (selectbox: 팀원 5명)
   - 모델 선택 (selectbox: qwen3.5:7b, gemma4, gemma4:26b)
   - Ollama 연결 상태 표시 (녹색/빨간색 인디케이터)
   - "대화 초기화" 버튼
   - 현재 날씨 요약 카드
   - 오늘 투표 현황 미니 카드

3. 메인 영역:
   - 제목: "🍱 오늘 뭐 먹지?"
   - 부제: "점심 추천 챗봇 — 날씨·영양·팀 투표 통합"

4. 빠른 액션 버튼 (st.columns 4개):
   - 🍽️ "오늘 추천" → "오늘 점심 추천해줘"
   - 🗳️ "투표현황" → "투표 현황 알려줘"
   - 📊 "영양리포트" → "이번 주 영양 상태 알려줘"
   - 🌤️ "날씨" → "오늘 날씨 어때?"

5. 채팅 영역:
   - st.session_state.messages로 히스토리 관리
   - st.chat_message("user") / st.chat_message("assistant")
   - 어시스턴트 응답은 st.write_stream으로 스트리밍 표시

6. 입력:
   - st.chat_input("점심에 대해 뭐든 물어보세요!")

세션 상태 관리:
- st.session_state.chatbot: LunchChatbot 인스턴스
- st.session_state.messages: 표시용 메시지 히스토리
- st.session_state.user_id: 선택된 사용자
- st.session_state.team_id: 팀 ID

에러 처리:
- Ollama 미연결 시 경고 배너 표시
- 모델 미다운로드 시 설치 명령어 안내

실행 명령어:
streamlit run ui/streamlit_app.py --server.port 8501
```

---

## 8. Step 4B — FastAPI 채팅 백엔드

### Claude Code 프롬프트

```
api/chat_router.py를 구현해줘.

FastAPI 라우터로 채팅 API 엔드포인트를 구현해줘.
기존 api/main.py에 이 라우터를 include하는 구조.

1. POST /api/chat
   일반 채팅 (비스트리밍).
   Body: {"user_id": "user1", "team_id": "team1", "message": "오늘 뭐 먹지?"}
   Response: {"reply": "...", "intent": "RECOMMEND", "tool_used": ["get_lunch_recommendations"]}

2. GET /api/chat/stream
   SSE 스트리밍 채팅.
   Query: message, user_id, team_id
   Response: text/event-stream
   
   각 이벤트 형식:
   data: {"type": "token", "content": "오"}
   data: {"type": "token", "content": "늘"}
   data: {"type": "token", "content": "은"}
   ...
   data: {"type": "done", "content": "", "metadata": {"intent": "RECOMMEND", "tokens": 245, "time_ms": 3200}}

   구현:
   from fastapi.responses import StreamingResponse

   async def stream_chat(message: str, user_id: str, team_id: str):
       chatbot = get_or_create_chatbot(user_id, team_id)
       
       async def event_generator():
           for token in chatbot.chat_stream(message):
               yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
           yield f"data: {json.dumps({'type': 'done', 'content': ''})}\n\n"
       
       return StreamingResponse(
           event_generator(),
           media_type="text/event-stream",
           headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
       )

3. POST /api/chat/reset
   대화 초기화.
   Body: {"user_id": "user1", "team_id": "team1"}

4. GET /api/chat/health
   Ollama 연결 상태 + 모델 정보 반환.

세션 관리:
- user_id + team_id 조합으로 chatbot 인스턴스를 딕셔너리로 관리
- 30분 미사용 시 자동 정리 (메모리 관리)

CORS 설정 (React 프론트엔드 연동):
- allow_origins=["http://localhost:5173", "http://localhost:3000"]

api/main.py에 chat_router를 include하는 코드도 추가해줘:
app.include_router(chat_router, prefix="/api/chat", tags=["Chat"])
```

---

## 9. Step 5B — React 채팅 프론트엔드

### 9.1 프로젝트 초기화 프롬프트

```
ui/react-chat 디렉토리에 React 채팅 프론트엔드를 초기화해줘.

Vite + React + Tailwind CSS를 사용해줘.
기존 대시보드(lunch-optimizer-dashboard.jsx)와
동일한 디자인 시스템을 사용하되, 채팅 전용 UI를 만들어줘.

초기화 명령어:
cd ui/react-chat
npm create vite@latest . -- --template react
npm install
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p

추가 패키지:
npm install react-markdown lucide-react
```

### 9.2 채팅 API 서비스 프롬프트

```
ui/react-chat/src/services/chatApi.js를 구현해줘.

FastAPI 백엔드와 통신하는 API 서비스 모듈.

const API_BASE = "http://localhost:8000/api/chat";

1. sendMessage(message, userId, teamId) → Promise<string>:
   POST /api/chat 호출. 전체 응답 반환.

2. streamMessage(message, userId, teamId, onToken, onDone):
   GET /api/chat/stream을 fetch로 호출.
   ReadableStream으로 SSE 파싱하여 토큰 단위 콜백.

   구현:
   const response = await fetch(
     `${API_BASE}/stream?message=${encodeURIComponent(message)}&user_id=${userId}&team_id=${teamId}`
   );
   const reader = response.body.getReader();
   const decoder = new TextDecoder();
   
   while (true) {
     const { done, value } = await reader.read();
     if (done) break;
     
     const text = decoder.decode(value);
     const lines = text.split("\n\n").filter(l => l.startsWith("data: "));
     
     for (const line of lines) {
       const data = JSON.parse(line.replace("data: ", ""));
       if (data.type === "token") onToken(data.content);
       if (data.type === "done") onDone(data.metadata);
     }
   }

3. resetChat(userId, teamId):
   POST /api/chat/reset 호출.

4. checkHealth() → Promise<{status, model, available}>:
   GET /api/chat/health 호출.
```

### 9.3 커스텀 훅 프롬프트

```
ui/react-chat/src/hooks/useChat.js를 구현해줘.

React 커스텀 훅으로 채팅 상태 관리.

export function useChat(userId, teamId) {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingText, setStreamingText] = useState("");
  const [error, setError] = useState(null);

  const sendMessage = async (text) => {
    // 1. 사용자 메시지 추가
    // 2. isStreaming = true
    // 3. streamMessage 호출
    //    - onToken: streamingText에 누적
    //    - onDone: 최종 메시지를 messages에 추가, isStreaming = false
  };

  const resetChat = async () => { ... };

  return { messages, isLoading, isStreaming, streamingText, error, sendMessage, resetChat };
}
```

### 9.4 메인 채팅 컴포넌트 프롬프트

```
ui/react-chat/src/App.jsx를 구현해줘.

전체 채팅 UI를 구현해줘. 다음 컴포넌트로 구성:

1. ChatWindow (메인 컨테이너):
   - 최대 너비 800px, 중앙 정렬
   - 헤더: "🍱 오늘 뭐 먹지?" + Ollama 연결 상태 인디케이터
   - 메시지 영역: 스크롤 가능, 하단 자동 스크롤
   - 입력 바: 하단 고정

2. MessageBubble:
   - 사용자 메시지: 우측 정렬, 배경색 구분
   - 어시스턴트 메시지: 좌측 정렬, 아바타 "🍱"
   - 마크다운 렌더링 지원 (react-markdown)
   - 스트리밍 중: 커서 깜빡임 애니메이션

3. InputBar:
   - 텍스트 입력 (Enter로 전송, Shift+Enter로 줄바꿈)
   - 전송 버튼 (Send 아이콘)
   - 스트리밍 중에는 입력 비활성화 + "응답 중..." 표시

4. QuickActions:
   - 대화가 비어있을 때만 표시
   - 4개 버튼: "오늘 추천", "투표현황", "영양리포트", "날씨"
   - 클릭 시 해당 메시지를 자동 전송

5. RestaurantCard (선택, Phase 2):
   - 어시스턴트가 음식점을 추천했을 때 카드 형태로 표시
   - 음식점명, 거리, 점수, 카테고리 배지

디자인:
- Tailwind CSS 사용
- 다크모드 지원 (prefers-color-scheme)
- 모바일 반응형 (max-w-full, 패딩 조정)
- 색상: 사용자 버블 teal, 어시스턴트 버블 gray
- 폰트: Pretendard (구글 폰트 CDN)

실행: npm run dev (포트 5173)
```

---

## 10. Step 5/6 — 테스트 및 검증

### Claude Code 프롬프트

```
tests/test_chatbot_core.py에 챗봇 통합 테스트를 작성해줘.

Ollama는 mock으로 처리하고, 파이프라인 DB는 인메모리 SQLite 사용.

테스트 케이스:

IntentClassifier:
1. test_intent_recommend_basic: "오늘 뭐 먹지?" → RECOMMEND
2. test_intent_recommend_conditional: "비 오는데 추천" → RECOMMEND_CONDITIONAL, condition="비"
3. test_intent_action_vote: "한솥에 투표" → ACTION_VOTE, restaurant_name="한솥도시락"
4. test_intent_action_record: "서브웨이 먹었어 4점" → ACTION_RECORD, satisfaction=4
5. test_intent_query_nutrition: "이번 주 영양 어때?" → QUERY_NUTRITION
6. test_intent_followup: "2번째 거로 할게" → FOLLOWUP, number_ref=2
7. test_intent_chitchat: "안녕" → CHITCHAT

OllamaChat:
8. test_chat_basic: mock 응답이 올바르게 반환되는지
9. test_chat_stream: 스트리밍 응답이 토큰 단위로 yield되는지
10. test_connection_error: 서버 미연결 시 에러 메시지

LunchChatbot (통합):
11. test_full_recommend_flow: "추천해줘" → 컨텍스트 빌드 → LLM 호출 → 응답
12. test_full_vote_flow: "한솥 투표" → Tool 실행 → DB 저장 → 응답
13. test_history_management: 10턴 이상 대화 후 trim 확인

Ollama mock fixture:
def mock_ollama_response(content="테스트 응답입니다"):
    return {"message": {"role": "assistant", "content": content}}
```

### 실행 확인 프롬프트

```
전체 챗봇 시스템을 실행하고 동작을 확인해줘.

1. Ollama 서버 확인: curl http://localhost:11434/api/tags
2. 테스트 실행: pytest tests/test_chatbot_core.py -v
3. Streamlit 실행: streamlit run ui/streamlit_app.py
4. FastAPI 실행: uvicorn api.main:app --reload --port 8000
5. React 실행: cd ui/react-chat && npm run dev

각 단계에서 문제가 있으면 원인을 분석하고 수정해줘.
최종적으로 "오늘 뭐 먹지?"를 입력했을 때 추천 응답이 나오는지 확인해줘.
```

---

## 11. 트러블슈팅 가이드

**문제 1: Ollama 스트리밍에서 한글이 깨짐**

```
Ollama 스트리밍 응답에서 한글이 깨져서 나와.
UTF-8 멀티바이트 문자가 토큰 경계에서 잘리는 문제일 수 있어.
TextDecoder를 "utf-8"로 명시하고,
불완전한 바이트가 있으면 다음 chunk와 합쳐서 디코딩하는 로직을 추가해줘.
```

**문제 2: React SSE에서 CORS 에러**

```
React에서 FastAPI의 /stream 엔드포인트를 호출하면 CORS 에러가 발생해.
FastAPI의 CORSMiddleware 설정을 확인하고,
SSE 응답의 헤더에 Access-Control-Allow-Origin을 추가해줘.
또한 Vite의 프록시 설정으로 개발 환경에서 CORS를 우회하는 방법도 알려줘.
```

**문제 3: Tool Calling이 모델에서 지원 안 됨**

```
사용 중인 Ollama 모델이 tool/function calling을 지원하지 않아.
Tool Calling 대신 "프롬프트 기반 Tool 실행" 방식으로 전환해줘:
1. 시스템 프롬프트에 Tool 목록과 호출 형식을 텍스트로 정의
2. LLM 응답에서 [TOOL: tool_name(args)] 패턴을 정규식으로 파싱
3. 파싱된 Tool을 실행하고 결과를 컨텍스트에 추가하여 재호출
이 방식이면 어떤 모델이든 Tool 실행이 가능해.
```

**문제 4: Streamlit 세션 간 상태 공유 안 됨**

```
Streamlit에서 다른 사용자가 투표한 결과가 내 화면에 반영이 안 돼.
Streamlit의 session_state는 각 브라우저 세션에 독립이라서 그래.
투표 데이터는 DB에서 직접 조회하도록 하고,
session_state에는 UI 상태(대화 히스토리)만 저장하도록 분리해줘.
```

**문제 5: LLM 응답이 너무 길거나 형식이 안 맞음**

```
LLM이 너무 긴 응답을 생성하거나 원하는 형식을 따르지 않아.
시스템 프롬프트에 다음 제약을 추가해줘:
- "응답은 300자 이내로 간결하게 작성하세요"
- "음식점 목록은 번호+이름+거리+한줄이유 형식으로 작성하세요"
- "불필요한 인사말이나 반복 표현을 피하세요"
또한 Ollama 호출 시 num_predict 파라미터로 최대 토큰 수를 제한해줘.
```

---

## 12. 체크리스트

### 구현 완료 확인

```
Phase 1 챗봇의 구현 상태를 점검해줘.
아래 체크리스트 항목별로 현재 상태를 확인하고,
미완료 항목이 있으면 구현해줘.
```

**공통 코어:**
- [ ] Ollama 설치 및 모델 다운로드 완료
- [ ] `scripts/check_ollama.py` 실행 시 연결 성공
- [ ] `chatbot/prompts/system.md` 시스템 프롬프트 작성
- [ ] `IntentClassifier`가 12가지 Intent를 분류 (키워드 기반)
- [ ] 음식점명 추출 (DB 목록 기반 매칭)
- [ ] `ChatHistory`의 add/get/trim 동작
- [ ] 토큰 추정 및 자동 trim (4096 초과 시)
- [ ] `ContextBuilder`가 Intent별 필요 데이터만 선택 조회
- [ ] 추천 데이터의 LLM 친화적 포맷팅
- [ ] `OllamaChat.chat()` 비스트리밍 호출 동작
- [ ] `OllamaChat.chat_stream()` 스트리밍 호출 동작
- [ ] 서버 미연결 시 사용자 친화적 에러 메시지
- [ ] `ToolExecutor` 8개 Tool 래핑 및 실행
- [ ] Tool 실행 에러 시 graceful fallback
- [ ] `LunchChatbot.chat()` 전체 파이프라인 동작
- [ ] `LunchChatbot.chat_stream()` 스트리밍 파이프라인

**Track A — Streamlit:**
- [ ] 페이지 제목/아이콘 설정
- [ ] 사이드바: 사용자/모델 선택, Ollama 상태
- [ ] 빠른 액션 버튼 4개
- [ ] `st.chat_message`로 메시지 표시
- [ ] `st.write_stream`으로 스트리밍 응답
- [ ] 대화 초기화 버튼
- [ ] `streamlit run` 정상 실행

**Track B — React + FastAPI:**
- [ ] `POST /api/chat` 비스트리밍 엔드포인트
- [ ] `GET /api/chat/stream` SSE 스트리밍 엔드포인트
- [ ] `POST /api/chat/reset` 초기화 엔드포인트
- [ ] CORS 설정 (localhost:5173 허용)
- [ ] 세션 관리 (user_id+team_id별 인스턴스)
- [ ] React 프로젝트 초기화 (Vite + Tailwind)
- [ ] `chatApi.js` SSE 스트리밍 파싱
- [ ] `useChat` 훅: messages, isStreaming 상태 관리
- [ ] `ChatWindow` 컴포넌트: 스크롤, 자동 하단 이동
- [ ] `MessageBubble`: 사용자/어시스턴트 구분, 마크다운 렌더링
- [ ] `InputBar`: Enter 전송, 스트리밍 중 비활성화
- [ ] `QuickActions`: 첫 화면 빠른 버튼
- [ ] 다크모드 지원
- [ ] 모바일 반응형
- [ ] `npm run dev` 정상 실행

**테스트:**
- [ ] IntentClassifier 테스트 7건
- [ ] OllamaChat 테스트 3건 (mock)
- [ ] LunchChatbot 통합 테스트 3건
- [ ] 전체 테스트 통과 (`pytest tests/ -v`)
- [ ] 수동 테스트: "오늘 뭐 먹지?" 입력 시 추천 응답 확인

---

<div align="center">

**"오늘 뭐 먹지?"라고 물어보세요. AI가 답합니다.**

*Streamlit으로 3일 만에 프로토타입, React로 2주 만에 프로덕션.*
*백엔드 코어는 하나, 프론트엔드는 선택.*

</div>
