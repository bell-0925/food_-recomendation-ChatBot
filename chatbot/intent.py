"""
Intent 분류기 — 키워드 규칙 기반 (Phase 1)
Phase 2에서 LLM 기반으로 업그레이드 가능한 구조
"""

import re
import logging
from enum import Enum

logger = logging.getLogger(__name__)

# 더미 음식점 목록 (실제 DB 연결 시 교체)
_DEFAULT_RESTAURANTS = [
    "명동칼국수", "서브웨이", "한솥도시락", "한솥", "스시로",
    "본죽", "맥도날드", "버거킹", "롯데리아", "이삭토스트",
    "교촌치킨", "BBQ", "파리바게뜨",
]


class Intent(str, Enum):
    RECOMMEND = "RECOMMEND"
    RECOMMEND_CONDITIONAL = "RECOMMEND_CONDITIONAL"
    QUERY_RESTAURANT = "QUERY_RESTAURANT"
    QUERY_WEATHER = "QUERY_WEATHER"
    QUERY_NUTRITION = "QUERY_NUTRITION"
    QUERY_VOTE = "QUERY_VOTE"
    QUERY_HISTORY = "QUERY_HISTORY"
    ACTION_VOTE = "ACTION_VOTE"
    ACTION_RECORD = "ACTION_RECORD"
    ACTION_VETO = "ACTION_VETO"
    FOLLOWUP = "FOLLOWUP"
    CHITCHAT = "CHITCHAT"


# ── 키워드 규칙 ───────────────────────────────────────
_RECOMMEND_KW = ["추천", "뭐 먹", "뭐먹", "점심", "메뉴", "뭐 드실", "뭐드실"]
_CONDITIONAL_KW = ["한식", "일식", "양식", "중식", "분식", "가까운", "단백질",
                   "비", "따뜻", "시원", "가벼운", "든든", "칼로리", "저칼로리"]
_WEATHER_KW = ["날씨", "비", "미세먼지", "황사", "기온", "온도", "눈", "맑"]
_NUTRITION_KW = ["영양", "칼로리", "단백질", "이번 주", "이번주", "탄수화물", "나트륨"]
_VOTE_STATUS_KW = ["투표 현황", "투표현황", "누가 투표", "투표 상황", "몇 표"]
_HISTORY_KW = ["최근", "지난번", "히스토리", "방문", "갔던", "먹었던"]
_VOTE_ACTION_KW = ["투표", "한 표", "한표", "뽑"]
_RECORD_KW = ["먹었어", "먹었다", "먹음", "기록", "점 줄게", "점줄게", "만족도", "별점"]
_VETO_KW = ["거부권", "거부", "안 가", "싫어", "패스"]
_FOLLOWUP_KW = ["1번", "2번", "3번", "4번", "5번", "첫번째", "두번째", "세번째",
                "그거", "거기", "그 거", "다른 거", "다른거", "대신"]
_CHITCHAT_KW = ["안녕", "고마워", "감사", "ㅋㅋ", "ㅎㅎ", "잘 있어", "bye"]
_NUMBER_PATTERN = re.compile(r"(\d+)\s*번")


