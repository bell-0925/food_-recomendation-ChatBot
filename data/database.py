"""
SQLAlchemy 엔진 및 세션 관리.
DATABASE_URL 환경변수로 연결 대상을 결정한다.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///data/lunch_chatbot.db")

_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI/스크립트용 DB 세션 제너레이터."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """모든 테이블을 생성한다. 이미 존재하면 무시."""
    from data.repositories.sqlite import models  # noqa: F401 — 모델 등록
    Base.metadata.create_all(bind=engine)
