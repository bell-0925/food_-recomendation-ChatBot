"""
점심 추천 챗봇 — 터미널 대화형
- Gemini 2.5 Flash + Tool Calling
- 5 RPM 제한 대응: 지수 백오프 자동 재시도
"""

import os
import sys
import time
import json
import random
from pathlib import Path

# Windows 콘솔 UTF-8
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

from google import genai
from google.genai import types
from google.api_core.exceptions import ResourceExhausted, TooManyRequests

# ── env.env 로드 ───────────────────────────────────────
def load_env_file(filepath=None):
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
                    os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
    except FileNotFoundError:
        print(f"⚠️  env 파일을 찾을 수 없습니다: {filepath}")

load_env_file()

# ── 설정 ──────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = "gemini-2.5-flash"

if not GEMINI_API_KEY:
    print("⚠️  GEMINI_API_KEY 없음. env.env 파일을 확인하세요.")
    sys.exit(1)

client = genai.Client(api_key=GEMINI_API_KEY)

# ── Tool Functions ─────────────────────────────────────
def get_lunch_recommendations(top_n: int = 5, category: str = None, max_distance: int = None) -> dict:
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
    return {"temp": 12, "sky": "흐림", "pop": 60, "dust_grade": "보통", "outdoor_comfort": "우산 챙기세요"}

def get_nutrition_diagnosis(user_id: str) -> dict:
    return {
        "user_id": user_id, "recorded_days": 3, "avg_protein": 18,
        "overall_status": "단백질 부족", "overall_score": 65,
        "recommendations": ["단백질 섭취 늘리기", "나트륨 줄이기"],
    }

def get_restaurant_info(restaurant_name: str) -> dict:
    db = {
        "명동칼국수": {"kcal": 550, "protein": 20, "carbs": 78, "sodium": 1200, "distance": 320},
        "서브웨이":   {"kcal": 480, "protein": 28, "carbs": 52, "sodium": 900,  "distance": 180},
        "한솥도시락": {"kcal": 620, "protein": 18, "carbs": 85, "sodium": 1400, "distance": 120},
    }
    return db.get(restaurant_name, {"error": "음식점 정보 없음"})

def cast_vote(user_id: str, restaurant_name: str) -> dict:
    return {"status": "success", "message": f"{restaurant_name}에 투표 완료!", "user_id": user_id}

def get_vote_status(team_id: str) -> dict:
    return {
        "team_id": team_id, "team_members": 5, "voted_count": 2,
        "tally": [
            {"restaurant_name": "한솥도시락", "votes": 2},
            {"restaurant_name": "서브웨이",   "votes": 1},
        ],
    }

def record_meal(user_id: str, restaurant_name: str, satisfaction: int = None) -> dict:
    return {"status": "success", "message": f"식사 기록 완료 ({restaurant_name})", "satisfaction": satisfaction}

def get_visit_history(team_id: str, days: int = 7) -> dict:
    return {
        "team_id": team_id, "days": days,
        "history": [
            {"date": "2026-04-28", "restaurant": "서브웨이",   "votes": 3},
            {"date": "2026-04-27", "restaurant": "명동칼국수", "votes": 4},
            {"date": "2026-04-26", "restaurant": "한솥도시락", "votes": 5},
        ],
    }

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

# ── Gemini Tool 스펙 ───────────────────────────────────
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

# ── API 호출 래퍼 (429 자동 재시도) ───────────────────
def generate_with_retry(max_retries: int = 5, **kwargs):
    for attempt in range(max_retries):
        try:
            return client.models.generate_content(**kwargs)
        except (ResourceExhausted, TooManyRequests) as e:
            if attempt == max_retries - 1:
                raise
            wait = (2 ** attempt) + random.uniform(0, 1)
            print(f"\n  ⏳ Rate Limit — {wait:.1f}초 후 재시도 ({attempt + 1}/{max_retries})...")
            time.sleep(wait)

# ── 챗봇 클래스 ───────────────────────────────────────
class LunchChatbot:
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

        response = generate_with_retry(
            model=MODEL,
            contents=self.history,
            config=self.config,
        )

        # Tool Calling 루프
        while (
            response.candidates[0].content.parts
            and any(
                hasattr(p, "function_call") and p.function_call
                for p in response.candidates[0].content.parts
            )
        ):
            tool_parts, result_parts = [], []

            for part in response.candidates[0].content.parts:
                if hasattr(part, "function_call") and part.function_call:
                    fn_call = part.function_call
                    result_str = self._execute_tool(fn_call)
                    print(f"  🔧 {fn_call.name}({dict(fn_call.args) if fn_call.args else {}})")
                    tool_parts.append(part)
                    result_parts.append(types.Part(
                        function_response=types.FunctionResponse(
                            name=fn_call.name,
                            response={"result": result_str}
                        )
                    ))

            self.history.append(types.Content(role="model", parts=tool_parts))
            self.history.append(types.Content(role="user",  parts=result_parts))

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

    def reset(self):
        self.history = []
        print("  🔄 대화 기록이 초기화됐습니다.")

# ── 메인 루프 ──────────────────────────────────────────
def main():
    print("=" * 55)
    print("  🍱 점심 도우미 챗봇")
    print("=" * 55)
    print("  명령어: 'reset' — 대화 초기화 | 'quit' — 종료")
    print("-" * 55)

    bot = LunchChatbot()

    while True:
        try:
            user_input = input("\n👤 나: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\n  챗봇을 종료합니다. 맛있는 점심 드세요! 🍽️")
            break

        if not user_input:
            continue

        if user_input.lower() == "quit":
            print("  챗봇을 종료합니다. 맛있는 점심 드세요! 🍽️")
            break

        if user_input.lower() == "reset":
            bot.reset()
            continue

        print("  ⏳ 생각 중...", end="\r")
        try:
            reply = bot.chat(user_input)
            print(f"             \r", end="")  # 로딩 텍스트 지우기
            print(f"\n🤖 도우미: {reply}")
        except Exception as e:
            print(f"\n❌ 오류 발생: {e}")


if __name__ == "__main__":
    main()
