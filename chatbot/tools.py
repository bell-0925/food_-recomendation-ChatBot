"""
Tool Functions 래퍼 — 기존 더미 함수를 챗봇용 Tool로 래핑합니다.
실제 DB 연결 시 각 함수의 내부 구현만 교체하면 됩니다.
"""

import json
import logging

logger = logging.getLogger(__name__)

# ── 더미 데이터 함수 (실제 DB 연결 시 교체) ────────────
def _get_lunch_recommendations(top_n: int = 5, category: str | None = None, max_distance: int | None = None) -> dict:
    restaurants = [
        {"name": "명동칼국수", "score": 82, "distance": 320, "category": "한식", "kcal": 550, "protein": 20},
        {"name": "서브웨이",   "score": 78, "distance": 180, "category": "양식", "kcal": 380, "protein": 28},
        {"name": "한솥도시락", "score": 75, "distance": 120, "category": "한식", "kcal": 620, "protein": 18},
        {"name": "스시로",     "score": 71, "distance": 450, "category": "일식", "kcal": 480, "protein": 22},
        {"name": "본죽",       "score": 68, "distance": 160, "category": "한식", "kcal": 320, "protein": 12},
    ]
    if category:
        restaurants = [r for r in restaurants if r["category"] == category]
    if max_distance:
        restaurants = [r for r in restaurants if r["distance"] <= max_distance]
    return {"recommendations": restaurants[:top_n], "total": len(restaurants)}

def _get_current_weather() -> dict:
    return {"temp": 12, "sky": "흐림", "pop": 60, "dust_grade": "보통", "outdoor_comfort": "우산 챙기세요"}

def _get_nutrition_diagnosis(user_id: str) -> dict:
    return {"user_id": user_id, "recorded_days": 3, "avg_protein": 18,
            "overall_status": "단백질 부족", "overall_score": 65,
            "recommendations": ["단백질 섭취 늘리기", "나트륨 줄이기"]}

def _get_restaurant_info(restaurant_name: str) -> dict:
    db = {
        "명동칼국수": {"kcal": 550, "protein": 20, "carbs": 78, "sodium": 1200, "distance": 320, "rating": 4.2},
        "서브웨이":   {"kcal": 480, "protein": 28, "carbs": 52, "sodium": 900,  "distance": 180, "rating": 4.0},
        "한솥도시락": {"kcal": 620, "protein": 18, "carbs": 85, "sodium": 1400, "distance": 120, "rating": 3.8},
    }
    info = db.get(restaurant_name, {})
    if not info:
        return {"error": f"{restaurant_name} 정보를 찾을 수 없습니다"}
    return {"name": restaurant_name, **info}

def _cast_vote(user_id: str, restaurant_name: str) -> dict:
    return {"status": "success", "message": f"✅ {restaurant_name}에 투표 완료!", "user_id": user_id, "restaurant": restaurant_name}

def _get_vote_status(team_id: str) -> dict:
    return {"team_id": team_id, "team_members": 5, "voted_count": 2,
            "tally": [{"restaurant_name": "한솥도시락", "votes": 2}, {"restaurant_name": "서브웨이", "votes": 1}]}

def _record_meal(user_id: str, restaurant_name: str, satisfaction: int | None = None) -> dict:
    return {"status": "success", "message": f"✅ 식사 기록 완료 ({restaurant_name})", "satisfaction": satisfaction}

def _get_visit_history(team_id: str, days: int = 7) -> dict:
    return {"team_id": team_id, "days": days,
            "history": [
                {"date": "2026-04-25", "restaurant": "서브웨이",   "votes": 3},
                {"date": "2026-04-24", "restaurant": "명동칼국수", "votes": 4},
                {"date": "2026-04-23", "restaurant": "한솥도시락", "votes": 5},
            ]}


# ── Tool 정의 목록 ────────────────────────────────────
TOOL_DEFINITIONS: list[dict] = [
    {
        "name": "get_lunch_recommendations",
        "description": "오늘 날씨, 영양 밸런스, 팀 투표를 종합한 점심 추천 목록을 조회합니다",
        "parameters": {
            "type": "object",
            "properties": {
                "top_n":        {"type": "integer", "description": "추천 개수 (기본 5)"},
                "category":     {"type": "string",  "description": "카테고리 필터 (한식/일식/양식)"},
                "max_distance": {"type": "integer", "description": "최대 거리(m)"},
            },
        },
    },
    {
        "name": "get_current_weather",
        "description": "현재 날씨와 미세먼지 정보를 조회합니다",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "get_nutrition_diagnosis",
        "description": "사용자의 이번 주 영양 섭취 진단 결과를 조회합니다",
        "parameters": {
            "type": "object",
            "properties": {"user_id": {"type": "string", "description": "사용자 ID"}},
            "required": ["user_id"],
        },
    },
    {
        "name": "get_restaurant_info",
        "description": "특정 음식점의 상세 정보(거리, 영양, 평점 등)를 조회합니다",
        "parameters": {
            "type": "object",
            "properties": {"restaurant_name": {"type": "string", "description": "음식점 이름"}},
            "required": ["restaurant_name"],
        },
    },
    {
        "name": "cast_vote",
        "description": "점심 투표를 행사합니다",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id":         {"type": "string", "description": "사용자 ID"},
                "restaurant_name": {"type": "string", "description": "투표할 음식점 이름"},
            },
            "required": ["user_id", "restaurant_name"],
        },
    },
    {
        "name": "get_vote_status",
        "description": "현재 팀 투표 현황을 조회합니다",
        "parameters": {
            "type": "object",
            "properties": {"team_id": {"type": "string", "description": "팀 ID"}},
            "required": ["team_id"],
        },
    },
    {
        "name": "record_meal",
        "description": "식사 기록을 저장합니다",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id":         {"type": "string",  "description": "사용자 ID"},
                "restaurant_name": {"type": "string",  "description": "음식점 이름"},
                "satisfaction":    {"type": "integer", "description": "만족도 1~5점"},
            },
            "required": ["user_id", "restaurant_name"],
        },
    },
    {
        "name": "get_visit_history",
        "description": "최근 방문 기록을 조회합니다",
        "parameters": {
            "type": "object",
            "properties": {
                "team_id": {"type": "string",  "description": "팀 ID"},
                "days":    {"type": "integer", "description": "조회 기간(일)"},
            },
            "required": ["team_id"],
        },
    },
]

