"""
SQLAlchemy 2.0 ORM 모델 — 10개 테이블.
data/database.py의 Base를 상속한다.
"""
from datetime import datetime, date
from sqlalchemy import (
    String, Integer, Float, Text, DateTime, Date,
    ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from data.database import Base


class Restaurant(Base):
    __tablename__ = "restaurants"

    place_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str | None] = mapped_column(String)
    address: Mapped[str | None] = mapped_column(String)
    lat: Mapped[float | None] = mapped_column(Float)
    lng: Mapped[float | None] = mapped_column(Float)
    phone: Mapped[str | None] = mapped_column(String)
    rating: Mapped[float | None] = mapped_column(Float)
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    open_time: Mapped[str | None] = mapped_column(String)
    close_time: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class WeatherLog(Base):
    __tablename__ = "weather_logs"
    __table_args__ = (Index("idx_weather_recorded", "recorded_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    condition: Mapped[str | None] = mapped_column(String)
    temperature: Mapped[float | None] = mapped_column(Float)
    humidity: Mapped[int | None] = mapped_column(Integer)
    wind_speed: Mapped[float | None] = mapped_column(Float)
    description: Mapped[str | None] = mapped_column(Text)
    lat: Mapped[float | None] = mapped_column(Float)
    lng: Mapped[float | None] = mapped_column(Float)


class NutritionInfo(Base):
    __tablename__ = "nutrition_info"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    food_category: Mapped[str] = mapped_column(String, nullable=False)
    avg_calories: Mapped[float | None] = mapped_column(Float)
    avg_protein: Mapped[float | None] = mapped_column(Float)
    avg_carbs: Mapped[float | None] = mapped_column(Float)
    avg_fat: Mapped[float | None] = mapped_column(Float)
    avg_sodium: Mapped[float | None] = mapped_column(Float)
    health_score: Mapped[float | None] = mapped_column(Float)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MealHistory(Base):
    __tablename__ = "meal_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String, nullable=False)
    restaurant_id: Mapped[str | None] = mapped_column(ForeignKey("restaurants.place_id"))
    meal_name: Mapped[str | None] = mapped_column(String)
    eaten_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    calories: Mapped[float | None] = mapped_column(Float)
    satisfaction: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)


class Team(Base):
    __tablename__ = "teams"

    team_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    lat: Mapped[float | None] = mapped_column(Float)
    lng: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    team_id: Mapped[str | None] = mapped_column(ForeignKey("teams.team_id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class VoteSession(Base):
    __tablename__ = "vote_sessions"

    session_id: Mapped[str] = mapped_column(String, primary_key=True)
    team_id: Mapped[str | None] = mapped_column(ForeignKey("teams.team_id"))
    date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String, default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Vote(Base):
    __tablename__ = "votes"
    __table_args__ = (UniqueConstraint("session_id", "user_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str | None] = mapped_column(ForeignKey("vote_sessions.session_id"))
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.user_id"))
    restaurant_id: Mapped[str | None] = mapped_column(ForeignKey("restaurants.place_id"))
    voted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class VisitHistory(Base):
    __tablename__ = "visit_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    team_id: Mapped[str | None] = mapped_column(ForeignKey("teams.team_id"))
    restaurant_id: Mapped[str | None] = mapped_column(ForeignKey("restaurants.place_id"))
    visited_at: Mapped[date] = mapped_column(Date, nullable=False)
    headcount: Mapped[int | None] = mapped_column(Integer)


class Veto(Base):
    __tablename__ = "vetoes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.user_id"))
    restaurant_id: Mapped[str | None] = mapped_column(ForeignKey("restaurants.place_id"))
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
