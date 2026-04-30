"""
Gemini 2.5 Flash 테스트 스크립트
- 기본 대화 테스트
- Tool Calling (Function Calling) 테스트
- 스트리밍 응답 테스트
- 점심 추천 챗봇 시나리오 테스트
"""

import os
import sys
import time
import json
import random
from pathlib import Path

# Windows 콘솔 UTF-8 출력 설정
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

from google import genai
from google.genai import types
from google.api_core.exceptions import ResourceExhausted, TooManyRequests

# ── env.env 파일 로드 ─────────────────────────────────
def load_env_file(filepath: str = None):
    """env.env 파일에서 환경변수를 읽어 os.environ에 설정합니다."""
    if filepath is None:
        filepath = Path(__file__).parent / "env.env"
    try:
        with open(filepath, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    os.environ.setdefault(key, value)
    except FileNotFoundError:
        print(f"⚠️  env 파일을 찾을 수 없습니다: {filepath}")

load_env_file()

# ── 설정 ──────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = "gemini-2.5-flash"

client = genai.Client(api_key=GEMINI_API_KEY)

# ── Tool Functions 정의 (기존 프로젝트와 동일한 8개) ──────
def get_lunch_recommendations(top_n: int = 5, category: str = None, max_distance: int = None) -> dict:
    """더미 데이터 — 실제 DB 연결 시 교체"""
    restaurants = [
        {"name": "명동칼국수", "score": 82, "distance": 320, "category": "한식", "protein": 20},
        {"name": "서브웨이",   "score": 78, "distance": 180, "category": "양식", "protein": 28},
        {"name": "한솥도시락", "score": 75, "distance": 120, "category": "한식", "protein": 18},
        {"name": "스시로",     "score": 71, "distance": 450, "category": "일식", "protein": 22},
        {"name": "본죽",       "score": 68, "distance": 160, "category": "한식", "protein": 12},
    ]
    if category:
        restaurants = [r for r in restaurants if r["category"] == category]
    if max_distance:
        restaurants = [r for r in restaurants if r["distance"] <= max_distance]
    return {"recommendations": restaurants[:top_n], "total": len(restaurants)}

def get_current_weather() -> dict:
    """더미 날씨 데이터"""
    return {
        "temp": 12, "sky": "흐림", "pop": 60,
        "dust_grade": "보통", "outdoor_comfort": "우산 챙기세요"
    }

def get_nutrition_diagnosis(user_id: str) -> dict:
    """더미 영양 진단"""
    return {
        "user_id": user_id,
        "recorded_days": 3,
        "avg_protein": 18,
        "overall_status": "단백질 부족",
        "overall_score": 65,
        "recommendations": ["단백질 섭취 늘리기", "나트륨 줄이기"]
    }

def get_restaurant_info(restaurant_name: str) -> dict:
    """더미 음식점 상세"""
    db = {
        "명동칼국수": {"kcal": 550, "protein": 20, "carbs": 78, "sodium": 1200, "distance": 320},
        "서브웨이":   {"kcal": 480, "protein": 28, "carbs": 52, "sodium": 900,  "distance": 180},
        "한솥도시락": {"kcal": 620, "protein": 18, "carbs": 85, "sodium": 1400, "distance": 120},
    }
    return db.get(restaurant_name, {"error": "음식점 정보 없음"})

def cast_vote(user_id: str, restaurant_name: str) -> dict:
    """더미 투표"""
    return {"status": "success", "message": f"{restaurant_name}에 투표 완료!", "user_id": user_id}

def get_vote_status(team_id: str) -> dict:
    """더미 투표 현황"""
    return {
        "team_id": team_id,
        "team_members": 5,
        "voted_count": 2,
        "tally": [
            {"restaurant_name": "한솥도시락", "votes": 2},
            {"restaurant_name": "서브웨이",   "votes": 1},
        ]
    }

def record_meal(user_id: str, restaurant_name: str, satisfaction: int = None) -> dict:
    """더미 식사 기록"""
    return {"status": "success", "message": f"식사 기록 완료 ({restaurant_name})", "satisfaction": satisfaction}

def get_visit_history(team_id: str, days: int = 7) -> dict:
    """더미 방문 이력"""
    return {
        "team_id": team_id, "days": days,
        "history": [
            {"date": "2026-04-25", "restaurant": "서브웨이",   "votes": 3},
            {"date": "2026-04-24", "restaurant": "명동칼국수", "votes": 4},
            {"date": "2026-04-23", "restaurant": "한솥도시락", "votes": 5},
        ]
    }

# Tool 함수 매핑
TOOL_MAP = {
    "get_lunch_recommendations": get_lunch_recommendations,
    "get_current_weather":       get_current_weather,
    "get_nutrition_diagnosis":   get_nutrition_diagnosis,
    "get_restaurant_info":       get_restaurant_info,
    "cast_vote":                 cast_vote,
    "get_vote_status":           get_vote_status,
    "record_meal":               record_meal,
    "get_visit_history":         get_visit_history,
}

# ── Gemini Tool 스펙 정의 ─────────────────────────────
TOOLS = types.Tool(function_declarations=[
    types.FunctionDeclaration(
        name="get_lunch_recommendations",
        description="오늘 날씨, 영양 밸런스, 팀 투표를 종합한 점심 추천 목록을 조회합니다",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "top_n":        types.Schema(type="INTEGER", description="추천 개수 (기본 5)"),
                "category":     types.Schema(type="STRING",  description="카테고리 필터 (한식/일식/양식)"),
                "max_distance": types.Schema(type="INTEGER", description="최대 거리(m)"),
            }
        )
    ),
    types.FunctionDeclaration(
        name="get_current_weather",
        description="현재 날씨와 미세먼지 정보를 조회합니다",
        parameters=types.Schema(type="OBJECT", properties={})
    ),
    types.FunctionDeclaration(
        name="get_nutrition_diagnosis",
        description="사용자의 이번 주 영양 섭취 진단 결과를 조회합니다",
        parameters=types.Schema(
            type="OBJECT",
            properties={"user_id": types.Schema(type="STRING", description="사용자 ID")},
            required=["user_id"]
        )
    ),
    types.FunctionDeclaration(
        name="get_restaurant_info",
        description="특정 음식점의 상세 정보(거리, 영양, 평점 등)를 조회합니다",
        parameters=types.Schema(
            type="OBJECT",
            properties={"restaurant_name": types.Schema(type="STRING", description="음식점 이름")},
            required=["restaurant_name"]
        )
    ),
    types.FunctionDeclaration(
        name="cast_vote",
        description="점심 투표를 행사합니다",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "user_id":         types.Schema(type="STRING", description="사용자 ID"),
                "restaurant_name": types.Schema(type="STRING", description="투표할 음식점 이름"),
            },
            required=["user_id", "restaurant_name"]
        )
    ),
    types.FunctionDeclaration(
        name="get_vote_status",
        description="현재 팀 투표 현황을 조회합니다",
        parameters=types.Schema(
            type="OBJECT",
            properties={"team_id": types.Schema(type="STRING", description="팀 ID")},
            required=["team_id"]
        )
    ),
    types.FunctionDeclaration(
        name="record_meal",
        description="식사 기록을 저장합니다",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "user_id":         types.Schema(type="STRING",  description="사용자 ID"),
                "restaurant_name": types.Schema(type="STRING",  description="음식점 이름"),
                "satisfaction":    types.Schema(type="INTEGER", description="만족도 1~5점"),
            },
            required=["user_id", "restaurant_name"]
        )
    ),
    types.FunctionDeclaration(
        name="get_visit_history",
        description="최근 방문 기록을 조회합니다",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "team_id": types.Schema(type="STRING",  description="팀 ID"),
                "days":    types.Schema(type="INTEGER", description="조회 기간(일)"),
            },
            required=["team_id"]
        )
    ),
])

