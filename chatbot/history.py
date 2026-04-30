"""
대화 히스토리 관리
- 최대 턴 수 제한
- 시스템 프롬프트 유지
- 토큰 추정 및 자동 trim
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

_TOKEN_LIMIT = 4096
_KOREAN_CHAR_TOKEN_RATIO = 2  # 한글 1자 ≈ 2토큰


class ChatHistory:
    """
    대화 히스토리를 관리하는 클래스.

    내부적으로 Gemini/OpenAI/Claude 공통 메시지 형식
    [{"role": "...", "content": "..."}] 을 사용합니다.
    """

    def __init__(self, max_turns: int = 10, system_prompt: str = ""):
        """
        Args:
            max_turns: 최대 저장 턴 수 (사용자+어시스턴트 쌍 기준).
            system_prompt: 시스템 프롬프트 문자열.
        """
        self._max_turns = max_turns
        self._system_prompt = system_prompt
        self._messages: list[dict[str, Any]] = []
        self._last_recommendations: list[dict] | None = None
        logger.info("ChatHistory 초기화 (max_turns=%d)", max_turns)

    # ── 메시지 추가 ───────────────────────────────────

    def add_user_message(self, content: str) -> None:
        """사용자 메시지를 히스토리에 추가합니다."""
        self._messages.append({"role": "user", "content": content})
        self._auto_trim()

    def add_assistant_message(self, content: str) -> None:
        """어시스턴트 응답을 히스토리에 추가합니다."""
        self._messages.append({"role": "assistant", "content": content})
        self._auto_trim()

    def add_tool_result(self, tool_name: str, result: dict) -> None:
        """Tool 호출 결과를 히스토리에 저장합니다 (LLM 전달용)."""
        import json
        self._messages.append({
            "role": "tool",
            "tool_name": tool_name,
            "content": json.dumps(result, ensure_ascii=False),
        })

    # ── 조회 ─────────────────────────────────────────

    def get_messages(self) -> list[dict]:
        """
        LLM API 형식의 메시지 리스트를 반환합니다.
        시스템 프롬프트가 있으면 첫 항목으로 포함합니다.

        Returns:
            [{"role": "system", "content": "..."},
             {"role": "user", "content": "..."},
             ...]
        """
        result = []
        if self._system_prompt:
            result.append({"role": "system", "content": self._system_prompt})
        result.extend(self._messages)
        return result

    def get_last_recommendations(self) -> list[dict] | None:
        """가장 최근 추천 결과를 반환합니다 (FOLLOWUP 처리용)."""
        return self._last_recommendations

    def set_last_recommendations(self, recommendations: list[dict]) -> None:
        """추천 결과를 저장합니다."""
        self._last_recommendations = recommendations

    # ── 관리 ─────────────────────────────────────────

    def trim(self, max_turns: int | None = None) -> None:
        """
        오래된 대화를 삭제합니다. 시스템 프롬프트는 유지됩니다.

        Args:
            max_turns: 유지할 최대 턴 수. None이면 self._max_turns 사용.
        """
        limit = max_turns or self._max_turns
        # role이 "user" 또는 "assistant"인 메시지만 카운트
        dialog = [m for m in self._messages if m["role"] in ("user", "assistant")]
        # 최대 limit*2개 메시지(user+assistant 쌍)만 유지
        keep = limit * 2
        if len(dialog) > keep:
            self._messages = dialog[-keep:]
            logger.debug("히스토리 trim: %d개 메시지 유지", len(self._messages))

    def clear(self) -> None:
        """대화 히스토리를 초기화합니다 (시스템 프롬프트 유지)."""
        self._messages = []
        self._last_recommendations = None
        logger.info("ChatHistory 초기화 완료")

    def update_system_prompt(self, system_prompt: str) -> None:
        """시스템 프롬프트를 업데이트합니다."""
        self._system_prompt = system_prompt

    # ── 토큰 추정 ─────────────────────────────────────

    def get_token_estimate(self) -> int:
        """
        대략적인 토큰 수를 추정합니다.
        한글 1자 ≈ 2토큰, 영어/숫자 1자 ≈ 0.3토큰 기준.
        """
        total = 0
        all_msgs = self.get_messages()
        for msg in all_msgs:
            text = msg.get("content", "")
            if not isinstance(text, str):
                continue
            for ch in text:
                if "\uAC00" <= ch <= "\uD7A3":  # 한글
                    total += _KOREAN_CHAR_TOKEN_RATIO
                else:
                    total += 1
        return total

    def _auto_trim(self) -> None:
        """턴 수 초과 또는 토큰 초과 시 자동 trim을 트리거합니다."""
        dialog = [m for m in self._messages if m["role"] in ("user", "assistant")]
        if len(dialog) > self._max_turns * 2:
            logger.debug("대화 턴 수 초과(%d) — 자동 trim 실행", len(dialog))
            self.trim()
            return

        estimated = self.get_token_estimate()
        if estimated > _TOKEN_LIMIT:
            logger.warning("토큰 추정치 %d > %d — 자동 trim 실행", estimated, _TOKEN_LIMIT)
            self.trim()
