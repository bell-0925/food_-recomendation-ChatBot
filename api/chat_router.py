"""
FastAPI 채팅 라우터
- POST /chat        — 비스트리밍 채팅
- GET  /chat/stream — SSE 스트리밍 채팅
- POST /chat/reset  — 대화 초기화
- GET  /chat/health — 서버 상태 확인
"""

import json
import time
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Generator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from chatbot.core import LunchChatbot

logger = logging.getLogger(__name__)

router = APIRouter()

# ── 세션 관리 ──────────────────────────────────────────
# user_id + team_id 조합으로 챗봇 인스턴스를 관리합니다.
_sessions: dict[str, dict] = {}  # key → {"chatbot": LunchChatbot, "last_used": datetime}
_SESSION_TIMEOUT_MINUTES = 30


def _session_key(user_id: str, team_id: str) -> str:
    return f"{user_id}::{team_id}"


def _get_or_create_chatbot(user_id: str, team_id: str) -> LunchChatbot:
    """세션에서 챗봇 인스턴스를 가져오거나 새로 생성합니다."""
    _cleanup_sessions()
    key = _session_key(user_id, team_id)
    if key not in _sessions:
        logger.info("새 챗봇 세션 생성: %s", key)
        _sessions[key] = {
            "chatbot": LunchChatbot(user_id=user_id, team_id=team_id),
            "last_used": datetime.now(),
        }
    else:
        _sessions[key]["last_used"] = datetime.now()
    return _sessions[key]["chatbot"]


def _cleanup_sessions() -> None:
    """30분 미사용 세션을 제거합니다."""
    cutoff = datetime.now() - timedelta(minutes=_SESSION_TIMEOUT_MINUTES)
    expired = [k for k, v in _sessions.items() if v["last_used"] < cutoff]
    for k in expired:
        del _sessions[k]
        logger.info("세션 만료 제거: %s", k)


# ── 요청/응답 모델 ────────────────────────────────────
class ChatRequest(BaseModel):
    user_id: str = "user_001"
    team_id: str = "team_alpha"
    message: str


class ResetRequest(BaseModel):
    user_id: str = "user_001"
    team_id: str = "team_alpha"


# ── 엔드포인트 ────────────────────────────────────────

@router.post("")
async def chat(req: ChatRequest):
    """
    비스트리밍 채팅 엔드포인트.

    Response: {"reply": "...", "intent": "RECOMMEND", "tool_used": [...]}
    """
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="메시지를 입력해주세요.")

    chatbot = _get_or_create_chatbot(req.user_id, req.team_id)

    # Intent 분류 (응답에 포함용)
    from chatbot.intent import IntentClassifier
    intent_info = IntentClassifier().classify(req.message)

    t0 = time.time()
    reply = chatbot.chat(req.message)
    elapsed_ms = int((time.time() - t0) * 1000)

    logger.info("chat 완료 (user=%s, %dms)", req.user_id, elapsed_ms)

    return {
        "reply": reply,
        "intent": intent_info["intent"],
        "confidence": intent_info["confidence"],
        "elapsed_ms": elapsed_ms,
    }


@router.get("/stream")
async def stream_chat(message: str, user_id: str = "user_001", team_id: str = "team_alpha"):
    """
    SSE 스트리밍 채팅 엔드포인트.

    각 이벤트 형식:
      data: {"type": "token", "content": "안"}
      data: {"type": "done", "content": "", "metadata": {...}}
    """
    if not message.strip():
        raise HTTPException(status_code=400, detail="메시지를 입력해주세요.")

    chatbot = _get_or_create_chatbot(user_id, team_id)

    def event_generator() -> Generator[str, None, None]:
        t0 = time.time()
        token_count = 0
        try:
            for token in chatbot.chat_stream(message):
                token_count += len(token)
                payload = json.dumps({"type": "token", "content": token}, ensure_ascii=False)
                yield f"data: {payload}\n\n"

            elapsed_ms = int((time.time() - t0) * 1000)
            done_payload = json.dumps({
                "type": "done",
                "content": "",
                "metadata": {
                    "elapsed_ms": elapsed_ms,
                    "chars": token_count,
                    "user_id": user_id,
                    "team_id": team_id,
                },
            }, ensure_ascii=False)
            yield f"data: {done_payload}\n\n"

        except Exception as e:
            logger.error("스트리밍 오류 (user=%s): %s", user_id, e)
            error_payload = json.dumps({"type": "error", "content": str(e)}, ensure_ascii=False)
            yield f"data: {error_payload}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.post("/reset")
async def reset_chat(req: ResetRequest):
    """대화 히스토리를 초기화합니다."""
    key = _session_key(req.user_id, req.team_id)
    if key in _sessions:
        _sessions[key]["chatbot"].reset()
    return {"status": "ok", "message": "대화가 초기화되었습니다."}


@router.get("/health")
async def health():
    """서버 상태 및 LLM 연결 정보를 반환합니다."""
    import os
    provider = os.getenv("LLM_PROVIDER", "gemini")
    model = os.getenv("LLM_MODEL", "gemini-2.5-flash")

    return {
        "status": "ok",
        "llm_provider": provider,
        "llm_model": model,
        "active_sessions": len(_sessions),
        "timestamp": datetime.now().isoformat(),
    }