# ── 시스템 프롬프트 ───────────────────────────────────
SYSTEM_PROMPT = """당신은 '점심 도우미'입니다. 직장인 팀의 점심 식사를 도와주는 친근한 AI 어시스턴트입니다.

역할:
- 날씨, 영양 상태, 팀 투표를 종합하여 최적의 점심을 추천합니다.
- 투표, 식사 기록 등의 행동을 대화로 수행할 수 있게 도와줍니다.
- 친근하고 간결하게 답변하되, 중요한 정보는 빠뜨리지 않습니다.

행동 규칙:
1. 추천 시 반드시 추천 이유를 함께 제공하세요.
2. 영양 관련 조언은 권고 수준으로 제공하고, 의학적 진단은 하지 마세요.
3. 투표나 기록 같은 행동은 사용자의 명시적 요청이 있을 때만 실행하세요.
4. 답변은 한국어로 하고, 이모지를 적절히 사용하세요.
5. 음식점 추천은 최대 5개까지만 제공하세요.

기본 컨텍스트:
- 사용자 ID: user_001
- 팀 ID: team_alpha
"""

# ── API 호출 래퍼 (429 자동 재시도) ──────────────────
def generate_with_retry(max_retries: int = 5, **kwargs):
    """429 TooManyRequests 발생 시 지수 백오프로 재시도"""
    for attempt in range(max_retries):
        try:
            return client.models.generate_content(**kwargs)
        except (ResourceExhausted, TooManyRequests) as e:
            if attempt == max_retries - 1:
                raise
            wait = (2 ** attempt) + random.uniform(0, 1)
            print(f"  ⏳ 429 Rate Limit — {wait:.1f}초 후 재시도 ({attempt + 1}/{max_retries})")
            time.sleep(wait)

