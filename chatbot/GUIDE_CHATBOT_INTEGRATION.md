# 🤖 "오늘 뭐 먹지?" 점심 추천 챗봇 — 상세 계획서

> ⚡ **선택적 추가 기능 · React 전용** (2026-04-08 결정)
>
> 본 프로젝트의 **메인 언어 처리 축은 [`../NLP/`](../NLP/README.md) (NLP MVP)** 입니다.
> ChatBOT 은 NLP 레이어 완성 후 **선택적 추가 기능**으로 구현합니다.
> 역할 분리 상세: [`../ROLE_SEPARATION_DECISION.md`](../ROLE_SEPARATION_DECISION.md)
>
> ⚠️ **Streamlit (Track A) 완전 제거됨** — 모든 UI 는 **React** 로 구현.
>
> ⚠️ **Ollama (로컬 LLM) 제거됨** — 외부 LLM API 로 전환:
> - **기본**: `gemini-2.5-flash` (Google Gemini)
> - **대안 A**: `gpt-4o-mini` (OpenAI)
> - **대안 B**: `claude-haiku-3-5` (Anthropic)
>
> **ChatBOT 의 고유 가치 영역 (NLP 와 겹치지 않음):**
> - Function Calling 기반 **행동 실행** (투표·식사 기록·거부권)
> - lunch-optimizer 28 엔드포인트의 **Tool 래핑**
> - Phase 4 **Docker Compose 통합 배포** (Ollama 컨테이너 없음)
>
> ---
>
> **소주제 1~4 파이프라인 + Gemini 2.5 Flash = 대화형 점심 추천 챗봇**
>
> 사용자가 자연어로 "오늘 뭐 먹지?", "단백질 많은 메뉴 추천해줘",
> "서브웨이에 투표할게" 같은 말을 하면, 4개 파이프라인의 데이터를
> 실시간으로 조합하여 맞춤 추천을 제공하는 클라우드 LLM API 챗봇

---

## 📋 목차

