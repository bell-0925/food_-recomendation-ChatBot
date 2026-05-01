import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from data.repositories.base import (
    BaseRestaurantRepo, BaseWeatherRepo,
    BaseNutritionRepo, BaseTeamRepo
)

def test_base_repos_are_abstract():
    """추상 클래스는 직접 인스턴스화 불가."""
    import inspect
    assert inspect.isabstract(BaseRestaurantRepo)
    assert inspect.isabstract(BaseWeatherRepo)
    assert inspect.isabstract(BaseNutritionRepo)
    assert inspect.isabstract(BaseTeamRepo)


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

# 테스트용 인메모리 DB 사용
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from data.database import init_db
from data.repositories.sqlite.restaurant_repo import SQLiteRestaurantRepo
from data.repositories.sqlite.weather_repo import SQLiteWeatherRepo
from data.repositories.sqlite.nutrition_repo import SQLiteNutritionRepo
from data.repositories.sqlite.team_repo import SQLiteTeamRepo
from data.repositories.sqlite.models import Restaurant, WeatherLog, NutritionInfo, Team, User
from data.database import SessionLocal
from datetime import datetime, date, timedelta, timezone


@pytest.fixture(autouse=True)
def setup_db():
    init_db()
    yield
    from data.database import Base, engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()


def test_restaurant_get_nearby(db):
    """반경 내 식당 반환."""
    db.add(Restaurant(
        place_id="p001", name="명동칼국수", category="한식",
        lat=37.4979, lng=127.0276, rating=4.5
    ))
    db.commit()
    repo = SQLiteRestaurantRepo()
    results = repo.get_nearby(lat=37.4979, lng=127.0276, radius=1000)
    assert len(results) == 1
    assert results[0]["name"] == "명동칼국수"


def test_restaurant_search(db):
    """키워드로 식당 검색."""
    db.add(Restaurant(place_id="p002", name="사쿠라스시", category="일식",
                      lat=37.498, lng=127.028))
    db.commit()
    repo = SQLiteRestaurantRepo()
    results = repo.search("스시")
    assert len(results) >= 1
    assert results[0]["name"] == "사쿠라스시"


def test_weather_get_latest_cached(db):
    """가장 최근 날씨 캐시 반환."""
    db.add(WeatherLog(
        recorded_at=datetime.now(timezone.utc), condition="sunny",
        temperature=24.0, humidity=55, lat=37.4979, lng=127.0276
    ))
    db.commit()
    repo = SQLiteWeatherRepo()
    result = repo.get_latest_cached()
    assert result is not None
    assert result["condition"] == "sunny"


def test_nutrition_record_and_retrieve(db):
    """식사 기록 저장 후 조회."""
    db.add(Team(team_id="t1", name="알파팀", lat=37.4979, lng=127.0276))
    db.add(User(user_id="u1", name="홍길동", team_id="t1"))
    db.add(Restaurant(place_id="p003", name="한솥도시락", category="한식",
                      lat=37.498, lng=127.028))
    db.commit()
    repo = SQLiteNutritionRepo()
    repo.record_meal(
        user_id="u1", restaurant_id="p003",
        meal_name="제육볶음", satisfaction=4
    )
    history = repo.get_meal_history(user_id="u1", days=7)
    assert len(history) == 1
    assert history[0]["meal_name"] == "제육볶음"
    assert history[0]["satisfaction"] == 4


def test_team_cast_vote(db):
    """투표 등록 및 결과 조회."""
    db.add(Team(team_id="t1", name="알파팀", lat=37.4979, lng=127.0276))
    db.add(User(user_id="u1", name="홍길동", team_id="t1"))
    db.add(Restaurant(place_id="p004", name="파스타리아", category="양식",
                      lat=37.498, lng=127.028))
    db.commit()
    repo = SQLiteTeamRepo()
    result = repo.cast_vote(user_id="u1", team_id="t1", restaurant_id="p004")
    assert result["restaurant_id"] == "p004"
    votes = repo.get_vote_results(team_id="t1", target_date=date.today())
    assert len(votes) >= 1


# ── 캐시 동작 테스트 ──────────────────────────────────

def test_weather_cache_hit_on_second_call(db):
    """두 번째 호출은 캐시에서 반환 (DB 재조회 없음)."""
    db.add(WeatherLog(
        recorded_at=datetime.now(timezone.utc), condition="cloudy",
        temperature=20.0, humidity=70, lat=37.4979, lng=127.0276
    ))
    db.commit()

    repo = SQLiteWeatherRepo()
    first  = repo.get_latest_cached()
    second = repo.get_latest_cached()

    assert first == second
    assert second["condition"] == "cloudy"


def test_weather_cache_invalidate(db):
    """캐시 무효화 후 재조회 시 새 데이터를 반환."""
    db.add(WeatherLog(
        recorded_at=datetime.now(timezone.utc) - timedelta(hours=1),
        condition="sunny", temperature=25.0, humidity=50,
        lat=37.4979, lng=127.0276
    ))
    db.commit()

    repo = SQLiteWeatherRepo()
    repo.get_latest_cached()  # 캐시 채우기

    # DB에 더 최신 데이터 추가
    db.add(WeatherLog(
        recorded_at=datetime.now(timezone.utc),
        condition="rainy", temperature=18.0, humidity=90,
        lat=37.4979, lng=127.0276
    ))
    db.commit()

    # 캐시 무효화 전: 여전히 sunny 반환
    assert repo.get_latest_cached()["condition"] == "sunny"

    # 캐시 무효화 후: rainy 반환
    repo._cache.invalidate()
    assert repo.get_latest_cached()["condition"] == "rainy"


def test_restaurant_cache_hit_on_second_call(db):
    """두 번째 get_nearby 호출은 캐시에서 반환."""
    db.add(Restaurant(
        place_id="p010", name="캐시테스트식당", category="한식",
        lat=37.4979, lng=127.0276, rating=4.0
    ))
    db.commit()

    repo = SQLiteRestaurantRepo()
    first  = repo.get_nearby(lat=37.4979, lng=127.0276, radius=1000)
    second = repo.get_nearby(lat=37.4979, lng=127.0276, radius=1000)

    assert first == second
    assert first[0]["name"] == "캐시테스트식당"


def test_restaurant_cache_separate_by_category(db):
    """category 파라미터가 다르면 별도 캐시 키로 관리."""
    db.add(Restaurant(place_id="p011", name="한식당", category="한식",
                      lat=37.4979, lng=127.0276, rating=4.0))
    db.add(Restaurant(place_id="p012", name="일식당", category="일식",
                      lat=37.4979, lng=127.0276, rating=4.0))
    db.commit()

    repo = SQLiteRestaurantRepo()
    all_results    = repo.get_nearby(lat=37.4979, lng=127.0276, radius=1000)
    korean_results = repo.get_nearby(lat=37.4979, lng=127.0276, radius=1000, category="한식")

    assert len(all_results) == 2
    assert len(korean_results) == 1
    assert korean_results[0]["name"] == "한식당"