# ── 핵심 챗봇 클래스 ─────────────────────────────────
class GeminiChatbot:
    def __init__(self):
        self.history = []
        self.config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            tools=[TOOLS],
            temperature=0.7,
        )

    def _execute_tool(self, fn_call) -> str:
        name = fn_call.name
        args = dict(fn_call.args) if fn_call.args else {}
        if name not in TOOL_MAP:
            return json.dumps({"error": f"알 수 없는 함수: {name}"}, ensure_ascii=False)
        result = TOOL_MAP[name](**args)
        return json.dumps(result, ensure_ascii=False)

    def chat(self, user_message: str) -> str:
        self.history.append(types.Content(
            role="user",
            parts=[types.Part(text=user_message)]
        ))

        # 1차 호출
        response = generate_with_retry(
            model=MODEL,
            contents=self.history,
            config=self.config,
        )

        # Tool Calling 루프
        while response.candidates[0].content.parts and \
              any(hasattr(p, "function_call") and p.function_call for p in response.candidates[0].content.parts):

            tool_parts = []
            result_parts = []

            for part in response.candidates[0].content.parts:
                if hasattr(part, "function_call") and part.function_call:
                    fn_call = part.function_call
                    result_str = self._execute_tool(fn_call)
                    print(f"  🔧 Tool 호출: {fn_call.name}({dict(fn_call.args) if fn_call.args else {}})")

                    tool_parts.append(part)
                    result_parts.append(types.Part(
                        function_response=types.FunctionResponse(
                            name=fn_call.name,
                            response={"result": result_str}
                        )
                    ))

            # 히스토리에 모델 응답 + tool 결과 추가
            self.history.append(types.Content(role="model", parts=tool_parts))
            self.history.append(types.Content(role="user", parts=result_parts))

            # 재호출
            response = generate_with_retry(
                model=MODEL,
                contents=self.history,
                config=self.config,
            )

        final_text = response.text or ""
        self.history.append(types.Content(
            role="model",
            parts=[types.Part(text=final_text)]
        ))
        return final_text


# ── 테스트 실행 ───────────────────────────────────────
def run_tests():
    print("=" * 60)
    print("  Gemini 2.5 Flash — 점심 챗봇 테스트")
    print("=" * 60)

    scenarios = [
        ("① 기본 추천",         "오늘 점심 뭐 먹을까?"),
        ("② 날씨 반영 추천",    "비가 올 것 같은데 따뜻한 거 추천해줘"),
        ("③ 영양 기반 추천",    "단백질 많은 메뉴로 추천해줘"),
        ("④ 음식점 상세 조회",  "명동칼국수 영양 정보 알려줘"),
        ("⑤ 투표 실행",         "한솥도시락에 투표할게"),
        ("⑥ 투표 현황 확인",    "지금 투표 현황 어때?"),
        ("⑦ 식사 기록",         "오늘 서브웨이 먹었어, 만족도 4점"),
    ]

    bot = GeminiChatbot()
    results = []

    for label, message in scenarios:
        print(f"\n{'─'*50}")
        print(f"🧪 {label}")
        print(f"👤 사용자: {message}")
        t0 = time.time()
        try:
            reply = bot.chat(message)
            elapsed = time.time() - t0
            print(f"🤖 Gemini: {reply}")
            print(f"⏱  응답 시간: {elapsed:.2f}초")
            results.append((label, "✅ 성공", elapsed))
        except Exception as e:
            elapsed = time.time() - t0
            print(f"❌ 오류: {e}")
            results.append((label, f"❌ 실패: {e}", elapsed))

        time.sleep(3)  # 시나리오 간 호출 간격

    # 결과 요약
    print(f"\n{'='*60}")
    print("  테스트 결과 요약")
    print(f"{'='*60}")
    for label, status, elapsed in results:
        print(f"  {label:20s} {status:10s}  {elapsed:.2f}s")

    success = sum(1 for _, s, _ in results if s.startswith("✅"))
    avg_time = sum(e for _, _, e in results) / len(results)
    print(f"\n  통과: {success}/{len(results)}   평균 응답 시간: {avg_time:.2f}초")
    print("=" * 60)


if __name__ == "__main__":
    if not GEMINI_API_KEY:
        print("⚠️  GEMINI_API_KEY를 찾을 수 없습니다.")
        print("    env.env 파일에 GEMINI_API_KEY = \"your-key-here\" 형식으로 입력하세요.")
    else:
        run_tests()
