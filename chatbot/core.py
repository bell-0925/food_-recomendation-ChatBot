"""
LunchChatbot — 챗봇 모든 컴포넌트를 조립하는 메인 클래스
"""

import logging
from typing import Generator

from chatbot.history import ChatHistory
from chatbot.intent import IntentClassifier, Intent
from chatbot.context_builder import ContextBuilder
from chatbot.llm_client import get_llm_client, LLMError
from chatbot.tools import ToolExecutor

logger = logging.getLogger(__name__)


class LunchChatbot:
    """
    점심 추천 챗봇의 메인 클래스.
    Intent 분류 → 컨텍스트 빌드 → LLM 호출 → Tool 실행 → 응답 반환 파이프라인을 조율합니다.
    """

    def __init__(self, user_id: str = "user_001", team_id: str = "team_alpha"):
        """
        Args:
            user_id: 사용자 ID
            team_id: 팀 ID
        """
        self._user_id = user_id
        self._team_id = team_id

        self._context_builder = ContextBuilder()
        self._intent_classifier = IntentClassifier()
        self._tool_executor = ToolExecutor(user_id=user_id, team_id=team_id)

        # 시스템 프롬프트 로드
        system_prompt = self._context_builder.build_system_prompt(
            user_name=user_id, team_name=team_id
        )

        import os
        max_turns = int(os.getenv("CHATBOT_MAX_HISTORY", "10"))
        self._history = ChatHistory(max_turns=max_turns, system_prompt=system_prompt)

        # LLM 클라이언트 초기화 (에러 시 None, 이후 요청에서 안내 메시지 반환)
        try:
            self._llm = get_llm_client()
        except LLMError as e:
            logger.error("LLM 클라이언트 초기화 실패: %s", e)
            self._llm = None
            self._llm_error = str(e)
        else:
            self._llm_error = ""

        logger.info("LunchChatbot 초기화 (user=%s, team=%s)", user_id, team_id)

    # ── 공개 메서드 ───────────────────────────────────

    def chat(self, user_message: str) -> str:
        """
        전체 챗봇 파이프라인 실행 (비스트리밍).

        흐름:
          a. 사용자 메시지 히스토리 추가
          b. Intent 분류
          c. 컨텍스트 빌드
          d. 메시지 리스트 구성
          e. LLM 호출
          f. 최종 응답 히스토리 추가 & 반환
        """
        if not self._llm:
            return f"⚠️ LLM 연결 오류: {self._llm_error}"

        # a. 히스토리 추가
        self._history.add_user_message(user_message)

        # b. Intent 분류
        intent = self._intent_classifier.classify(user_message)
        logger.info("Intent: %s (%.2f)", intent["intent"], intent["confidence"])

        # c. 컨텍스트 빌드
        context = self._context_builder.build_context(intent, self._user_id, self._team_id)

        # d. 메시지 구성
        messages = self._build_messages(user_message, context)

        # e. LLM 호출
        try:
            reply = self._llm.chat(messages)
        except LLMError as e:
            reply = f"죄송합니다, 응답 생성 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.\n({e})"
            logger.error("LLM chat 오류: %s", e)

        # f. 히스토리 추가 & 반환
        self._history.add_assistant_message(reply)
        return reply

    def chat_stream(self, user_message: str) -> Generator[str, None, None]:
        """
        스트리밍 버전의 chat.
        Tool 실행은 스트리밍 시작 전에 완료하고, 결과를 컨텍스트에 포함합니다.

        흐름:
          a~d. chat()과 동일
          e. Tool이 필요하면 비스트리밍으로 먼저 실행
          f. Tool 결과를 컨텍스트에 추가
          g. 최종 응답을 스트리밍으로 생성
          h. 전체 응답을 히스토리에 추가
        """
        if not self._llm:
            yield f"⚠️ LLM 연결 오류: {self._llm_error}"
            return

        self._history.add_user_message(user_message)

        intent = self._intent_classifier.classify(user_message)
        context = self._context_builder.build_context(intent, self._user_id, self._team_id)

        # Tool이 필요한 Action Intent라면 미리 실행
        extra_context = self._run_action_tool(intent, user_message)
        if extra_context:
            context = (context + "\n\n" + extra_context).strip()

        messages = self._build_messages(user_message, context)

        full_reply = ""
        try:
            for token in self._llm.chat_stream(messages):
                full_reply += token
                yield token
        except LLMError as e:
            error_msg = f"\n⚠️ 스트리밍 오류: {e}"
            full_reply += error_msg
            yield error_msg
            logger.error("LLM stream 오류: %s", e)

        self._history.add_assistant_message(full_reply)

    def reset(self) -> None:
        """대화 히스토리를 초기화합니다."""
        self._history.clear()
        logger.info("LunchChatbot 대화 초기화 완료")

    # ── 내부 헬퍼 ─────────────────────────────────────

    def _build_messages(self, user_message: str, context: str) -> list[dict]:
        """
        히스토리 메시지에 컨텍스트를 포함하여 LLM에 전달할 메시지 리스트를 구성합니다.
        """
        messages = self._history.get_messages()

        if context:
            # 마지막 user 메시지에 컨텍스트 주입
            for i in range(len(messages) - 1, -1, -1):
                if messages[i]["role"] == "user":
                    messages[i] = {
                        "role": "user",
                        "content": f"{messages[i]['content']}\n\n{context}",
                    }
                    break

        return messages

    def _run_action_tool(self, intent: dict, user_message: str) -> str:
        """
        Action Intent (ACTION_VOTE, ACTION_RECORD, ACTION_VETO)인 경우
        Tool을 미리 실행하고 결과 컨텍스트 문자열을 반환합니다.
        """
        import json
        from chatbot.intent import Intent

        intent_type = intent.get("intent")
        entities = intent.get("entities", {})
        restaurant_name = entities.get("restaurant_name", "")

        if intent_type == Intent.ACTION_VOTE and restaurant_name:
            result = self._tool_executor.execute("cast_vote", {
                "user_id": self._user_id,
                "restaurant_name": restaurant_name,
            })
            return f"[투표 실행 결과]\n{json.dumps(result, ensure_ascii=False)}"

        if intent_type == Intent.ACTION_RECORD and restaurant_name:
            satisfaction = entities.get("satisfaction")
            args = {"user_id": self._user_id, "restaurant_name": restaurant_name}
            if satisfaction:
                args["satisfaction"] = satisfaction
            result = self._tool_executor.execute("record_meal", args)
            return f"[식사 기록 결과]\n{json.dumps(result, ensure_ascii=False)}"

        return ""
