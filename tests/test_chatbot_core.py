"""
챗봇 통합 테스트
- IntentClassifier: 키워드 기반 분류 7건
- LLM 클라이언트: mock 3건
- LunchChatbot 통합: 3건
"""

import os
import sys
import json
import pytest
from unittest.mock import MagicMock, patch

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── env.env 로드 ──────────────────────────────────────
from pathlib import Path

def _load_env():
    env_path = Path(__file__).parent.parent / "env.env"
    if not env_path.exists():
        return
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, val = line.partition("=")
                key, val = key.strip(), val.strip().strip('"').strip("'")
                if val:
                    os.environ.setdefault(key, val)

_load_env()


# ═══════════════════════════════════════════════════════
# IntentClassifier 테스트 (7건)
# ═══════════════════════════════════════════════════════

from chatbot.intent import IntentClassifier, Intent


@pytest.fixture
def classifier():
    return IntentClassifier()


def test_intent_recommend_basic(classifier):
    """'오늘 뭐 먹지?' → RECOMMEND"""
    result = classifier.classify("오늘 뭐 먹지?")
    assert result["intent"] == Intent.RECOMMEND


def test_intent_recommend_conditional(classifier):
    """'비 오는데 추천' → RECOMMEND_CONDITIONAL, condition 포함"""
    result = classifier.classify("비 오는데 따뜻한 거 추천해줘")
    assert result["intent"] == Intent.RECOMMEND_CONDITIONAL
    assert result["entities"]["condition"] is not None


def test_intent_action_vote(classifier):
    """'한솥에 투표' → ACTION_VOTE, restaurant_name 추출"""
    result = classifier.classify("한솥도시락에 투표할게")
    assert result["intent"] == Intent.ACTION_VOTE
    assert result["entities"]["restaurant_name"] == "한솥도시락"


def test_intent_action_record(classifier):
    """'서브웨이 먹었어 4점' → ACTION_RECORD, satisfaction=4"""
    result = classifier.classify("서브웨이 먹었어, 만족도 4점")
    assert result["intent"] == Intent.ACTION_RECORD
    assert result["entities"]["satisfaction"] == 4


def test_intent_query_nutrition(classifier):
    """'이번 주 영양 어때?' → QUERY_NUTRITION"""
    result = classifier.classify("이번 주 영양 상태 어때?")
    assert result["intent"] == Intent.QUERY_NUTRITION


def test_intent_followup(classifier):
    """'2번째 거로 할게' → FOLLOWUP, number_ref=2"""
    result = classifier.classify("2번째 거로 할게")
    assert result["intent"] == Intent.FOLLOWUP
    assert result["entities"]["number_ref"] == 2


def test_intent_chitchat(classifier):
    """'안녕' → CHITCHAT"""
    result = classifier.classify("안녕!")
    assert result["intent"] == Intent.CHITCHAT


# ═══════════════════════════════════════════════════════
# LLM 클라이언트 테스트 (mock, 3건)
# ═══════════════════════════════════════════════════════

from chatbot.llm_client import GeminiClient, LLMError


def test_chat_basic():
    """mock 응답이 올바르게 반환되는지"""
    with patch("chatbot.llm_client.GeminiClient.__init__", return_value=None):
        client = GeminiClient.__new__(GeminiClient)
        # chat 메서드만 mock
        client.chat = MagicMock(return_value="테스트 응답입니다")
        result = client.chat([{"role": "user", "content": "테스트"}])
        assert result == "테스트 응답입니다"


def test_chat_stream():
    """스트리밍 응답이 토큰 단위로 yield되는지"""
    with patch("chatbot.llm_client.GeminiClient.__init__", return_value=None):
        client = GeminiClient.__new__(GeminiClient)
        tokens = ["오", "늘", "은", " ", "한식"]
        client.chat_stream = MagicMock(return_value=iter(tokens))

        result = list(client.chat_stream([{"role": "user", "content": "추천"}]))
        assert result == tokens
        assert "".join(result) == "오늘은 한식"


def test_connection_error():
    """서버 미연결 / API 키 없음 시 LLMError 발생"""
    original = os.environ.pop("GEMINI_API_KEY", None)
    try:
        with pytest.raises(LLMError, match="GEMINI_API_KEY"):
            GeminiClient()
    finally:
        if original:
            os.environ["GEMINI_API_KEY"] = original


# ═══════════════════════════════════════════════════════
# LunchChatbot 통합 테스트 (3건)
# ═══════════════════════════════════════════════════════

from chatbot.core import LunchChatbot


def _make_mock_llm(reply="테스트 응답입니다"):
    """LLM 클라이언트 mock 생성 헬퍼."""
    mock_llm = MagicMock()
    mock_llm.chat.return_value = reply
    mock_llm.chat_stream.return_value = iter(list(reply))
    return mock_llm


def test_full_recommend_flow():
    """'추천해줘' → 컨텍스트 빌드 → LLM 호출 → 응답 반환"""
    with patch("chatbot.core.get_llm_client") as mock_factory:
        mock_factory.return_value = _make_mock_llm("오늘은 명동칼국수 추천드려요! 🍜")
        bot = LunchChatbot(user_id="test_user", team_id="test_team")
        reply = bot.chat("오늘 점심 추천해줘")

    assert isinstance(reply, str)
    assert len(reply) > 0
    # LLM이 호출되었는지 확인
    bot._llm.chat.assert_called_once()


def test_full_vote_flow():
    """'한솥 투표' → Tool 실행 → DB 저장 → LLM 응답"""
    with patch("chatbot.core.get_llm_client") as mock_factory:
        mock_factory.return_value = _make_mock_llm("한솥도시락에 투표 완료했어요! 🗳️")
        bot = LunchChatbot(user_id="test_user", team_id="test_team")

        # ToolExecutor mock
        bot._tool_executor.execute = MagicMock(return_value={
            "result": "✅ 한솥도시락에 투표 완료!", "restaurant": "한솥도시락"
        })

        reply = bot.chat("한솥도시락에 투표할게")

    assert isinstance(reply, str)
    assert len(reply) > 0


def test_history_management():
    """10턴 이상 대화 후 trim 동작 확인"""
    with patch("chatbot.core.get_llm_client") as mock_factory:
        mock_factory.return_value = _make_mock_llm("응답")
        bot = LunchChatbot(user_id="test_user", team_id="test_team")

        # 12턴 대화 (user + assistant = 24 메시지)
        for i in range(12):
            bot.chat(f"테스트 메시지 {i}")

    # max_turns=10이므로 20개 이하 메시지만 유지
    history_msgs = bot._history.get_messages()
    non_system = [m for m in history_msgs if m["role"] != "system"]
    assert len(non_system) <= 20, f"히스토리 메시지가 너무 많습니다: {len(non_system)}"