class IntentClassifier:
    """
    사용자 메시지를 분석하여 Intent를 분류하는 키워드 기반 분류기.

    Phase 2에서 classify() 내부만 LLM 호출로 교체 가능.
    """

    def __init__(self, restaurant_list: list[str] | None = None):
        """
        Args:
            restaurant_list: DB에서 로드한 음식점 이름 목록.
                             None이면 내장 기본 목록 사용.
        """
        self._restaurants = restaurant_list or _DEFAULT_RESTAURANTS
        logger.info("IntentClassifier 초기화 완료 (음식점 %d개)", len(self._restaurants))

    # ── 공개 메서드 ───────────────────────────────────

    def classify(self, message: str) -> dict:
        """
        메시지를 분석하여 Intent와 엔티티를 반환합니다.

        Returns:
            {
                "intent": Intent,
                "confidence": float,
                "entities": {
                    "category": str | None,
                    "restaurant_name": str | None,
                    "condition": str | None,
                    "number_ref": int | None,
                    "satisfaction": int | None,
                }
            }
        """
        msg = message.strip()
        entities = self._extract_entities(msg)

        intent, confidence = self._classify_intent(msg, entities)

        result = {
            "intent": intent,
            "confidence": confidence,
            "entities": entities,
        }
        logger.debug("Intent 분류: %s (%.2f) | 메시지: %s", intent, confidence, msg[:40])
        return result

    # ── 내부 메서드 ───────────────────────────────────

    def _classify_intent(self, msg: str, entities: dict) -> tuple[Intent, float]:
        """규칙 기반 Intent 분류. (Intent, confidence) 튜플 반환."""

        # 1. 거부권
        if self._has_any(msg, _VETO_KW):
            return Intent.ACTION_VETO, 0.9

        # 2. 식사 기록 (음식점명 있을 때 우선)
        if self._has_any(msg, _RECORD_KW):
            return Intent.ACTION_RECORD, 0.9

        # 3. 투표 실행 (음식점명 존재 + 투표 키워드)
        if self._has_any(msg, _VOTE_ACTION_KW) and entities["restaurant_name"]:
            return Intent.ACTION_VOTE, 0.9

        # 4. 투표 현황 조회
        if self._has_any(msg, _VOTE_STATUS_KW):
            return Intent.QUERY_VOTE, 0.9

        # 5. 날씨 조회 (투표보다 먼저)
        if self._has_any(msg, _WEATHER_KW) and not self._has_any(msg, _RECOMMEND_KW):
            return Intent.QUERY_WEATHER, 0.85

        # 6. 영양 조회
        if self._has_any(msg, _NUTRITION_KW) and not self._has_any(msg, _RECOMMEND_KW):
            return Intent.QUERY_NUTRITION, 0.85

        # 7. 방문 이력 조회
        if self._has_any(msg, _HISTORY_KW):
            return Intent.QUERY_HISTORY, 0.85

        # 8. 특정 음식점 정보 조회 (추천 키워드 없을 때)
        if entities["restaurant_name"] and not self._has_any(msg, _RECOMMEND_KW):
            return Intent.QUERY_RESTAURANT, 0.8

        # 9. FOLLOWUP (숫자 참조 또는 대명사)
        if entities["number_ref"] is not None or self._has_any(msg, _FOLLOWUP_KW):
            return Intent.FOLLOWUP, 0.8

        # 10. 조건부 추천 (추천 + 조건 키워드)
        if self._has_any(msg, _RECOMMEND_KW) and (
            self._has_any(msg, _CONDITIONAL_KW) or
            self._has_any(msg, _WEATHER_KW) or
            self._has_any(msg, _NUTRITION_KW)
        ):
            return Intent.RECOMMEND_CONDITIONAL, 0.85

        # 11. 일반 추천
        if self._has_any(msg, _RECOMMEND_KW):
            return Intent.RECOMMEND, 0.8

        # 12. CHITCHAT
        if self._has_any(msg, _CHITCHAT_KW):
            return Intent.CHITCHAT, 0.7

        # 기본값: 추천
        return Intent.RECOMMEND, 0.4

    def _extract_entities(self, msg: str) -> dict:
        """메시지에서 엔티티 추출."""
        entities = {
            "category": None,
            "restaurant_name": None,
            "condition": None,
            "number_ref": None,
            "satisfaction": None,
        }

        # 카테고리
        for cat in ["한식", "일식", "양식", "중식", "분식"]:
            if cat in msg:
                entities["category"] = cat
                break

        # 음식점명 (DB 목록 기반 매칭)
        for name in self._restaurants:
            if name in msg:
                entities["restaurant_name"] = name
                break

        # 조건 (날씨/기타)
        for cond in ["비 오", "비가", "눈", "맑", "흐림", "따뜻", "시원", "단백질", "가벼운"]:
            if cond in msg:
                entities["condition"] = cond.strip()
                break

        # 숫자 참조 ("2번째", "1번")
        m = _NUMBER_PATTERN.search(msg)
        if m:
            entities["number_ref"] = int(m.group(1))

        # 만족도 점수 ("4점", "3점")
        sat_m = re.search(r"(\d)\s*점", msg)
        if sat_m:
            val = int(sat_m.group(1))
            if 1 <= val <= 5:
                entities["satisfaction"] = val

        return entities

    @staticmethod
    def _has_any(text: str, keywords: list[str]) -> bool:
        return any(kw in text for kw in keywords)