1. [프로젝트 개요](#1-프로젝트-개요)
2. [LLM API 선택: Gemini / OpenAI / Claude](#2-llm-api-선택-gemini--openai--claude)
3. [전체 아키텍처](#3-전체-아키텍처)
4. [핵심 설계: RAG + Function Calling](#4-핵심-설계-rag--function-calling)
5. [대화 시나리오 설계](#5-대화-시나리오-설계)
6. [구현 단계별 계획](#6-구현-단계별-계획)
7. [시스템 프롬프트 설계](#7-시스템-프롬프트-설계)
8. [UI/UX 계획](#8-uiux-계획)
9. [성능 최적화 전략](#9-성능-최적화-전략)
10. [테스트 및 평가 계획](#10-테스트-및-평가-계획)
11. [배포 및 운영 계획](#11-배포-및-운영-계획)
12. [일정 및 마일스톤](#12-일정-및-마일스톤)

---

## 1. 프로젝트 개요

### 1.1 왜 챗봇인가?

기존 대시보드는 "보는" 도구이지만, 챗봇은 "말하는" 도구입니다.
점심시간 직전 바쁜 직장인에게 대시보드 4개 탭을 클릭하게 하는 것보다,
"오늘 뭐 먹지?"라고 한마디 하면 알아서 답해주는 인터페이스가 더 자연스럽습니다.

| 기존 대시보드 | 챗봇 |
|-------------|------|
| 4개 탭을 직접 탐색 | "오늘 뭐 먹지?"로 한 번에 |
| 수치/차트를 해석해야 함 | 자연어로 설명해줌 |
| 투표를 UI에서 클릭 | "서브웨이에 투표할게"로 끝 |
| 영양 리포트를 읽어야 함 | "이번 주 영양 밸런스 어때?"로 요약 |

### 1.2 핵심 가치

- **제로 클릭 추천**: 질문 하나로 4개 축(거리/날씨/영양/팀) 통합 답변
- **맥락 인식 대화**: "그럼 거기 말고 다른 데는?" 같은 후속 질문 처리
- **행동 실행**: 투표, 식사 기록, 거부권 등을 대화로 수행
- **빠른 응답**: 클라우드 LLM API 사용으로 로컬 모델 대비 응답 속도 대폭 향상

---

## 2. LLM API 선택: Gemini / OpenAI / Claude

### 2.1 API 비교 (2026년 4월 기준)

| 항목 | **Gemini 2.5 Flash** ✅ 기본 | GPT-4o Mini | Claude Haiku 3.5 |
|------|--------------------------|-------------|-----------------|
| 제공사 | Google | OpenAI | Anthropic |
| 한국어 성능 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Function Calling | 완벽 지원 | 완벽 지원 | 완벽 지원 |
| 응답 속도 | 매우 빠름 | 빠름 | 빠름 |
| 비용 (입력/1M tok) | $0.15 | $0.15 | $0.80 |
| 비용 (출력/1M tok) | $0.60 | $0.60 | $4.00 |
| 스트리밍 | 지원 | 지원 | 지원 |
| 무료 티어 | ✅ 있음 | ❌ 없음 | ❌ 없음 |
| SDK | `google-genai` | `openai` | `anthropic` |

### 2.2 권장 선택

**기본 (테스트/MVP)**: `gemini-2.5-flash`
- 무료 티어 제공으로 초기 개발/테스트에 최적
- 응답 속도 빠르고 한국어 품질 우수
- Function Calling 완벽 지원

**대안 A**: `gpt-4o-mini`
- OpenAI의 경량 모델, 비용 효율적
- Function Calling이 가장 성숙하고 안정적

**대안 B**: `claude-haiku-3-5`
- 한국어 이해 및 자연스러운 응답 품질 최상위
- 비용은 가장 높지만 품질 우선 시 선택

### 2.3 API 키 설정

```bash
# env.env 파일에 사용할 API 키 설정 (하나 이상)
GEMINI_API_KEY=your-gemini-api-key       # 기본 (Google AI Studio에서 무료 발급)
OPENAI_API_KEY=your-openai-api-key       # 대안 A
ANTHROPIC_API_KEY=your-anthropic-api-key # 대안 B

# 사용할 프로바이더 지정 (gemini / openai / claude)
LLM_PROVIDER=gemini
LLM_MODEL=gemini-2.5-flash
```

### 2.4 패키지 설치

```bash
pip install google-genai          # Gemini (기본)
pip install openai                # OpenAI (대안 A)
pip install anthropic             # Claude (대안 B)
```

---

## 3. 전체 아키텍처

### 3.1 계층 구조

```
┌─────────────────────────────────────────────────────────────┐
│                    Presentation Layer                        │
│  ┌──────────────────────────┐  ┌──────────────┐             │
│  │ React Chat Component     │  │ Slack Bot    │             │
│  │ (대시보드 통합 사이드패널)  │  │ (Phase 2)    │             │
│  └──────────────┬───────────┘  └──────┬───────┘             │
└─────────────────┼────────────────────┼──────────────────────┘
                  │                    │
                  ▼                    ▼
┌─────────────────────────────────────────────────────────────┐
│                    Chatbot Core Layer                        │
│                                                             │
│  ┌─────────────────────────────────────────────────┐        │
│  │           Intent Classifier & Router             │        │
│  │  "오늘 뭐 먹지?" → RECOMMEND                      │        │
│  │  "한솥 칼로리 알려줘" → QUERY                      │        │
│  │  "서브웨이에 투표" → ACTION                        │        │
│  │  "이번 주 영양 어때?" → REPORT                     │        │
│  │  "안녕" → CHITCHAT                               │        │
│  └─────────────┬───────────────────────────┘        │
│                │                                     │
│  ┌─────────────▼───────────────────────────┐        │
│  │         Context Builder (RAG)            │        │
│  │  • 파이프라인 DB 조회 (4개 소주제)          │        │
│  │  • Tool Function 실행 (투표/기록)          │        │
│  │  • 사용자 프로필 로드                      │        │
│  │  • 대화 히스토리 관리                      │        │
│  │  • System Prompt 조립                    │        │
│  └─────────────┬───────────────────────────┘        │
│                │                                     │
│  ┌─────────────▼───────────────────────────┐        │
│  │    LLM API Provider (추상화 레이어)       │        │
│  │  ┌─────────────┬───────────┬──────────┐ │        │
│  │  │ Gemini 2.5  │ GPT-4o   │ Claude   │ │        │
│  │  │ Flash ✅기본 │ Mini     │ Haiku    │ │        │
│  │  └─────────────┴───────────┴──────────┘ │        │
│  │    • Streaming response                  │        │
│  │    • Function calling (tool use)         │        │
│  │    • 환경변수로 프로바이더 전환             │        │
│  └─────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────┐
│                    Data Layer (소주제 1~4)                    │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐               │
│  │음식점DB │ │날씨 로그│ │영양 정보│ │투표/이력│               │
│  │(소주제1)│ │(소주제2)│ │(소주제3)│ │(소주제4)│               │
│  └────────┘ └────────┘ └────────┘ └────────┘               │
│                     SQLite / PostgreSQL                      │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 핵심 설계 원칙

**LLM은 "두뇌", 파이프라인은 "감각기관"**

LLM은 자연어 이해와 생성만 담당하고, 실제 데이터 조회/계산은 기존 파이프라인 코드가 수행합니다. LLM이 직접 SQL을 쓰거나 API를 호출하는 것이 아니라, 미리 정의된 Tool Function을 호출하여 결과를 받아 자연어로 가공합니다.

---

## 4. 핵심 설계: RAG + Function Calling

### 4.1 Tool Functions 정의

LLM에게 제공할 도구 함수 목록입니다. 각 함수는 기존 소주제 1~4의 코드를 래핑합니다.

```python
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_lunch_recommendations",
            "description": "오늘 날씨, 영양 밸런스, 팀 투표를 종합한 점심 추천 목록을 조회합니다",
            "parameters": {
                "type": "object",
                "properties": {
                    "top_n": {"type": "integer", "description": "추천 개수", "default": 5},
                    "category": {"type": "string", "description": "카테고리 필터 (한식/일식/양식 등)"},
                    "max_distance": {"type": "integer", "description": "최대 거리(m)"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_weather",
            "description": "현재 날씨와 미세먼지 정보를 조회합니다",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_nutrition_diagnosis",
            "description": "사용자의 이번 주 영양 섭취 진단 결과를 조회합니다",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "사용자 ID"}
                },
                "required": ["user_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_restaurant_info",
            "description": "특정 음식점의 상세 정보(거리, 영양, 평점 등)를 조회합니다",
            "parameters": {
                "type": "object",
                "properties": {
                    "restaurant_name": {"type": "string", "description": "음식점 이름"}
                },
                "required": ["restaurant_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "cast_vote",
            "description": "점심 투표를 행사합니다",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string"},
                    "restaurant_name": {"type": "string", "description": "투표할 음식점 이름"}
                },
                "required": ["user_id", "restaurant_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_vote_status",
            "description": "현재 팀 투표 현황을 조회합니다",
            "parameters": {
                "type": "object",
                "properties": {
                    "team_id": {"type": "string"}
                },
                "required": ["team_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "record_meal",
            "description": "식사 기록을 저장합니다",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string"},
                    "restaurant_name": {"type": "string"},
                    "satisfaction": {"type": "integer", "description": "만족도 1~5점"}
                },
                "required": ["user_id", "restaurant_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_visit_history",
            "description": "최근 방문 기록을 조회합니다",
            "parameters": {
                "type": "object",
                "properties": {
                    "team_id": {"type": "string"},
                    "days": {"type": "integer", "default": 7}
                },
                "required": ["team_id"]
            }
        }
    }
]
```

### 4.2 RAG 컨텍스트 조립 흐름

```
사용자 입력: "비 오는데 따뜻한 거 추천해줘"
      │
      ▼
[1] Intent 분류 → RECOMMEND (조건부 추천)
      │
      ▼
[2] Context 수집 (병렬 실행):
    ├── 날씨 DB → {"temp": 8, "rain_type": 1, "dust": "보통"}
    ├── 사용자 영양 이력 → {"avg_protein": 18, "status": "단백질 부족"}
    ├── 팀 투표 현황 → {"한솥도시락": 2표, "서브웨이": 1표}
    └── 음식점 목록 → [12개 음식점 + 점수]
      │
      ▼
[3] System Prompt + Context 조립:
    "당신은 점심 추천 도우미입니다.
     현재 날씨: 기온 8°C, 비, 미세먼지 보통
     사용자 영양: 단백질 부족 (주간 평균 18g)
     팀 투표: 한솥 2표, 서브웨이 1표
     추천 음식점 TOP 5: [...]
     사용자 조건: 따뜻한 음식, 비 오는 날"
      │
      ▼
[4] Ollama LLM 호출 → 자연어 응답 생성
      │
      ▼
"비가 오고 있어서 가까운 곳이 좋겠네요! 🌧️

1위 **명동칼국수** (320m) — 따끈한 칼국수가 이 날씨에 딱이에요.
   게다가 단백질 20g으로 이번 주 부족한 단백질도 보충할 수 있어요.

2위 **본죽** (160m) — 가장 가까운 따뜻한 메뉴! 비 올 때 딱 좋아요.

팀원 3명이 아직 투표 안 했어요. 투표하시겠어요?"
```

---

## 5. 대화 시나리오 설계

### 5.1 핵심 시나리오 10가지

| # | 사용자 발화 (예시) | Intent | 호출 Tool | 기대 응답 |
|---|-----------------|--------|----------|----------|
| 1 | "오늘 뭐 먹지?" | RECOMMEND | get_lunch_recommendations | TOP 5 종합 추천 + 이유 |
| 2 | "비 오는데 가까운 곳" | RECOMMEND (조건부) | get_current_weather + recommendations | 날씨 반영 필터링 추천 |
| 3 | "단백질 많은 메뉴 추천" | RECOMMEND (영양) | get_nutrition_diagnosis + recommendations | 영양 기반 필터링 추천 |
| 4 | "한솥도시락 칼로리 알려줘" | QUERY | get_restaurant_info | 특정 음식점 상세 정보 |
| 5 | "이번 주 영양 어때?" | REPORT | get_nutrition_diagnosis | 주간 영양 진단 요약 |
| 6 | "서브웨이에 투표할게" | ACTION (투표) | cast_vote | 투표 완료 + 현재 현황 |
| 7 | "지금 투표 현황 알려줘" | QUERY (투표) | get_vote_status | 팀원별 투표 현황 |
| 8 | "오늘 서브웨이 먹었어, 4점" | ACTION (기록) | record_meal | 식사 기록 완료 + 영양 코멘트 |
| 9 | "최근에 뭐 먹었지?" | QUERY (이력) | get_visit_history | 최근 방문 기록 목록 |
| 10 | "그럼 2번째 거로 할게" | CONTEXT (이전 응답 참조) | (이전 추천 결과 참조) | 후속 처리 |

### 5.2 멀티턴 대화 예시

```
사용자: 오늘 뭐 먹을까?
봇:     오늘은 기온 12°C에 흐린 날씨예요. 이번 주 단백질이 좀 부족했네요!
        
        1. 명동칼국수 (320m) — 종합 82점 ⭐
           따뜻한 국물 + 단백질 20g, 비 올 가능성 대비 실내
        2. 서브웨이 (180m) — 종합 78점
           가장 가까운 고단백 메뉴, 팀원 2명 투표 중
        3. 한솥도시락 (120m) — 종합 75점
           팀에서 가장 인기 많은 곳!
        
        투표하시겠어요? 아니면 더 자세한 정보가 필요하시면 말씀해주세요!

사용자: 1번 영양 정보 더 알려줘
봇:     명동칼국수의 추정 영양 정보예요:
        
        · 열량: 550kcal (적정 범위 ✅)
        · 단백질: 20g (이번 주 부족분 보충에 좋아요!)
        · 탄수화물: 78g (약간 높은 편)
        · 나트륨: 1,200mg (⚠️ 국물은 좀 남기세요)
        
        이번 주 평균 단백질이 18g이었는데, 여기서 20g을 먹으면
        주간 평균이 19g으로 올라갈 수 있어요.

사용자: 좋아, 거기로 투표할게
봇:     명동칼국수에 투표 완료! 🗳️
        
        현재 투표 현황:
        · 명동칼국수: 2표 (김민수, 본인)
        · 서브웨이: 1표 (박준혁)
        · 미투표: 이수진, 정하은, 최동원
        
        아직 3명이 투표하지 않았어요. 11:30에 자동 마감됩니다!

사용자: (식후) 오늘 명동칼국수 먹었어, 만족도 4점
봇:     식사 기록 저장했어요! 😋
        
        오늘 섭취: 550kcal, 단백질 20g, 탄수화물 78g
        이번 주 누적: 3일 기록, 평균 칼로리 593kcal
        
        단백질이 조금 올라갔네요! 내일은 지방이 적은 메뉴를
        선택하면 밸런스가 더 좋아질 거예요.
```

---

## 6. 구현 단계별 계획

### Phase 1: 기본 챗봇 (1~2주)

```
목표: Gemini 2.5 Flash API 연동 + React + FastAPI 기본 대화 동작

구현:
1. API 키 발급 및 환경변수 설정 (env.env)
2. llm_client.py 구현 (GeminiClient + 멀티 프로바이더 추상화)
3. 기본 System Prompt 작성
4. FastAPI /api/chat 엔드포인트 + SSE 스트리밍 구현
5. 대화 히스토리 관리 (ChatHistory 클래스)
```

### Phase 2: Tool Calling 연동 (2~3주)

```
목표: 8개 Tool Function과 소주제 1~4 파이프라인 연결

구현:
1. Tool Function 8개 정의 및 파이프라인 코드 래핑
2. Intent 분류 로직 (키워드 기반 → LLM 기반)
3. RAG Context Builder 구현
4. Tool 결과를 LLM 컨텍스트에 주입하는 파이프라인
5. Function Calling 응답 파싱 및 재호출 루프
```

### Phase 3: 맥락 인식 고도화 (1~2주)

```
목표: 멀티턴 대화, 후속 질문, 사용자 프로필 반영

구현:
1. 대화 히스토리에서 이전 추천 결과 참조
2. "그럼 2번째 거로" 같은 대명사 해석
3. 사용자 프로필(알레르기, 비선호) 자동 반영
4. 시간대별 행동 유도 (10시→투표 안내, 12시→기록 안내)
```

### Phase 4: UI/UX 완성 (1주)

```
목표: 프로덕션 수준의 채팅 UI

구현:
1. Streamlit 또는 React 채팅 UI 완성
2. 음식점 카드 컴포넌트 (이미지, 점수, 거리 표시)
3. 빠른 응답 버튼 ("투표하기", "기록하기")
4. 스트리밍 응답 표시
5. 모바일 반응형
```

---

## 7. 시스템 프롬프트 설계

### 7.1 기본 시스템 프롬프트

```python
SYSTEM_PROMPT = """당신은 "점심 도우미"입니다. 직장인 팀의 점심 식사를 도와주는 친근한 AI 어시스턴트입니다.

## 역할
- 오늘의 날씨, 사용자의 영양 상태, 팀원들의 투표를 종합하여 최적의 점심을 추천합니다.
- 사용자가 투표, 식사 기록, 거부권 등의 행동을 대화로 수행할 수 있게 도와줍니다.
- 친근하고 간결하게 답변하되, 중요한 정보는 빠뜨리지 않습니다.

## 행동 규칙
1. 추천 시 반드시 '종합 점수'와 '추천 이유'를 함께 제공하세요.
2. 영양 관련 조언은 권고 수준으로 제공하고, 의학적 진단은 하지 마세요.
3. 투표나 기록 같은 행동은 사용자의 명시적 요청이 있을 때만 실행하세요.
4. 이전 대화의 맥락을 기억하고, "그거", "거기" 같은 대명사를 이해하세요.
5. 답변은 한국어로 하되, 이모지를 적절히 사용하세요.
6. 음식점 추천은 최대 5개까지만 제공하세요.

## 현재 상태
- 오늘 날짜: {today}
- 현재 시각: {current_time}
- 사용자: {user_name} ({team_name} 소속)
- 투표 상태: {vote_status}
"""
```

### 7.2 동적 컨텍스트 주입

```python
def build_context(user_id: str, team_id: str) -> str:
    """Tool 호출 결과를 시스템 프롬프트에 주입"""
    weather = get_current_weather()
    diagnosis = get_nutrition_diagnosis(user_id)
    vote_status = get_vote_status(team_id)
    
    context = f"""
## 오늘의 환경 정보
- 날씨: 기온 {weather['temp']}°C, {weather['sky_str']}, 강수확률 {weather['pop']}%
- 미세먼지: {weather['dust_grade']}
- 외출 쾌적도: {weather['outdoor_comfort']}

## 사용자 영양 상태
- 이번 주 기록: {diagnosis['recorded_days']}일
- 종합 판정: {diagnosis['overall_status']} ({diagnosis['overall_score']}점)
- 주요 이슈: {', '.join(diagnosis['recommendations'][:2])}

## 팀 투표 현황
- 투표 참여: {vote_status['voted_count']}/{vote_status['team_members']}명
- 현재 1위: {vote_status['tally'][0]['restaurant_name'] if vote_status['tally'] else '없음'}
"""
    return context
```

---

## 8. UI/UX 계획

### 8.1 Streamlit 채팅 UI (MVP)

```python
# 핵심 구조
import streamlit as st
from ollama import chat

st.title("🍱 오늘 뭐 먹지?")
st.caption("점심 추천 챗봇 — 날씨·영양·팀 투표 통합")

# 채팅 히스토리
if "messages" not in st.session_state:
    st.session_state.messages = []

# 빠른 액션 버튼
col1, col2, col3, col4 = st.columns(4)
with col1:
    if st.button("🍽️ 추천받기"):
        prompt = "오늘 점심 추천해줘"
with col2:
    if st.button("🗳️ 투표현황"):
        prompt = "투표 현황 알려줘"
with col3:
    if st.button("📊 영양리포트"):
        prompt = "이번 주 영양 상태 알려줘"
with col4:
    if st.button("🌤️ 날씨"):
        prompt = "오늘 날씨 어때?"

# 채팅 인터페이스
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("점심에 대해 뭐든 물어보세요!"):
    # ... Ollama 호출 및 응답 스트리밍
```

### 8.2 React 채팅 컴포넌트 (Phase 4)

React 대시보드에 채팅 사이드 패널을 추가하여, 기존 대시보드와 챗봇을 동시에 사용할 수 있게 합니다. FastAPI 백엔드의 `/api/chat` 엔드포인트와 SSE(Server-Sent Events)로 연결합니다.

---

## 9. 성능 최적화 전략

### 9.1 응답 속도 최적화

| 전략 | 설명 | 예상 효과 |
|------|------|----------|
| 컨텍스트 프리로드 | 투표 시간 시작 시 날씨/영양 데이터를 미리 캐싱 | 첫 응답 1~2초 단축 |
| 스트리밍 응답 | SDK stream 옵션으로 토큰 단위 전송 (SSE) | 체감 대기 시간 감소 |
| 경량 Intent 분류 | LLM 호출 전 키워드 규칙으로 1차 분류 | 단순 질문에 LLM 호출 불필요 |
| DB 쿼리 캐싱 | 동일 날짜 내 날씨/추천 결과를 Redis 캐싱 | DB 부하 90% 감소 |
| Rate Limit 대응 | 지수 백오프 재시도 + 프로바이더 자동 전환 | API 오류 시 자동 복구 |

### 9.2 컨텍스트 윈도우 관리

```python
MAX_HISTORY_TURNS = 10  # 최근 10턴만 유지
MAX_CONTEXT_TOKENS = 4096  # 컨텍스트 토큰 제한

def trim_history(messages: list, max_turns: int = 10) -> list:
    """시스템 프롬프트 + 최근 N턴만 유지"""
    system = [m for m in messages if m["role"] == "system"]
    conversations = [m for m in messages if m["role"] != "system"]
    return system + conversations[-max_turns * 2:]  # user+assistant 쌍
```

### 9.3 프로바이더별 비용 최적화 전략

| 환경 | 프로바이더 | 모델 | 예상 월비용 (팀 5명) | 품질 |
|------|----------|------|-------------------|------|
| 개발/테스트 | Gemini | gemini-2.5-flash | 무료 (무료 티어) | 우수 |
| 소규모 팀 운영 | Gemini | gemini-2.5-flash | ~$3~10 | 우수 |
| 품질 우선 | Claude | claude-haiku-3-5 | ~$10~30 | 최상 |
| 대안 | OpenAI | gpt-4o-mini | ~$5~15 | 우수 |

> 💡 토큰 절감 팁: Tool 결과를 LLM에 전달할 때 전체 JSON 대신 포맷된 요약 텍스트를 사용하면 토큰 사용량을 40~60% 줄일 수 있습니다.

---

## 10. 테스트 및 평가 계획

### 10.1 기능 테스트 시나리오

| # | 시나리오 | 입력 | 기대 결과 | 합격 기준 |
|---|---------|------|----------|----------|
| 1 | 기본 추천 | "오늘 뭐 먹지?" | 5개 추천 + 점수 | 5개 반환, 점수 내림차순 |
| 2 | 조건부 추천 | "가까운 한식집" | 한식 + 거리순 | 카테고리=한식만 포함 |
| 3 | 날씨 반영 | "비 오는데 추천" | 가까운 곳 + 국물류 | 날씨 점수 반영 확인 |
| 4 | 영양 반영 | "단백질 많은 거" | 고단백 메뉴 우선 | 단백질 25g+ 상위 |
| 5 | 투표 실행 | "한솥에 투표" | 투표 완료 메시지 | DB에 투표 기록 저장 |
| 6 | 식사 기록 | "서브웨이 먹었어 5점" | 기록 완료 + 영양 코멘트 | DB에 기록 저장 |
| 7 | 후속 질문 | (추천 후) "2번째 거 상세" | 2번째 음식점 정보 | 이전 맥락 참조 |
| 8 | 잘못된 입력 | "아이언맨 추천해줘" | 부드러운 거절 | 점심 관련 안내 |

### 10.2 품질 평가 지표

| 지표 | 측정 방법 | 목표 |
|------|----------|------|
| 응답 정확도 | 50개 테스트 질문 대비 정확 답변 비율 | 85%+ |
| 평균 응답 시간 | 첫 토큰까지 시간 (TTFT) | 2초 이내 |
| Tool 호출 정확도 | 올바른 Tool을 호출한 비율 | 90%+ |
| 한국어 자연스러움 | 5명 사용자 평가 (1~5점) | 4.0+ |
| 대화 유지율 | 3턴 이상 대화한 비율 | 60%+ |

---

## 11. 배포 및 운영 계획

### 11.1 Docker Compose 구성

```yaml
# docker-compose.yml — Ollama 컨테이너 없음, LLM은 외부 API 사용
version: '3.8'
services:
  api:
    build: .
    ports:
      - "8000:8000"   # FastAPI
    environment:
      # LLM API 설정
      - LLM_PROVIDER=${LLM_PROVIDER:-gemini}
      - LLM_MODEL=${LLM_MODEL:-gemini-2.5-flash}
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}       # 선택
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY} # 선택
      - DB_URL=sqlite:///data/lunch_optimizer.db
    volumes:
      - app_data:/app/data

  frontend:
    build:
      dockerfile: docker/frontend/Dockerfile
    ports:
      - "3000:3000"

volumes:
  app_data:
```

### 11.2 운영 모니터링

| 항목 | 모니터링 대상 | 도구 |
|------|-------------|------|
| API 상태 | LLM API 응답 성공률, Rate Limit 발생 횟수 | FastAPI middleware |
| 응답 시간 | P50/P95 latency (TTFT 포함) | FastAPI middleware |
| 토큰 사용량 | 세션당 평균 토큰 수, 월별 누적 비용 | 커스텀 로깅 |
| 에러율 | Tool 호출 실패, LLM 타임아웃, Rate Limit | 로그 모니터링 |
| 사용 패턴 | 시간대별 사용량, 인기 Intent | DB 로그 분석 |

---

## 12. 일정 및 마일스톤

### 전체 타임라인 (약 6~8주)

| 주차 | 마일스톤 | 산출물 |
|------|---------|--------|
| 1주 | API 키 발급 + llm_client.py 구현 + FastAPI 기본 엔드포인트 | 기본 채팅 API 동작 확인 |
| 2주 | Tool Functions 8개 정의 + 파이프라인 연결 | Tool 호출 동작 확인 |
| 3주 | RAG Context Builder + System Prompt 완성 | 날씨/영양/투표 반영 추천 |
| 4주 | Intent 분류 고도화 + 멀티턴 대화 | 10가지 시나리오 통과 |
| 5주 | UI/UX 완성 + 빠른 버튼 + 스트리밍 | 프로덕션 수준 UI |
| 6주 | 테스트 + 성능 최적화 + 문서화 | 품질 평가 보고서 |
| 7~8주 | Docker 배포 + 팀 베타 테스트 + 피드백 반영 | 최종 릴리스 |

### 최종 산출물 요약

```
lunch-optimizer/
├── (소주제 1~4 기존 코드)
├── chatbot/
│   ├── __init__.py
│   ├── core.py              # 챗봇 메인 로직
│   ├── intent.py             # Intent 분류기
│   ├── context_builder.py    # RAG 컨텍스트 조립
│   ├── tools.py              # Tool Functions 래퍼
│   ├── prompts.py            # System Prompt 관리
│   ├── history.py            # 대화 히스토리 관리
│   └── llm_client.py         # LLM API 클라이언트 (Gemini/OpenAI/Claude)
├── ui/
│   └── react-chat/           # React 채팅 UI (대시보드 통합)
├── tests/
│   ├── test_chatbot_core.py
│   ├── test_intent.py
│   ├── test_tools.py
│   └── test_scenarios.py     # 10가지 시나리오 테스트
├── docker-compose.yml
└── GUIDE_CHATBOT.md          # (이 문서)
```

---

<div align="center">

**"오늘 뭐 먹지?" 한마디면, 나머지는 AI가 알아서.**

*4개 파이프라인의 데이터가 자연어로 흐르는 순간,*
*점심 고민은 대화 한 번으로 끝납니다.*

</div>
