"""
Tool Functions 래퍼 — ToolExecutor 클래스가 SQLite Repository를 통해 실제 DB에 접근합니다.
"""

import logging

logger = logging.getLogger(__name__)

from data.repositories.factory import (
    get_restaurant_repo,
    get_team_repo,
    get_nutrition_repo,
    get_weather_repo,
)


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


class ToolExecutor:
    """Tool 함수를 실행하고 LLM 친화적 형식으로 결과를 반환합니다."""

    def __init__(self, user_id: str = "user_001", team_id: str = "team_alpha"):
        self._user_id = user_id
        self._team_id = team_id
        self._restaurant_repo = get_restaurant_repo()
        self._team_repo = get_team_repo()
        self._nutrition_repo = get_nutrition_repo()
        self._weather_repo = get_weather_repo()

    # ── 내부 Tool 메서드들 ────────────────────────────

    def _get_lunch_recommendations(self, top_n=5, category=None, max_distance=None):
        recs = self._restaurant_repo.get_nearby(
            lat=37.4979, lng=127.0276, radius=max_distance or 1000, category=category
        )
        return {"recommendations": recs[:top_n], "total": len(recs)}

    def _get_current_weather(self):
        w = self._weather_repo.get_latest_cached() or {}
        return {
            "condition": w.get("condition", "unknown"),
            "temp": w.get("temperature", "?"),
            "humidity": w.get("humidity", "?"),
            "description": w.get("description", ""),
        }

    def _get_nutrition_diagnosis(self, user_id=None):
        uid = user_id or self._user_id
        history = self._nutrition_repo.get_meal_history(user_id=uid, days=7)
        if not history:
            return {
                "user_id": uid,
                "recorded_days": 0,
                "overall_status": "기록 없음",
                "overall_score": 0,
                "recommendations": [],
            }
        avg_sat = sum(h.get("satisfaction", 0) or 0 for h in history) / len(history)
        return {
            "user_id": uid,
            "recorded_days": len(history),
            "overall_status": f"평균 만족도 {avg_sat:.1f}/5.0",
            "overall_score": int(avg_sat * 20),
            "recommendations": [],
        }

    def _get_restaurant_info(self, restaurant_name):
        results = self._restaurant_repo.search(restaurant_name)
        if not results:
            return {"error": f"{restaurant_name} 정보를 찾을 수 없습니다"}
        r = results[0]
        return {
            "name": r["name"],
            "category": r.get("category"),
            "address": r.get("address"),
            "rating": r.get("rating"),
            "review_count": r.get("review_count"),
            "open_time": r.get("open_time"),
            "close_time": r.get("close_time"),
        }

    def _cast_vote(self, user_id=None, restaurant_name=None):
        uid = user_id or self._user_id
        candidates = self._restaurant_repo.search(restaurant_name or "")
        if not candidates:
            return {"status": "error", "message": f"'{restaurant_name}' 식당을 찾을 수 없습니다"}
        rid = candidates[0]["place_id"]
        name = candidates[0]["name"]
        try:
            self._team_repo.cast_vote(user_id=uid, team_id=self._team_id, restaurant_id=rid)
            return {
                "status": "success",
                "message": f"✅ {name}에 투표 완료!",
                "user_id": uid,
                "restaurant": name,
            }
        except Exception as e:
            return {"status": "error", "message": f"투표 실패: {e}"}

    def _get_vote_status(self, team_id=None):
        from datetime import date
        tid = team_id or self._team_id
        votes = self._team_repo.get_vote_results(team_id=tid, target_date=date.today())
        tally = [{"restaurant_name": v["name"], "votes": v["vote_count"]} for v in votes]
        return {"team_id": tid, "team_members": 5, "voted_count": len(votes), "tally": tally}

    def _record_meal(self, user_id=None, restaurant_name=None, satisfaction=None):
        uid = user_id or self._user_id
        candidates = self._restaurant_repo.search(restaurant_name or "")
        rid = candidates[0]["place_id"] if candidates else None
        try:
            self._nutrition_repo.record_meal(
                user_id=uid,
                restaurant_id=rid,
                meal_name=restaurant_name or "",
                satisfaction=satisfaction or 3,
            )
            return {
                "status": "success",
                "message": f"✅ 식사 기록 완료 ({restaurant_name})",
                "satisfaction": satisfaction,
            }
        except Exception as e:
            return {"status": "error", "message": f"기록 실패: {e}"}

    def _get_visit_history(self, team_id=None, days=7):
        tid = team_id or self._team_id
        history = self._team_repo.get_visit_history(team_id=tid, days=days)
        formatted = [
            {
                "date": h["visited_at"],
                "restaurant": h.get("restaurant_id", "?"),
                "votes": h.get("headcount", 0),
            }
            for h in history
        ]
        return {"team_id": tid, "days": days, "history": formatted}

    # ── execute / format ──────────────────────────────

    def execute(self, tool_name: str, arguments: dict) -> dict:
        """
        tool_name에 해당하는 메서드를 실행합니다.

        Args:
            tool_name: TOOL_DEFINITIONS에 정의된 함수 이름
            arguments: LLM이 전달한 인수 딕셔너리

        Returns:
            LLM이 이해할 수 있는 평문 형식의 결과 dict
        """
        method_name = f"_{tool_name}"
        fn = getattr(self, method_name, None)
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
            formatted = []
            for i, r in enumerate(recs):
                name = r.get("name", "?")
                dist = r.get("distance", r.get("distance_m", "?"))
                score = r.get("score", r.get("rating", "?"))
                kcal = r.get("kcal", r.get("calories", "?"))
                formatted.append(f"{i+1}. {name} ({dist}m, {score}점, {kcal}kcal)")
            return {"result": "점심 추천 목록", "items": formatted, "total": raw.get("total", 0)}

        if tool_name == "get_current_weather":
            condition = raw.get("condition", raw.get("sky", "?"))
            temp = raw.get("temp", raw.get("temperature", "?"))
            humidity = raw.get("humidity", raw.get("pop", "?"))
            description = raw.get("description", raw.get("outdoor_comfort", ""))
            return {
                "result": f"{condition} {temp}°C, 습도 {humidity}%, {description}",
                "tip": description,
            }

        if tool_name == "get_nutrition_diagnosis":
            return {
                "result": raw["overall_status"],
                "score": raw["overall_score"],
                "recorded_days": raw.get("recorded_days", 0),
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
