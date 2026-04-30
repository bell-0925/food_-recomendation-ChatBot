"""
컨텍스트 빌더 — Intent에 따라 필요한 데이터를 조회하고
LLM에 전달할 컨텍스트 문자열을 조립합니다.
"""

import json
import logging
from datetime import datetime
from pathlib import Path

from chatbot.intent import Intent
from data.repositories.factory import (
    get_restaurant_repo,
    get_weather_repo,
    get_nutrition_repo,
    get_team_repo,
)

logger = logging.getLogger(__name__)

# 시스템 프롬프트 기본 경로
_DEFAULT_SYSTEM_PROMPT_PATH = Path(__file__).parent / "prompts" / "system.md"


class ContextBuilder:
    """
    Intent에 따라 필요한 데이터만 선택적으로 조회하여
    LLM에게 전달할 컨텍스트 문자열을 조립합니다.
    """

    def __init__(self, system_prompt_path=None):
        self._prompt_path = Path(system_prompt_path or _DEFAULT_SYSTEM_PROMPT_PATH)
        self._restaurant_repo = get_restaurant_repo()
        self._weather_repo = get_weather_repo()
        self._nutrition_repo = get_nutrition_repo()
        self._team_repo = get_team_repo()

    # ── 공개 메서드 ───────────────────────────────────

    def build_context(self, intent: dict, user_id: str, team_id: str) -> str:
        """
        Intent에 따라 필요한 데이터만 조회하여 컨텍스트 문자열을 반환합니다.

        Args:
            intent: IntentClassifier.classify() 반환값
            user_id: 사용자 ID
            team_id: 팀 ID

        Returns:
            LLM에 전달할 컨텍스트 문자열 (없으면 빈 문자열)
        """
        intent_type = intent.get("intent")
        entities = intent.get("entities", {})

        try:
            if intent_type in (Intent.RECOMMEND, Intent.RECOMMEND_CONDITIONAL):
                return self._build_recommend_context(user_id, team_id, entities)

            elif intent_type == Intent.QUERY_WEATHER:
                return self._build_weather_context()

            elif intent_type == Intent.QUERY_NUTRITION:
                return self._build_nutrition_context(user_id)

            elif intent_type == Intent.QUERY_VOTE:
                return self._build_vote_context(team_id)

            elif intent_type == Intent.QUERY_RESTAURANT:
                name = entities.get("restaurant_name", "")
                return self._build_restaurant_context(name)

            elif intent_type == Intent.QUERY_HISTORY:
                return self._build_history_context(team_id)

            else:
                # CHITCHAT, FOLLOWUP, ACTION_* — 컨텍스트 불필요
                return ""

        except Exception as e:
            logger.warning("컨텍스트 빌드 실패 (intent=%s): %s", intent_type, e)
            return ""

    def build_system_prompt(self, user_name: str = "사용자", team_name: str = "팀") -> str:
        """
        system.md를 읽어와 동적 변수를 치환한 시스템 프롬프트를 반환합니다.
        """
        try:
            template = self._prompt_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            logger.error("시스템 프롬프트 파일을 찾을 수 없습니다: %s", self._prompt_path)
            template = "당신은 점심 추천 AI 어시스턴트입니다."

        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        return template.replace("{datetime}", now).replace("{user_name}", user_name).replace("{team_name}", team_name)

    # ── 내부 빌더 ─────────────────────────────────────

    def _build_recommend_context(self, user_id: str, team_id: str, entities: dict) -> str:
        # 날씨: repo에서 가져오기
        weather_data = self._weather_repo.get_latest_cached() or {}
        condition = weather_data.get("condition", "unknown")
        temp = weather_data.get("temperature", "?")
        humidity = weather_data.get("humidity", "?")

        # 식사 기록: repo에서 가져오기
        meal_history = self._nutrition_repo.get_meal_history(user_id=user_id, days=7)

        # 추천 식당: repo에서 가져오기 (반경 1km)
        category = entities.get("category")
        recs = self._restaurant_repo.get_nearby(lat=37.4979, lng=127.0276, radius=1000, category=category)[:5]

        # 투표 현황
        from datetime import date
        votes = self._team_repo.get_vote_results(team_id=team_id, target_date=date.today())
        vote_summary = f"{len(votes)}개 식당 투표 중" if votes else "투표 없음"

        lines = [
            "[현재 상황]",
            f"날씨: {condition} {temp}°C, 습도 {humidity}%",
            f"최근 식사: {len(meal_history)}건 기록",
            f"팀 투표: {vote_summary}",
            "",
            self._format_recommendations(recs),
        ]
        return "\n".join(lines)

    def _build_weather_context(self) -> str:
        w = self._weather_repo.get_latest_cached() or {}
        cond = w.get("condition", "unknown")
        temp = w.get("temperature", "?")
        humidity = w.get("humidity", "?")
        desc = w.get("description", "")
        tips = {
            "rainy": "실내 식당 또는 배달 추천, 우산 필수",
            "cloudy": "국물 음식이나 따뜻한 메뉴 추천",
            "sunny": "야외 식당도 좋습니다",
            "hot": "시원한 냉면, 냉국수, 아이스 음료 추천",
        }
        tip = tips.get(cond, desc)
        return (
            f"[날씨 상세]\n"
            f"날씨: {cond}, 기온: {temp}°C\n"
            f"습도: {humidity}%\n"
            f"점심 팁: {tip}"
        )

    def _build_nutrition_context(self, user_id: str) -> str:
        history = self._nutrition_repo.get_meal_history(user_id=user_id, days=7)
        if not history:
            return f"[영양 진단 — {user_id}]\n기록 없음"
        avg_sat = sum(h.get("satisfaction", 0) or 0 for h in history) / len(history)
        return (
            f"[영양 진단 — {user_id}]\n"
            f"최근 7일 식사 기록: {len(history)}건\n"
            f"평균 만족도: {avg_sat:.1f}/5.0"
        )

    def _build_vote_context(self, team_id: str) -> str:
        from datetime import date
        votes = self._team_repo.get_vote_results(team_id=team_id, target_date=date.today())
        if not votes:
            return f"[투표 현황 — {team_id}]\n오늘 투표 없음"
        tally_lines = "\n".join(
            f"  - {v['name']}: {v['vote_count']}표" for v in votes
        )
        return f"[투표 현황 — {team_id}]\n현황:\n{tally_lines}"

    def _build_restaurant_context(self, name: str) -> str:
        if not name:
            return ""
        results = self._restaurant_repo.search(name)
        if not results:
            return f"[음식점 정보]\n{name}: 정보 없음"
        r = results[0]
        return (
            f"[{r['name']} 상세]\n"
            f"카테고리: {r.get('category', '?')}\n"
            f"주소: {r.get('address', '?')}\n"
            f"평점: {r.get('rating', '?')}\n"
            f"리뷰: {r.get('review_count', 0)}개\n"
            f"영업: {r.get('open_time', '?')} ~ {r.get('close_time', '?')}"
        )

    def _build_history_context(self, team_id: str) -> str:
        history = self._team_repo.get_visit_history(team_id=team_id, days=30)
        if not history:
            return "[최근 방문 이력]\n방문 기록 없음"
        lines = ["[최근 방문 이력]"]
        for h in history[:5]:
            lines.append(f"  {h['visited_at']}: {h.get('restaurant_id', '?')} ({h.get('headcount', '?')}명)")
        return "\n".join(lines)

    @staticmethod
    def _format_recommendations(recommendations: list) -> str:
        """추천 결과를 LLM 친화적 텍스트로 포맷팅."""
        if not recommendations:
            return "[추천 데이터]\n데이터 없음"

        lines = ["[추천 데이터]"]
        for i, r in enumerate(recommendations, 1):
            lines.append(
                f"{i}. {r['name']} | {r.get('category', '?')} | 평점 {r.get('rating', '?')} | {r.get('address', '')}"
            )
        return "\n".join(lines)
