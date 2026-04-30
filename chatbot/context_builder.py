"""
컨텍스트 빌더 — Intent에 따라 필요한 데이터를 조회하고
LLM에 전달할 컨텍스트 문자열을 조립합니다.

Phase 1: 더미 데이터 사용 (실제 DB 연결 시 loader/scorer import로 교체)
"""

import json
import logging
from datetime import datetime
from pathlib import Path

from chatbot.intent import Intent

logger = logging.getLogger(__name__)

# 시스템 프롬프트 기본 경로
_DEFAULT_SYSTEM_PROMPT_PATH = Path(__file__).parent / "prompts" / "system.md"


# ── 더미 데이터 제공자 (실제 DB 연결 시 교체) ─────────────
def _dummy_weather() -> dict:
    return {"temp": 12, "sky": "흐림", "pop": 60, "dust_grade": "보통",
            "outdoor_comfort": "우산 챙기세요"}

def _dummy_nutrition(user_id: str) -> dict:
    return {"user_id": user_id, "recorded_days": 3, "avg_protein": 18,
            "overall_status": "단백질 부족", "overall_score": 65,
            "recommendations": ["단백질 섭취 늘리기", "나트륨 줄이기"]}

def _dummy_vote_status(team_id: str) -> dict:
    return {"team_id": team_id, "team_members": 5, "voted_count": 2,
            "tally": [{"restaurant_name": "한솥도시락", "votes": 2},
                      {"restaurant_name": "서브웨이", "votes": 1}]}

def _dummy_recommendations() -> list[dict]:
    return [
        {"name": "명동칼국수", "score": 82, "distance": 320, "category": "한식",
         "weather_score": 75, "nutrition_score": 68, "team_score": 85, "kcal": 550},
        {"name": "서브웨이",   "score": 78, "distance": 180, "category": "양식",
         "weather_score": 60, "nutrition_score": 82, "team_score": 65, "kcal": 380},
        {"name": "한솥도시락", "score": 75, "distance": 120, "category": "한식",
         "weather_score": 70, "nutrition_score": 65, "team_score": 80, "kcal": 620},
        {"name": "스시로",     "score": 71, "distance": 450, "category": "일식",
         "weather_score": 55, "nutrition_score": 75, "team_score": 60, "kcal": 480},
        {"name": "본죽",       "score": 68, "distance": 160, "category": "한식",
         "weather_score": 80, "nutrition_score": 60, "team_score": 55, "kcal": 320},
    ]

def _dummy_restaurant_info(name: str) -> dict:
    db = {
        "명동칼국수": {"kcal": 550, "protein": 20, "carbs": 78, "sodium": 1200, "distance": 320, "rating": 4.2},
        "서브웨이":   {"kcal": 480, "protein": 28, "carbs": 52, "sodium": 900,  "distance": 180, "rating": 4.0},
        "한솥도시락": {"kcal": 620, "protein": 18, "carbs": 85, "sodium": 1400, "distance": 120, "rating": 3.8},
    }
    return db.get(name, {})


class ContextBuilder:
    """
    Intent에 따라 필요한 데이터만 선택적으로 조회하여
    LLM에게 전달할 컨텍스트 문자열을 조립합니다.
    """

    def __init__(self, system_prompt_path: str | Path | None = None):
        self._prompt_path = Path(system_prompt_path or _DEFAULT_SYSTEM_PROMPT_PATH)

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
        weather = _dummy_weather()
        nutrition = _dummy_nutrition(user_id)
        vote = _dummy_vote_status(team_id)
        recs = _dummy_recommendations()

        # 카테고리 필터
        if entities.get("category"):
            recs = [r for r in recs if r["category"] == entities["category"]]

        lines = [
            "[현재 상황]",
            f"날씨: {weather['sky']} {weather['temp']}°C, 강수확률 {weather['pop']}%, 미세먼지 {weather['dust_grade']}. {weather['outdoor_comfort']}",
            f"영양상태: {nutrition['overall_status']} (점수 {nutrition['overall_score']}점, {nutrition['recorded_days']}일 기록)",
            f"팀 투표: {vote['voted_count']}/{vote['team_members']}명 투표 완료",
            "",
            self._format_recommendations(recs),
        ]
        return "\n".join(lines)

    def _build_weather_context(self) -> str:
        w = _dummy_weather()
        tips = {
            "흐림": "국물 음식이나 따뜻한 메뉴 추천",
            "비": "실내 식당 또는 배달 추천, 우산 필수",
            "맑음": "야외 식당도 좋습니다",
        }
        tip = tips.get(w["sky"], "")
        return (
            f"[날씨 상세]\n"
            f"날씨: {w['sky']}, 기온: {w['temp']}°C\n"
            f"강수확률: {w['pop']}%, 미세먼지: {w['dust_grade']}\n"
            f"점심 팁: {tip or w['outdoor_comfort']}"
        )

    def _build_nutrition_context(self, user_id: str) -> str:
        n = _dummy_nutrition(user_id)
        recs = ", ".join(n["recommendations"])
        return (
            f"[영양 진단 — {user_id}]\n"
            f"기록 일수: {n['recorded_days']}일\n"
            f"평균 단백질: {n['avg_protein']}g/일\n"
            f"종합 상태: {n['overall_status']} (점수 {n['overall_score']})\n"
            f"권장사항: {recs}"
        )

    def _build_vote_context(self, team_id: str) -> str:
        v = _dummy_vote_status(team_id)
        tally_lines = "\n".join(
            f"  - {t['restaurant_name']}: {t['votes']}표"
            for t in v["tally"]
        )
        return (
            f"[투표 현황 — {team_id}]\n"
            f"참여: {v['voted_count']}/{v['team_members']}명\n"
            f"현황:\n{tally_lines}"
        )

    def _build_restaurant_context(self, name: str) -> str:
        if not name:
            return ""
        info = _dummy_restaurant_info(name)
        if not info:
            return f"[음식점 정보]\n{name}: 정보 없음"
        return (
            f"[{name} 상세]\n"
            f"거리: {info.get('distance', '?')}m\n"
            f"칼로리: {info.get('kcal', '?')}kcal\n"
            f"단백질: {info.get('protein', '?')}g / 탄수화물: {info.get('carbs', '?')}g\n"
            f"나트륨: {info.get('sodium', '?')}mg\n"
            f"평점: {info.get('rating', '?')}"
        )

    def _build_history_context(self, team_id: str) -> str:
        history = [
            {"date": "2026-04-25", "restaurant": "서브웨이",   "votes": 3},
            {"date": "2026-04-24", "restaurant": "명동칼국수", "votes": 4},
            {"date": "2026-04-23", "restaurant": "한솥도시락", "votes": 5},
        ]
        lines = ["[최근 방문 이력]"]
        for h in history:
            lines.append(f"  {h['date']}: {h['restaurant']} ({h['votes']}명 투표)")
        return "\n".join(lines)

    @staticmethod
    def _format_recommendations(recommendations: list[dict]) -> str:
        """추천 결과를 LLM 친화적 텍스트로 포맷팅."""
        if not recommendations:
            return "[추천 데이터]\n데이터 없음"

        lines = ["[추천 데이터]"]
        for i, r in enumerate(recommendations, 1):
            ws = r.get("weather_score", "-")
            ns = r.get("nutrition_score", "-")
            ts = r.get("team_score", "-")
            lines.append(
                f"{i}. {r['name']} | {r['distance']}m | 종합{r['score']}점 "
                f"| 날씨{ws} 영양{ns} 팀{ts} | {r['category']} | {r['kcal']}kcal"
            )
        return "\n".join(lines)
