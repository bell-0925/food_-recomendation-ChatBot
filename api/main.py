"""
FastAPI 메인 앱 — 점심 추천 챗봇 API 서버
"""

import os
import sys
import logging
from pathlib import Path

# ── env.env 로드 ──────────────────────────────────────
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
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if val:
                    os.environ.setdefault(key, val)

_load_env()

# ── 로깅 설정 ──────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.chat_router import router as chat_router

app = FastAPI(
    title="점심 추천 챗봇 API",
    description="Gemini 2.5 Flash 기반 점심 추천 챗봇 API",
    version="1.0.0",
)

# CORS 설정 (React 개발 서버 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite 개발 서버
        "http://localhost:3000",  # CRA 개발 서버
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(chat_router, prefix="/api/chat", tags=["Chat"])


@app.get("/")
async def root():
    return {"message": "점심 추천 챗봇 API 서버", "docs": "/docs"}
