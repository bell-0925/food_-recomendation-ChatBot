"""
LLM API 클라이언트 — 멀티 프로바이더 (Gemini / OpenAI / Claude)
환경변수 LLM_PROVIDER에 따라 자동으로 적절한 클라이언트를 선택합니다.
"""

import os
import time
import logging
import random
from abc import ABC, abstractmethod
from typing import Generator

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """통일된 LLM 에러 예외."""
    pass


# ── 기반 클래스 ───────────────────────────────────────
class BaseLLMClient(ABC):
    """모든 LLM 클라이언트의 공통 인터페이스."""

    @abstractmethod
    def chat(self, messages: list[dict], tools: list | None = None) -> str:
        """메시지 전송 및 전체 응답 반환."""
        ...

    @abstractmethod
    def chat_stream(self, messages: list[dict]) -> Generator[str, None, None]:
        """스트리밍 모드 — 토큰 단위로 yield."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """API 키 유효성 및 연결 확인."""
        ...

    @staticmethod
    def _backoff_wait(attempt: int) -> None:
        """지수 백오프 대기."""
        wait = (2 ** attempt) + random.uniform(0, 1)
        logger.warning("Rate limit — %.1f초 후 재시도 (시도 %d)", wait, attempt + 1)
        time.sleep(wait)


# ── Gemini 클라이언트 ──────────────────────────────────
class GeminiClient(BaseLLMClient):
    """Google Gemini API 클라이언트 (google-genai SDK)."""

    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            raise LLMError("GEMINI_API_KEY 환경변수를 설정해주세요.")

        from google import genai
        from google.genai import types

        self._genai = genai
        self._types = types
        self._client = genai.Client(api_key=api_key)
        self._model = os.getenv("LLM_MODEL", "models/gemini-2.5-flash-lite")
        logger.info("GeminiClient 초기화 (model=%s)", self._model)

    def chat(self, messages: list[dict], tools: list | None = None) -> str:
        """Gemini chat 호출. Tool Calling 루프 포함."""
        from google.api_core.exceptions import ResourceExhausted, TooManyRequests

        system_instruction, contents = self._convert_messages(messages)
        config_kwargs: dict = {"temperature": 0.7}
        if system_instruction:
            config_kwargs["system_instruction"] = system_instruction
        if tools:
            config_kwargs["tools"] = [self._types.Tool(function_declarations=tools)]

        config = self._types.GenerateContentConfig(**config_kwargs)

        for attempt in range(3):
            try:
                t0 = time.time()
                response = self._client.models.generate_content(
                    model=self._model,
                    contents=contents,
                    config=config,
                )
                elapsed = int((time.time() - t0) * 1000)
                logger.info("Gemini 응답 (model=%s, %dms)", self._model, elapsed)
                break
            except (ResourceExhausted, TooManyRequests):
                if attempt == 2:
                    raise LLMError("Gemini API rate limit 초과. 잠시 후 다시 시도해주세요.")
                self._backoff_wait(attempt)
            except Exception as e:
                raise LLMError(f"Gemini API 오류: {e}") from e

        # Tool Calling 루프
        while response.candidates and response.candidates[0].content.parts:
            fn_parts = [
                p for p in response.candidates[0].content.parts
                if hasattr(p, "function_call") and p.function_call
            ]
            if not fn_parts:
                break

            result_parts = []
            for part in fn_parts:
                fn = part.function_call
                fn_result = {"_tool_call": fn.name, "_args": dict(fn.args or {})}
                logger.debug("Tool 호출: %s(%s)", fn.name, dict(fn.args or {}))
                result_parts.append(
                    self._types.Part(
                        function_response=self._types.FunctionResponse(
                            name=fn.name,
                            response={"result": str(fn_result)},
                        )
                    )
                )

            contents = list(contents) + [
                self._types.Content(role="model", parts=fn_parts),
                self._types.Content(role="user", parts=result_parts),
            ]
            try:
                response = self._client.models.generate_content(
                    model=self._model, contents=contents, config=config
                )
            except Exception as e:
                raise LLMError(f"Gemini Tool 재호출 오류: {e}") from e

        return response.text or ""

    def chat_stream(self, messages: list[dict]) -> Generator[str, None, None]:
        """스트리밍 응답 생성."""
        system_instruction, contents = self._convert_messages(messages)
        config_kwargs: dict = {"temperature": 0.7}
        if system_instruction:
            config_kwargs["system_instruction"] = system_instruction

        config = self._types.GenerateContentConfig(**config_kwargs)
        try:
            for chunk in self._client.models.generate_content_stream(
                model=self._model, contents=contents, config=config
            ):
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            raise LLMError(f"Gemini 스트리밍 오류: {e}") from e

    def is_available(self) -> bool:
        try:
            self._client.models.generate_content(
                model=self._model, contents="ping"
            )
            return True
        except Exception:
            return False

    def _convert_messages(self, messages: list[dict]):
        """messages → (system_instruction, Gemini Contents 리스트)"""
        system_instruction = None
        contents = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                system_instruction = content
            elif role in ("user", "assistant"):
                gemini_role = "model" if role == "assistant" else "user"
                contents.append(
                    self._types.Content(
                        role=gemini_role,
                        parts=[self._types.Part(text=content)],
                    )
                )
        return system_instruction, contents


# ── OpenAI 클라이언트 ──────────────────────────────────
class OpenAIClient(BaseLLMClient):
    """OpenAI API 클라이언트."""

    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            raise LLMError("OPENAI_API_KEY 환경변수를 설정해주세요.")

        import openai
        self._client = openai.OpenAI(api_key=api_key)
        self._model = os.getenv("LLM_MODEL", "gpt-4o-mini")
        logger.info("OpenAIClient 초기화 (model=%s)", self._model)

    def chat(self, messages: list[dict], tools: list | None = None) -> str:
        kwargs: dict = {"model": self._model, "messages": messages}
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        for attempt in range(3):
            try:
                t0 = time.time()
                resp = self._client.chat.completions.create(**kwargs)
                elapsed = int((time.time() - t0) * 1000)
                logger.info("OpenAI 응답 (model=%s, %dms)", self._model, elapsed)
                break
            except Exception as e:
                if "429" in str(e) and attempt < 2:
                    self._backoff_wait(attempt)
                else:
                    raise LLMError(f"OpenAI API 오류: {e}") from e

        # tool_calls 처리
        msg = resp.choices[0].message
        if msg.tool_calls:
            logger.debug("OpenAI tool_calls: %s", [tc.function.name for tc in msg.tool_calls])

        return msg.content or ""

    def chat_stream(self, messages: list[dict]) -> Generator[str, None, None]:
        try:
            stream = self._client.chat.completions.create(
                model=self._model, messages=messages, stream=True
            )
            for chunk in stream:
                delta = chunk.choices[0].delta
                if delta.content:
                    yield delta.content
        except Exception as e:
            raise LLMError(f"OpenAI 스트리밍 오류: {e}") from e

    def is_available(self) -> bool:
        try:
            self._client.models.list()
            return True
        except Exception:
            return False


# ── Claude 클라이언트 ──────────────────────────────────
class ClaudeClient(BaseLLMClient):
    """Anthropic Claude API 클라이언트."""

    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise LLMError("ANTHROPIC_API_KEY 환경변수를 설정해주세요.")

        import anthropic
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = os.getenv("LLM_MODEL", "claude-haiku-4-5-20251001")
        logger.info("ClaudeClient 초기화 (model=%s)", self._model)

    def chat(self, messages: list[dict], tools: list | None = None) -> str:
        system = ""
        filtered = []
        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            else:
                filtered.append(msg)

        kwargs: dict = {
            "model": self._model,
            "max_tokens": 1024,
            "messages": filtered,
        }
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = tools

        for attempt in range(3):
            try:
                t0 = time.time()
                resp = self._client.messages.create(**kwargs)
                elapsed = int((time.time() - t0) * 1000)
                logger.info("Claude 응답 (model=%s, %dms)", self._model, elapsed)
                break
            except Exception as e:
                if "429" in str(e) and attempt < 2:
                    self._backoff_wait(attempt)
                else:
                    raise LLMError(f"Claude API 오류: {e}") from e

        text_blocks = [b.text for b in resp.content if hasattr(b, "text")]
        return " ".join(text_blocks)

    def chat_stream(self, messages: list[dict]) -> Generator[str, None, None]:
        system = ""
        filtered = []
        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            else:
                filtered.append(msg)

        kwargs: dict = {
            "model": self._model,
            "max_tokens": 1024,
            "messages": filtered,
        }
        if system:
            kwargs["system"] = system

        try:
            with self._client.messages.stream(**kwargs) as stream:
                for text in stream.text_stream:
                    yield text
        except Exception as e:
            raise LLMError(f"Claude 스트리밍 오류: {e}") from e

    def is_available(self) -> bool:
        try:
            self._client.messages.create(
                model=self._model, max_tokens=10,
                messages=[{"role": "user", "content": "ping"}]
            )
            return True
        except Exception:
            return False


# ── 팩토리 함수 ───────────────────────────────────────
def get_llm_client() -> BaseLLMClient:
    """
    LLM_PROVIDER 환경변수에 따라 적절한 클라이언트를 반환합니다.
    기본값: GeminiClient

    Returns:
        BaseLLMClient 인스턴스

    Raises:
        LLMError: API 키 미설정 또는 지원하지 않는 프로바이더
    """
    provider = os.getenv("LLM_PROVIDER", "gemini").lower()
    logger.info("LLM 클라이언트 초기화 (provider=%s)", provider)

    if provider == "gemini":
        return GeminiClient()
    elif provider == "openai":
        return OpenAIClient()
    elif provider in ("claude", "anthropic"):
        return ClaudeClient()
    else:
        raise LLMError(f"지원하지 않는 LLM 프로바이더: {provider}. (gemini | openai | claude)")
