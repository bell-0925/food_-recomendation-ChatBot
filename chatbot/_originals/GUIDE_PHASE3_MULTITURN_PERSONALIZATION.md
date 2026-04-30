# 🧠 Phase 3: 멀티턴 대화 고도화 + 개인화 — Claude Code 구현 가이드라인

> **목표**: Phase 2에서 완성한 Tool 기반 챗봇을 고도화하여,
> 문맥을 이해하는 자연스러운 대화, 시간대별 행동 유도,
> 사용자 선호 학습까지 구현합니다.

---

## 📋 목차

1. [Phase 3 개요](#1-phase-3-개요)
2. [프로젝트 구조 확장](#2-프로젝트-구조-확장)
3. [Step 1 — 대화 상태 머신 설계](#3-step-1--대화-상태-머신-설계)
4. [Step 2 — 후속 질문 및 대명사 해석](#4-step-2--후속-질문-및-대명사-해석)
5. [Step 3 — 대화 요약 및 컨텍스트 압축](#5-step-3--대화-요약-및-컨텍스트-압축)
6. [Step 4 — 시간대별 프로액티브 행동 유도](#6-step-4--시간대별-프로액티브-행동-유도)
7. [Step 5 — 사용자 선호 프로필 학습](#7-step-5--사용자-선호-프로필-학습)
8. [Step 6 — 개인화 추천 강화](#8-step-6--개인화-추천-강화)
9. [Step 7 — 대화 품질 가드레일](#9-step-7--대화-품질-가드레일)
10. [Step 8 — 테스트 및 평가](#10-step-8--테스트-및-평가)
11. [트러블슈팅 가이드](#11-트러블슈팅-가이드)
12. [체크리스트](#12-체크리스트)

---

## 1. Phase 3 개요

### 1.1 Phase 2 → Phase 3 변화

| 항목 | Phase 2 | Phase 3 |
|------|---------|---------|
| 대화 방식 | 1문 1답 (독립 질문) | 멀티턴 (문맥 유지) |
| 대명사 | 처리 불가 | "그거", "거기", "2번째" 해석 |
| 행동 유도 | 사용자가 먼저 질문 | 시간대별 챗봇이 먼저 제안 |
| 개인화 | 없음 (모든 사용자 동일) | 선호도 학습 기반 맞춤 추천 |
| 컨텍스트 | 고정 크기 | 동적 요약/압축 |
| 품질 관리 | 없음 | 할루시네이션 방지 가드레일 |

### 1.2 Phase 3에서 해결할 핵심 문제 5가지

**문제 1 — "그거 말고 다른 데"가 안 통함**
Phase 2에서는 각 메시지가 독립적이라 이전 추천 결과를 참조하지 못합니다.

**문제 2 — 매번 같은 질문을 해야 함**
오전 10시에 챗봇이 먼저 "오늘 투표 시작됐어요!"라고 알려주면 편리합니다.

**문제 3 — 모든 사용자에게 같은 추천**
사용자 A는 항상 한식을 선택하는데, 매번 양식도 추천합니다.

**문제 4 — 긴 대화에서 맥락을 잃음**
20턴 이상 대화하면 컨텍스트 윈도우를 초과하여 초기 내용을 잊습니다.

**문제 5 — 가끔 엉뚱한 답변을 함**
LLM이 존재하지 않는 음식점을 만들어내거나 잘못된 영양 정보를 생성합니다.

---

## 2. 프로젝트 구조 확장

### Claude Code 프롬프트

```
Phase 2의 chatbot/ 디렉토리를 Phase 3 구조로 확장해줘.

수정/추가할 파일:
chatbot/
├── core.py                      # 확장: 상태 머신 + 프로액티브 통합
├── history.py                   # 확장: 대화 요약/압축 기능
├── intent.py                    # 확장: 대명사 해석 + 후속 질문 분류
├── state_machine.py             # 신규: 대화 상태 관리
├── reference_resolver.py        # 신규: 대명사/순서 참조 해석
├── conversation_summarizer.py   # 신규: 대화 요약 엔진
├── proactive_agent.py           # 신규: 시간대별 행동 유도
├── user_profile.py              # 신규: 사용자 선호 학습
├── personalizer.py              # 신규: 개인화 추천 강화
├── guardrails.py                # 신규: 응답 품질 검증
└── prompts/
    ├── system.md                # 확장: 멀티턴 규칙 추가
    ├── summarize.md             # 신규: 대화 요약 프롬프트
    └── personalize.md           # 신규: 개인화 프롬프트

database/models.py에 추가:
- UserPreference 모델
- ConversationLog 모델

tests/
├── test_reference_resolver.py   # 신규
├── test_state_machine.py        # 신규
├── test_proactive_agent.py      # 신규
├── test_user_profile.py         # 신규
├── test_guardrails.py           # 신규
└── test_phase3_integration.py   # 신규
```

---

## 3. Step 1 — 대화 상태 머신 설계

### Claude Code 프롬프트

```
chatbot/state_machine.py를 구현해줘.

ConversationStateMachine 클래스:

대화의 현재 "단계"를 추적하여 적절한 응답과 행동 유도를 결정하는 상태 머신.

상태 정의 (Enum):

class ConversationState(Enum):
    IDLE = "idle"                        # 초기 상태 / 대화 없음
    GREETING = "greeting"                # 인사 교환 중
    RECOMMENDING = "recommending"        # 추천 결과를 제시한 상태
    EXPLORING = "exploring"              # 사용자가 추천 결과를 탐색 중
    VOTING = "voting"                    # 투표 프로세스 진행 중
    RECORDING = "recording"             # 식사 기록 진행 중
    REPORTING = "reporting"              # 리포트(영양/이력) 조회 중
    CONFIRMING = "confirming"            # 행동 확인 대기 중 (예/아니오)

상태 전이 규칙:

1. IDLE → GREETING: 사용자 첫 인사
2. IDLE/GREETING → RECOMMENDING: 추천 요청
3. RECOMMENDING → EXPLORING: 후속 질문 ("상세 알려줘", "다른 거")
4. EXPLORING → RECOMMENDING: 새로운 추천 요청
5. RECOMMENDING/EXPLORING → VOTING: "거기로 투표할게"
6. VOTING → CONFIRMING: 투표 확인 필요 시
7. CONFIRMING → IDLE: 확인 완료
8. * → RECORDING: "먹었어" / "기록해줘"
9. * → REPORTING: 영양/이력 조회

ConversationStateMachine:

1. __init__(self):
   state = ConversationState.IDLE
   context_data = {}  # 현재 상태의 관련 데이터

2. transition(intent: Intent, entities: dict) -> ConversationState:
   현재 상태 + Intent에 따라 다음 상태를 결정하고 전이.
   유효하지 않은 전이는 무시하고 현재 상태 유지.
   전이 시 context_data를 업데이트.

3. get_state() -> ConversationState:
   현재 상태 반환.

4. get_context_data() -> dict:
   현재 상태의 관련 데이터 반환.
   RECOMMENDING 상태: {"last_recommendations": [...], "filters": {...}}
   EXPLORING 상태: {"selected_restaurant": {...}, "from_rank": 2}
   VOTING 상태: {"target_restaurant": "한솥도시락", "confirmed": False}
   CONFIRMING 상태: {"pending_action": "vote", "target": "한솥도시락"}

5. set_recommendations(recommendations: list[dict]) -> None:
   추천 결과를 저장. RECOMMENDING 상태에서 호출.

6. get_selected_by_rank(rank: int) -> dict | None:
   저장된 추천 결과에서 rank번째 음식점 반환.

7. needs_confirmation() -> bool:
   현재 상태가 CONFIRMING인지 확인.

8. reset() -> None:
   IDLE 상태로 초기화.

타입 힌트, docstring 포함해줘.
```

---

## 4. Step 2 — 후속 질문 및 대명사 해석

### Claude Code 프롬프트

```
chatbot/reference_resolver.py를 구현해줘.

ReferenceResolver 클래스:

사용자 메시지에서 이전 대화를 참조하는 표현을 해석하는 역할.
Phase 2의 IntentClassifier가 FOLLOWUP으로 분류한 메시지를
실제 음식점명/조건으로 변환.

1. resolve(message: str, state: ConversationStateMachine,
           history: ChatHistory) -> dict:
   사용자 메시지의 참조 표현을 해석.
   
   반환:
   {
     "resolved": True,
     "original": "2번째 거로 할게",
     "resolved_text": "서브웨이에 투표할게",
     "resolved_entities": {
       "restaurant_name": "서브웨이",
       "action": "vote"
     },
     "resolution_type": "rank_reference"  # rank / pronoun / negation / comparison
   }

해석 규칙:

a. 순서 참조 (rank_reference):
   "1번", "첫 번째", "1번째 거", "맨 위에 거"
   → state.get_selected_by_rank(1)에서 음식점명 추출
   
   "마지막 거", "맨 아래"
   → state.get_selected_by_rank(-1)

b. 대명사 참조 (pronoun_reference):
   "거기", "그 집", "그거", "그 음식점"
   → EXPLORING 상태의 selected_restaurant 사용
   → 없으면 RECOMMENDING 상태의 1순위 사용
   
   "아까 그거"
   → history에서 가장 최근 언급된 음식점명 추출

c. 부정 참조 (negation_reference):
   "그거 말고", "다른 데", "그거 빼고"
   → 현재 선택된 음식점을 제외 목록에 추가하고 재추천 요청
   
   "한식 말고", "국물류 말고"
   → 카테고리/메뉴 타입 제외 조건 추출

d. 비교 참조 (comparison_reference):
   "1번이랑 3번 비교해줘"
   → 두 음식점의 상세 정보를 나란히 조회
   
   "거기보다 가까운 데"
   → 현재 선택된 음식점의 거리보다 가까운 조건 추가

e. 맥락 이어가기 (continuation):
   "더 알려줘", "또 뭐 있어", "계속"
   → 현재 상태에 따라:
     RECOMMENDING → 다음 5개 추천
     EXPLORING → 현재 음식점 추가 정보
     REPORTING → 다음 항목

2. _extract_rank_number(message: str) -> int | None:
   메시지에서 순서 숫자를 추출.
   "2번째" → 2, "세 번째" → 3, "첫 번째" → 1
   한글 숫자도 처리: "두 번째" → 2, "셋째" → 3

3. _extract_negation_target(message: str, state) -> dict | None:
   부정 대상 추출.
   "그거 말고" → 현재 selected_restaurant
   "한식 말고" → category="한식" 제외

4. _find_last_mentioned_restaurant(history: ChatHistory) -> str | None:
   대화 히스토리에서 가장 최근 언급된 음식점 이름을 역순 탐색.
   어시스턴트 응답에서 음식점명 DB와 매칭.

해석 실패 시:
{"resolved": False, "reason": "어떤 음식점을 말씀하시는지 알 수 없어요. 
음식점 이름을 직접 말씀해주시겠어요?"}

타입 힌트, docstring, 로깅 포함해줘.
```

---

## 5. Step 3 — 대화 요약 및 컨텍스트 압축

### Claude Code 프롬프트

```
chatbot/conversation_summarizer.py를 구현해줘.

ConversationSummarizer 클래스:

긴 대화의 컨텍스트 윈도우 초과를 방지하기 위해
오래된 대화를 요약하여 압축하는 역할.

1. should_summarize(history: ChatHistory) -> bool:
   요약이 필요한지 판단.
   조건:
   - 토큰 추정치가 MAX_CONTEXT_TOKENS의 70%를 초과할 때
   - 대화 턴 수가 8턴을 초과할 때
   둘 중 하나라도 충족하면 True.

2. summarize(history: ChatHistory, ollama: OllamaChat) -> str:
   오래된 대화(최근 4턴 제외)를 LLM을 사용하여 요약.
   
   요약 프롬프트 (chatbot/prompts/summarize.md):
   "아래 대화 내용을 3~5줄로 요약해주세요.
   핵심 정보만 남기세요:
   - 사용자가 선택한 음식점
   - 투표/기록 등 실행된 행동
   - 사용자가 표현한 선호/비선호
   - 진행 중인 결정 사항
   
   [대화 내용]
   {conversation_text}
   
   [요약]"
   
   반환: 요약된 텍스트

3. apply_summary(history: ChatHistory, summary: str) -> ChatHistory:
   히스토리에 요약을 적용.
   
   변환 전:
   [system, user1, assistant1, user2, assistant2, ..., user10, assistant10]
   
   변환 후:
   [system, {"role": "system", "content": "[이전 대화 요약]\n{summary}"},
    user9, assistant9, user10, assistant10]
   
   최근 4턴(user+assistant 쌍)은 원본 유지.
   나머지는 요약 텍스트로 대체.

4. _extract_key_decisions(history: ChatHistory) -> list[str]:
   대화에서 핵심 의사결정 포인트를 추출.
   - "투표 완료: 한솥도시락"
   - "비선호 표시: 맥도날드"
   - "관심 표시: 서브웨이"
   요약에 포함되어야 할 팩트를 보장.

5. _estimate_compression_ratio(original_tokens: int, summary_tokens: int) -> float:
   압축 비율 계산 및 로깅.
   예: 2000 → 400 토큰 = 80% 압축

중요: 요약 과정에서 사용자의 선호도, 실행된 행동, 현재 상태를
절대 누락하지 않아야 함. 사실 정보만 유지하고 감정/수사는 제거.

타입 힌트, docstring, 로깅 포함해줘.
```

---

## 6. Step 4 — 시간대별 프로액티브 행동 유도

### Claude Code 프롬프트

```
chatbot/proactive_agent.py를 구현해줘.

ProactiveAgent 클래스:

사용자가 질문하기 전에 챗봇이 먼저 적절한 행동을 제안하는 역할.
시간대와 현재 상태에 따라 프로액티브 메시지를 생성.

1. get_proactive_message(user_id: str, team_id: str,
                          current_time: datetime = None) -> str | None:
   현재 시각과 상태에 따라 프로액티브 메시지 반환.
   제안할 것이 없으면 None.

시간대별 규칙:

09:30~10:00 (출근 직후):
  - 투표 세션이 열렸으면:
    "좋은 아침이에요! 🌅 오늘 점심 투표가 시작됐어요.
     어제 날씨가 좋았는데 오늘은 {날씨}이에요.
     추천받으시겠어요?"
  - 투표 세션이 아직 안 열렸으면: None

10:00~11:00 (투표 시간):
  - 사용자가 아직 투표 안 했으면:
    "🗳️ 아직 투표 안 하셨네요! 현재 {1위 음식점}이 {N}표로 앞서고 있어요.
     추천받거나 바로 투표하시겠어요?"
  - 이미 투표했으면: None

11:00~11:30 (투표 마감 임박):
  - 팀 참여율이 50% 미만이면:
    "⏰ 투표 마감 30분 전이에요! 아직 {미투표자}님이 투표하지 않았어요."
  - 참여율 50% 이상이면: None

12:00~13:00 (점심시간):
  - 투표 결과가 확정됐으면:
    "🎉 오늘의 점심은 {확정 음식점}! 맛있게 드세요~
     식후에 만족도 기록해주시면 다음 추천에 반영됩니다."
  - 확정 안 됐으면: None

13:00~14:00 (식후):
  - 오늘 식사 기록이 아직 없으면:
    "식사는 맛있으셨나요? 😋
     오늘 먹은 곳과 만족도를 기록하면 영양 분석에 반영돼요.
     '서브웨이 먹었어 4점' 같이 말씀해주세요!"
  - 이미 기록했으면: None

17:00~18:00 (퇴근 전):
  - 이번 주 기록이 3일 이상이면:
    "📊 이번 주 영양 리포트가 준비됐어요! 확인하시겠어요?"
  - 3일 미만이면: None

2. _check_vote_status(user_id, team_id) -> dict:
   투표 관련 상태 조회 (세션 열림 여부, 사용자 투표 여부, 현재 1위 등).

3. _check_meal_status(user_id) -> dict:
   오늘 식사 기록 여부 확인.

4. should_show_proactive(user_id: str, last_shown: datetime | None) -> bool:
   프로액티브 메시지 표시 여부 판단.
   같은 시간대에 이미 표시했으면 False (중복 방지).
   최소 1시간 간격.

타입 힌트, docstring 포함해줘.
```

---

## 7. Step 5 — 사용자 선호 프로필 학습

### Claude Code 프롬프트

```
chatbot/user_profile.py를 구현해줘.

먼저 database/models.py에 UserPreference 모델을 추가해줘:

UserPreference:
- id: Integer, PK
- user_id: String(50), FK → users.id, index=True
- preference_type: String(50)
  (category_preference / distance_preference / nutrition_goal /
   time_preference / dislike / allergy)
- preference_key: String(100)
  (예: "한식", "max_distance", "high_protein")
- preference_value: String(200)
  (예: "0.85", "300", "true")
- confidence: Float (0.0~1.0)
  학습된 선호도의 신뢰도. 데이터가 많을수록 높음.
- learned_from: String(20)
  (explicit: 사용자가 직접 말함 / implicit: 행동에서 추론)
- updated_at: DateTime

UserProfileManager 클래스:

1. learn_from_history(user_id: str, days: int = 60) -> dict:
   사용자의 과거 식사 기록, 투표 이력, 만족도에서 선호도를 학습.

   학습 항목:
   a. 카테고리 선호도:
      각 카테고리 방문 비율 + 평균 만족도 → confidence 산출
      예: 한식 60% (만족도 4.2) → {"key": "한식", "value": "0.85", "confidence": 0.8}

   b. 거리 선호도:
      평균 방문 거리, 최대 수용 거리
      예: 평균 250m, 최대 400m → {"key": "max_distance", "value": "400"}

   c. 영양 목표:
      주간 진단 결과에서 반복되는 패턴
      예: 3주 연속 단백질 부족 → {"key": "high_protein", "value": "true"}

   d. 시간 선호도:
      보통 몇 시에 투표/기록하는지
      예: 평균 투표 시각 10:20 → {"key": "vote_time", "value": "10:20"}

   e. 비선호 항목:
      거부권 이력 + 낮은 만족도(2점 이하)에서 추출
      예: 맥도날드 3회 거부 → {"key": "맥도날드", "type": "dislike"}

   반환: {"learned_preferences": 12, "new": 3, "updated": 9}

2. learn_from_conversation(user_id: str, message: str,
                            intent: dict) -> None:
   대화 중 사용자가 명시적으로 표현한 선호도를 즉시 학습.

   감지 패턴:
   - "나 한식 좋아해" → category_preference: 한식, confidence=0.95, learned_from=explicit
   - "매운 거 못 먹어" → dislike: 매운음식, confidence=0.95
   - "알레르기 있어 갑각류" → allergy: 갑각류, confidence=1.0
   - "멀리는 싫어" → distance_preference: max_distance=200
   - "다이어트 중이야" → nutrition_goal: low_calorie

3. get_profile(user_id: str) -> dict:
   사용자 프로필 조회.
   
   반환:
   {
     "user_id": "user1",
     "name": "김민수",
     "category_preferences": [
       {"category": "한식", "score": 0.85, "confidence": 0.8},
       {"category": "일식", "score": 0.72, "confidence": 0.6}
     ],
     "distance_preference": {"max": 400, "preferred": 250},
     "nutrition_goals": ["high_protein"],
     "dislikes": ["맥도날드", "매운음식"],
     "allergies": ["갑각류"],
     "personality": "보수적",  # 모험적/보수적/균형
     "total_data_points": 45,
     "profile_completeness": 0.75  # 0~1
   }

4. get_profile_summary_for_llm(user_id: str) -> str:
   LLM 시스템 프롬프트에 삽입할 사용자 프로필 요약 텍스트.
   
   예:
   "## 사용자 프로필: 김민수
   - 선호 카테고리: 한식(85%), 일식(72%)
   - 선호 거리: 250m 이내 (최대 400m)
   - 영양 목표: 고단백 식단 추구
   - 비선호: 맥도날드, 매운 음식
   - 알레르기: 갑각류
   - 식사 성향: 보수적 (같은 곳을 자주 방문)"

5. update_preference(user_id, pref_type, key, value, source) -> None:
   선호도 업데이트. 기존 항목이 있으면 갱신, 없으면 생성.
   confidence는 데이터 포인트 수에 비례하여 증가 (최대 0.95).

타입 힌트, docstring, 로깅 포함해줘.
```

---

## 8. Step 6 — 개인화 추천 강화

### Claude Code 프롬프트

```
chatbot/personalizer.py를 구현해줘.

RecommendationPersonalizer 클래스:

사용자 프로필을 기반으로 추천 결과의 순위를 개인화 조정하는 역할.

1. personalize(recommendations: list[dict],
               user_profile: dict) -> list[dict]:
   추천 결과에 개인화 보너스/페널티를 적용하여 재정렬.

   개인화 규칙:
   
   a. 선호 카테고리 보너스:
      사용자가 선호하는 카테고리의 음식점에 +5~15점 가산.
      category_score = preference_score * 15 (최대 15점)
      예: 한식 선호도 0.85 → 한식 음식점에 +12.75점

   b. 비선호 음식점 페널티:
      dislike 목록에 있는 음식점에 -20점 감산.

   c. 알레르기 제외:
      allergy 항목에 해당하는 메뉴는 완전 제외 (점수 0).

   d. 거리 선호 반영:
      preferred_distance보다 먼 곳에 -5점.
      max_distance보다 먼 곳에 -15점.

   e. 영양 목표 반영:
      high_protein 목표 + 고단백 음식점 → +10점.
      low_calorie 목표 + 저칼로리 음식점 → +10점.

   f. 탐험 보너스 (보수적 사용자 전용):
      personality="보수적"인 사용자에게
      방문 기록 없는 음식점 1개를 TOP 5에 포함.
      "새로운 곳도 한번 가보시는 건 어때요?" 추가.

   최종 점수로 재정렬 후 반환.
   각 음식점에 personalization_applied 필드를 추가:
   {"personal_bonus": +12.75, "reason": "선호 카테고리(한식)"}

2. generate_personal_highlights(restaurant: dict,
                                 user_profile: dict) -> list[str]:
   개인화된 추천 이유 문구 생성.
   
   예:
   - "김민수님이 좋아하는 한식이에요!"
   - "고단백 목표에 딱 맞는 메뉴예요"
   - "새로운 곳이에요! 한번 도전해보세요"
   - "평소 선호 거리(250m) 내에 있어요"

3. should_suggest_exploration(user_profile: dict) -> bool:
   사용자에게 새로운 곳을 추천할지 판단.
   보수적 성향 + 최근 7일 중 5일 이상 같은 카테고리 → True

4. get_personalization_summary(original: list, personalized: list) -> dict:
   개인화 전후 순위 변동 요약.
   반환: {"rank_changes": [{"name": "한솥", "before": 3, "after": 1}], ...}

타입 힌트, docstring 포함해줘.
```

---

## 9. Step 7 — 대화 품질 가드레일

### Claude Code 프롬프트

```
chatbot/guardrails.py를 구현해줘.

ResponseGuardrails 클래스:

LLM의 응답 품질을 검증하고, 할루시네이션(허위 정보 생성)을 방지하는 역할.

1. validate_response(response: str, context: dict,
                      tool_results: list[dict]) -> dict:
   LLM 응답을 검증.
   
   반환:
   {
     "valid": True,
     "issues": [],
     "corrected_response": None  # 수정이 필요하면 수정된 텍스트
   }

검증 규칙:

a. 음식점명 검증 (hallucination_check):
   응답에 포함된 음식점 이름이 실제 DB에 존재하는지 확인.
   존재하지 않는 음식점명 발견 시:
   → issues에 "unknown_restaurant: {이름}" 추가
   → 해당 부분을 제거하거나 "정보를 확인할 수 없는 음식점입니다"로 대체

b. 숫자 정합성 (number_consistency):
   응답의 거리/칼로리/점수가 Tool 결과와 일치하는지 확인.
   예: Tool 결과에서 "명동칼국수 320m"인데 응답에서 "200m"라고 하면
   → issues에 "distance_mismatch: 명동칼국수 320m→200m" 추가
   
   허용 오차: 거리 ±10%, 칼로리 ±5%, 점수 정확 일치

c. 행동 무단 실행 방지 (unauthorized_action):
   사용자가 요청하지 않았는데 "투표했습니다", "기록했습니다"라는
   응답이 포함되면:
   → issues에 "unauthorized_action_claim" 추가
   → 해당 문장 제거

d. 범위 이탈 방지 (scope_check):
   점심/음식과 무관한 주제로 벗어나면:
   → issues에 "off_topic" 추가
   → 경고는 하되 응답 자체는 유지

e. 개인정보 노출 방지 (privacy_check):
   다른 팀원의 구체적 식사 내역, 영양 상태를 노출하면:
   → issues에 "privacy_leak" 추가
   → 해당 부분을 "팀원" 으로 익명화

2. post_process(response: str, validation: dict) -> str:
   검증 결과에 따라 응답을 후처리.
   issues가 있으면 corrected_response를 반환.
   없으면 원본 response 반환.

3. log_quality_metrics(response: str, validation: dict,
                        tool_results: list) -> None:
   응답 품질 메트릭을 로깅 (추후 분석용):
   - hallucination_count: 존재하지 않는 정보 생성 횟수
   - accuracy_score: 숫자 정합성 비율
   - relevance_score: 주제 관련성
   - response_length: 응답 길이 (자)

타입 힌트, docstring, 로깅 포함해줘.
```

---

## 10. Step 8 — 테스트 및 평가

### Claude Code 프롬프트

```
tests/test_phase3_integration.py에 Phase 3 전체 테스트를 작성해줘.

ReferenceResolver:
1. test_rank_reference_first: "1번째 거" → 추천 1위 음식점
2. test_rank_reference_korean: "두 번째" → 추천 2위 음식점
3. test_rank_reference_last: "마지막 거" → 추천 목록 마지막
4. test_pronoun_reference_that: "거기로 할게" → 현재 탐색 중인 음식점
5. test_pronoun_last_mentioned: "아까 그거" → 히스토리에서 최근 음식점
6. test_negation_exclude: "그거 말고" → 현재 음식점 제외 + 재추천
7. test_negation_category: "한식 말고" → 카테고리 제외 조건
8. test_comparison: "1번이랑 3번 비교" → 두 음식점 정보 조회
9. test_continuation: "더 알려줘" → 현재 상태에서 추가 정보
10. test_resolve_failure: 해석 불가 → resolved=False + 안내 메시지

ConversationSummarizer:
11. test_should_summarize_by_tokens: 토큰 70% 초과 시 True
12. test_should_summarize_by_turns: 8턴 초과 시 True
13. test_apply_summary: 요약 적용 후 히스토리 길이 감소
14. test_key_decisions_preserved: 투표/기록 정보가 요약에 포함

ProactiveAgent:
15. test_morning_vote_prompt: 10:00 + 미투표 → 투표 안내
16. test_noon_record_prompt: 13:00 + 미기록 → 기록 안내
17. test_no_duplicate: 같은 시간대 중복 표시 방지
18. test_already_voted: 이미 투표 → None

UserProfileManager:
19. test_learn_category_preference: 한식 60% 방문 → 한식 선호
20. test_learn_explicit_preference: "매운 거 못 먹어" → dislike 등록
21. test_learn_allergy: "갑각류 알레르기" → allergy 등록
22. test_profile_completeness: 데이터 많을수록 completeness 증가

Personalizer:
23. test_favorite_category_bonus: 선호 카테고리 음식점 순위 상승
24. test_dislike_penalty: 비선호 음식점 순위 하락
25. test_allergy_exclusion: 알레르기 음식점 완전 제외
26. test_exploration_suggestion: 보수적 사용자에게 새 곳 추천

Guardrails:
27. test_hallucination_detection: 없는 음식점명 감지
28. test_number_mismatch: 거리 수치 불일치 감지
29. test_unauthorized_action: 무단 행동 주장 감지
30. test_privacy_protection: 타인 정보 노출 감지

E2E 멀티턴 시나리오:
31. test_e2e_recommend_then_explore:
    "추천해줘" → 5개 결과 →
    "2번째 거 상세" → 상세 정보 →
    "거기로 투표" → 투표 완료

32. test_e2e_exclude_and_retry:
    "추천해줘" → 5개 결과 →
    "1번 말고 다른 거" → 1번 제외 재추천

33. test_e2e_personalized_flow:
    사용자 프로필(한식 선호) →
    "추천해줘" → 한식이 상위에 위치

34. test_e2e_long_conversation_summary:
    10턴 대화 후 요약 적용 →
    이전 투표 정보가 유지되는지 확인

35. test_e2e_proactive_then_action:
    프로액티브 메시지 "투표 안 하셨네요" →
    "한솥에 투표할게" → 투표 완료

mock/fixture는 fixtures/mock_pipeline_data.py 활용.
pytest.mark.parametrize 적극 활용.
```

---

## 11. 트러블슈팅 가이드

**문제 1: 대명사 해석이 엉뚱한 음식점을 가리킴**

```
"거기로 할게"라고 했는데 의도한 음식점이 아닌 다른 곳을 선택해.
ReferenceResolver의 우선순위를 조정해줘:
1순위: EXPLORING 상태의 selected_restaurant (가장 최근 탐색한 곳)
2순위: RECOMMENDING 상태의 1위
3순위: 히스토리에서 가장 최근 언급된 곳

그리고 해석 결과를 사용자에게 확인하는 로직을 추가해줘:
쓰기 Tool(투표/기록)일 때만:
"한솥도시락에 투표하시는 게 맞으시죠?" → 예/아니오 대기
읽기 Tool일 때는 바로 실행.
```

**문제 2: 대화 요약 시 핵심 정보가 누락됨**

```
요약 후 "아까 투표한 곳이 어디였지?"라고 물으면 답을 못 해.
_extract_key_decisions()에서 다음 패턴을 반드시 보존하도록 해줘:
- "투표 완료: {음식점명}" (ACTION 결과)
- "식사 기록: {음식점명} {만족도}" (ACTION 결과)
- "비선호 표시: {음식점명}" (VETO 결과)
- "사용자 선호: {선호 내용}" (명시적 선호 표현)
이 패턴들은 요약에서 절대 제거되지 않도록 하드코딩해줘.
```

**문제 3: 프로액티브 메시지가 너무 자주 나옴**

```
챗봇이 매번 대화를 시작할 때마다 프로액티브 메시지를 보내.
last_shown 시각을 DB에 저장하고,
같은 타입의 메시지는 최소 2시간 간격으로 표시하도록 해줘.
또한 사용자가 직접 질문한 경우에는 프로액티브 메시지를 건너뛰어야 해.
```

**문제 4: 선호도 학습이 너무 빨리 수렴함**

```
3번 한식을 먹었더니 바로 "한식 선호도 95%"로 올라가.
confidence 계산에 최소 데이터 포인트 제한을 추가해줘:
- 5회 미만: confidence 최대 0.5
- 5~10회: confidence 최대 0.7
- 10~20회: confidence 최대 0.85
- 20회 이상: confidence 최대 0.95
또한 최근 데이터에 더 높은 가중치를 부여해줘 (시간 감쇠).
```

**문제 5: 가드레일이 정상 응답도 차단함**

```
LLM이 "명동칼국수에서 약 550칼로리를 섭취하실 수 있어요"라고 답했는데
가드레일이 "550 != 548 (Tool 결과)" 때문에 차단해.
숫자 검증의 허용 오차를 조정해줘:
- 거리: ±20m 또는 ±10%
- 칼로리: ±30kcal 또는 ±5%
- 점수: 정확 일치 필요
- "약", "대략", "정도" 같은 수식어가 있으면 검증 스킵
```

---

## 12. 체크리스트

### 구현 완료 확인

```
Phase 3의 구현 상태를 점검해줘.
아래 체크리스트 항목별로 현재 상태를 확인하고,
미완료 항목이 있으면 구현해줘.
```

**대화 상태 머신:**
- [ ] 8개 상태(IDLE~CONFIRMING) 정의
- [ ] Intent 기반 상태 전이 규칙
- [ ] 추천 결과 저장 및 rank별 조회
- [ ] 쓰기 Tool 실행 전 CONFIRMING 상태 전이

**후속 질문 / 대명사 해석:**
- [ ] 순서 참조: "1번째", "두 번째", "마지막 거"
- [ ] 대명사: "거기", "그거", "아까 그거"
- [ ] 부정: "그거 말고", "한식 말고"
- [ ] 비교: "1번이랑 3번 비교"
- [ ] 이어가기: "더 알려줘", "또 뭐 있어"
- [ ] 해석 실패 시 되묻기

**대화 요약 / 컨텍스트 압축:**
- [ ] 토큰 70% 초과 또는 8턴 초과 시 요약 트리거
- [ ] LLM 기반 대화 요약 생성
- [ ] 최근 4턴 원본 유지 + 나머지 요약 대체
- [ ] 핵심 의사결정(투표/기록/선호) 보존 보장

**프로액티브 행동 유도:**
- [ ] 09:30~10:00: 투표 시작 안내
- [ ] 10:00~11:00: 미투표 시 투표 독려
- [ ] 11:00~11:30: 마감 임박 알림
- [ ] 12:00~13:00: 확정 결과 + 식사 안내
- [ ] 13:00~14:00: 기록 독려
- [ ] 17:00~18:00: 주간 리포트 안내
- [ ] 같은 시간대 중복 표시 방지

**사용자 선호 프로필:**
- [ ] UserPreference DB 모델 정의
- [ ] 과거 이력 기반 암묵적 학습 (implicit)
- [ ] 대화 중 명시적 선호 감지 (explicit)
- [ ] 카테고리/거리/영양/비선호/알레르기 학습
- [ ] confidence 최소 데이터 포인트 제한
- [ ] LLM용 프로필 요약 텍스트 생성

**개인화 추천:**
- [ ] 선호 카테고리 보너스 (+5~15점)
- [ ] 비선호 음식점 페널티 (-20점)
- [ ] 알레르기 음식점 완전 제외
- [ ] 보수적 사용자에게 탐험 제안
- [ ] 개인화된 추천 이유 문구 생성

**가드레일:**
- [ ] 음식점명 할루시네이션 감지
- [ ] 숫자 정합성 검증 (허용 오차 포함)
- [ ] 무단 행동 주장 감지
- [ ] 범위 이탈 감지
- [ ] 개인정보 노출 방지 (익명화)
- [ ] 품질 메트릭 로깅

**core.py 통합:**
- [ ] 상태 머신을 chat() 흐름에 통합
- [ ] ReferenceResolver를 FOLLOWUP 처리에 통합
- [ ] ConversationSummarizer를 자동 트리거
- [ ] ProactiveAgent를 세션 시작 시 확인
- [ ] UserProfile을 시스템 프롬프트에 동적 주입
- [ ] Personalizer를 추천 결과에 적용
- [ ] Guardrails를 최종 응답 전에 실행

**테스트:**
- [ ] ReferenceResolver 10건
- [ ] Summarizer 4건
- [ ] ProactiveAgent 4건
- [ ] UserProfile 4건
- [ ] Personalizer 4건
- [ ] Guardrails 4건
- [ ] E2E 멀티턴 5건
- [ ] 전체 테스트 통과 (`pytest tests/ -v`)

---

<div align="center">

**Phase 3 완성 후, 챗봇은 단순한 도구가 아닌 "점심 동료"가 됩니다.**

*맥락을 기억하고, 취향을 학습하고, 먼저 말을 걸어주는.*
*"오늘 뭐 먹지?" — 이제 당신을 아는 AI가 답합니다.*

</div>