# 함수 라우팅 맵
_TOOL_MAP = {
    "get_lunch_recommendations": _get_lunch_recommendations,
    "get_current_weather":       _get_current_weather,
    "get_nutrition_diagnosis":   _get_nutrition_diagnosis,
    "get_restaurant_info":       _get_restaurant_info,
    "cast_vote":                 _cast_vote,
    "get_vote_status":           _get_vote_status,
    "record_meal":               _record_meal,
    "get_visit_history":         _get_visit_history,
}


class ToolExecutor:
    """Tool 함수를 실행하고 LLM 친화적 형식으로 결과를 반환합니다."""

    def __init__(self, user_id: str = "user_001", team_id: str = "team_alpha"):
        self._user_id = user_id
        self._team_id = team_id

    def execute(self, tool_name: str, arguments: dict) -> dict:
        """
        tool_name에 해당하는 함수를 실행합니다.

        Args:
            tool_name: TOOL_DEFINITIONS에 정의된 함수 이름
            arguments: LLM이 전달한 인수 딕셔너리

        Returns:
            LLM이 이해할 수 있는 평문 형식의 결과 dict
        """
        fn = _TOOL_MAP.get(tool_name)
        if fn is None:
            logger.warning("알 수 없는 Tool: %s", tool_name)
            return {"error": f"알 수 없는 함수: {tool_name}"}

        # user_id / team_id 자동 주입
        if tool_name in ("get_nutrition_diagnosis", "cast_vote", "record_meal"):
            arguments.setdefault("user_id", self._user_id)
        if tool_name in ("get_vote_status", "get_visit_history"):
            arguments.setdefault("team_id", self._team_id)

        try:
            raw = fn(**arguments)
            result = self._format_for_llm(tool_name, raw)
            logger.debug("Tool 실행 완료: %s → %s", tool_name, str(result)[:80])
            return result
        except Exception as e:
            logger.error("Tool 실행 오류 (%s): %s", tool_name, e)
            return {"error": f"'{tool_name}' 실행 중 오류가 발생했습니다: {e}"}

    def _format_for_llm(self, tool_name: str, raw: dict) -> dict:
        """Tool 결과를 LLM 친화적 dict로 변환합니다."""
        # 에러는 그대로 반환
        if "error" in raw:
            return raw

        if tool_name == "get_lunch_recommendations":
            recs = raw.get("recommendations", [])
            formatted = [
                f"{i+1}. {r['name']} ({r['distance']}m, {r['score']}점, {r['kcal']}kcal)"
                for i, r in enumerate(recs)
            ]
            return {"result": "점심 추천 목록", "items": formatted, "total": raw.get("total", 0)}

        if tool_name == "get_current_weather":
            return {
                "result": f"{raw['sky']} {raw['temp']}°C, 강수확률 {raw['pop']}%, 미세먼지 {raw['dust_grade']}",
                "tip": raw.get("outdoor_comfort", ""),
            }

        if tool_name == "get_nutrition_diagnosis":
            return {
                "result": raw["overall_status"],
                "score": raw["overall_score"],
                "avg_protein_g": raw["avg_protein"],
                "advice": raw.get("recommendations", []),
            }

        if tool_name == "get_restaurant_info":
            return raw  # 이미 평탄한 구조

        if tool_name == "cast_vote":
            return {"result": raw["message"], "restaurant": raw.get("restaurant", "")}

        if tool_name == "get_vote_status":
            tally = raw.get("tally", [])
            summary = ", ".join(f"{t['restaurant_name']} {t['votes']}표" for t in tally)
            return {
                "result": f"{raw['voted_count']}/{raw['team_members']}명 투표",
                "tally": summary,
            }

        if tool_name == "record_meal":
            return {"result": raw["message"], "satisfaction": raw.get("satisfaction")}

        if tool_name == "get_visit_history":
            history = raw.get("history", [])
            lines = [f"{h['date']}: {h['restaurant']} ({h['votes']}명)" for h in history]
            return {"result": "최근 방문 이력", "history": lines}

        return raw

    def get_tool_definitions(self) -> list[dict]:
        """TOOL_DEFINITIONS 반환."""
        return TOOL_DEFINITIONS
