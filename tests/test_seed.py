# tests/test_seed.py
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import pytest
from data.database import init_db, Base, engine
from data.seed.seed_data import run_seed
from data.database import SessionLocal
from data.repositories.sqlite.models import (
    Restaurant, WeatherLog, NutritionInfo,
    MealHistory, Team, User, Vote, VisitHistory, Veto
)


@pytest.fixture(autouse=True)
def fresh_db():
    init_db()
    run_seed()
    yield
    Base.metadata.drop_all(bind=engine)


def test_seed_restaurants():
    with SessionLocal() as db:
        count = db.query(Restaurant).count()
    assert count == 20, f"식당 수가 20개여야 함 (실제: {count})"


def test_seed_weather():
    with SessionLocal() as db:
        count = db.query(WeatherLog).count()
    assert count == 7


def test_seed_team_users():
    with SessionLocal() as db:
        teams = db.query(Team).count()
        users = db.query(User).count()
    assert teams == 1
    assert users == 5


def test_seed_meal_history():
    with SessionLocal() as db:
        count = db.query(MealHistory).count()
    assert count == 25


def test_seed_votes():
    with SessionLocal() as db:
        count = db.query(Vote).count()
    assert count >= 15
