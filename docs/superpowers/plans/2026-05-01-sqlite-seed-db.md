# SQLite Seed DB Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** SQLite DB에 가상 데이터를 채워넣고, Repository Pattern으로 chatbot이 실제 데이터를 읽고 쓰도록 연동한다.

**Architecture:** `data/` 패키지에 SQLAlchemy 2.0 ORM 모델과 4개의 추상 Repository 인터페이스를 정의한다. SQLite 구현체가 기본값이고 `DATA_SOURCE=api` 환경변수로 향후 실제 API 구현체로 교체 가능하다. `chatbot/context_builder.py`와 `chatbot/tools.py`의 더미 함수들을 repo 팩토리 호출로 교체한다.

**Tech Stack:** SQLAlchemy 2.0, SQLite3, Python 3.11+, pytest

---

## 파일 구조

### 새로 생성
```
data/
├── __init__.py
├── database.py                          # 엔진/세션 관리
├── repositories/
│   ├── __init__.py
│   ├── base.py                          # 추상 인터페이스 4개
│   ├── factory.py                       # DATA_SOURCE 기반 팩토리
│   ├── sqlite/
│   │   ├── __init__.py
│   │   ├── models.py                    # ORM 10개 테이블
│   │   ├── restaurant_repo.py
│   │   ├── weather_repo.py
│   │   ├── nutrition_repo.py
│   │   └── team_repo.py
│   └── api/
│       ├── __init__.py
│       ├── restaurant_repo.py           # Kakao 스텁
│       ├── weather_repo.py              # OpenWeather 스텁
│       ├── nutrition_repo.py            # 식품안전처 스텁
│       └── team_repo.py                 # 내부 API 스텁
└── seed/
    └── seed_data.py                     # 가상 데이터 삽입 스크립트

tests/
├── test_repositories.py                 # repo CRUD 테스트
└── test_seed.py                         # seed 결과 검증
```

### 수정
```
env.env                                  # DATA_SOURCE, DATABASE_URL 추가
requirements.txt                         # sqlalchemy>=2.0 추가
chatbot/context_builder.py               # 더미 → repo 팩토리
chatbot/tools.py                         # 더미 → repo 팩토리
```

---

## Task 1: 의존성 및 DB 엔진 설정

**Files:**
- Modify: `requirements.txt`
- Modify: `env.env`
- Create: `data/__init__.py`
- Create: `data/database.py`

- [ ] **Step 1: requirements.txt에 sqlalchemy 추가**

`requirements.txt` 파일에 아래 줄 추가:
```
sqlalchemy>=2.0.0
```

- [ ] **Step 2: env.env에 DB 환경변수 추가**

`env.env` 파일에 아래 줄 추가:
```
DATA_SOURCE=sqlite
DATABASE_URL=sqlite:///data/lunch_chatbot.db
```

- [ ] **Step 3: data/__init__.py 생성 (빈 파일)**

```python
```

- [ ] **Step 4: data/database.py 작성**

```python
"""
SQLAlchemy 엔진 및 세션 관리.
DATABASE_URL 환경변수로 연결 대상을 결정한다.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///data/lunch_chatbot.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
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
```

- [ ] **Step 5: 커밋**

```bash
git add requirements.txt env.env data/__init__.py data/database.py
git commit -m "chore: SQLAlchemy 의존성 및 DB 엔진 설정"
```

---

## Task 2: ORM 모델 정의

**Files:**
- Create: `data/repositories/__init__.py`
- Create: `data/repositories/sqlite/__init__.py`
- Create: `data/repositories/sqlite/models.py`

- [ ] **Step 1: __init__.py 파일 2개 생성 (빈 파일)**

`data/repositories/__init__.py` — 빈 파일  
`data/repositories/sqlite/__init__.py` — 빈 파일

- [ ] **Step 2: data/repositories/sqlite/models.py 작성**

```python
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
```

- [ ] **Step 3: 테이블 생성 확인**

```bash
cd C:/aibigdata/13.WebSurvice/mini_project_13
python -c "from data.database import init_db; init_db(); print('테이블 생성 완료')"
```
Expected: `테이블 생성 완료`

- [ ] **Step 4: 커밋**

```bash
git add data/repositories/__init__.py data/repositories/sqlite/__init__.py data/repositories/sqlite/models.py
git commit -m "feat: SQLAlchemy ORM 모델 10개 테이블 정의"
```

---

## Task 3: 추상 인터페이스 정의

**Files:**
- Create: `data/repositories/base.py`

- [ ] **Step 1: 실패 테스트 작성 (tests/test_repositories.py)**

```python
# tests/test_repositories.py
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
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
pytest tests/test_repositories.py::test_base_repos_are_abstract -v
```
Expected: FAIL (ImportError — base.py 없음)

- [ ] **Step 3: data/repositories/base.py 작성**

```python
"""
Repository 추상 인터페이스.
SQLite 구현체와 API 구현체가 동일한 메서드를 구현해야 한다.
"""
from abc import ABC, abstractmethod
from datetime import date


class BaseRestaurantRepo(ABC):
    @abstractmethod
    def get_nearby(self, lat: float, lng: float, radius: int,
                   category: str | None = None) -> list[dict]:
        """반경 내 식당 목록 반환. 각 dict는 Restaurant 컬럼 키를 가짐."""
        ...

    @abstractmethod
    def get_by_id(self, place_id: str) -> dict | None:
        """place_id로 단일 식당 반환. 없으면 None."""
        ...

    @abstractmethod
    def search(self, keyword: str) -> list[dict]:
        """이름/주소 키워드 검색."""
        ...


class BaseWeatherRepo(ABC):
    @abstractmethod
    def get_current(self, lat: float, lng: float) -> dict:
        """현재 날씨 반환. API 구현체가 실제 호출, SQLite는 최신 캐시 반환."""
        ...

    @abstractmethod
    def get_latest_cached(self) -> dict | None:
        """DB에서 가장 최근 날씨 레코드 반환. 없으면 None."""
        ...


class BaseNutritionRepo(ABC):
    @abstractmethod
    def get_by_category(self, food_category: str) -> dict | None:
        """카테고리별 평균 영양 정보 반환."""
        ...

    @abstractmethod
    def get_meal_history(self, user_id: str, days: int = 7) -> list[dict]:
        """최근 N일간 식사 기록 반환."""
        ...

    @abstractmethod
    def record_meal(self, user_id: str, restaurant_id: str,
                    meal_name: str, satisfaction: int) -> dict:
        """식사 기록 저장. 저장된 레코드 dict 반환."""
        ...


class BaseTeamRepo(ABC):
    @abstractmethod
    def get_team(self, team_id: str) -> dict | None:
        """팀 정보 반환."""
        ...

    @abstractmethod
    def get_vote_results(self, team_id: str, target_date: date) -> list[dict]:
        """특정 날짜 투표 결과 반환. 각 dict: {restaurant_id, name, vote_count}."""
        ...

    @abstractmethod
    def cast_vote(self, user_id: str, team_id: str, restaurant_id: str) -> dict:
        """투표 등록. 오늘 열린 세션에 투표. 반환: {result, restaurant_id}."""
        ...

    @abstractmethod
    def get_visit_history(self, team_id: str, days: int = 30) -> list[dict]:
        """최근 N일간 팀 방문 식당 목록 반환."""
        ...
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
pytest tests/test_repositories.py::test_base_repos_are_abstract -v
```
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add data/repositories/base.py tests/test_repositories.py
git commit -m "feat: Repository 추상 인터페이스 4개 정의"
```

---

## Task 4: SQLite 구현체 4개

**Files:**
- Create: `data/repositories/sqlite/restaurant_repo.py`
- Create: `data/repositories/sqlite/weather_repo.py`
- Create: `data/repositories/sqlite/nutrition_repo.py`
- Create: `data/repositories/sqlite/team_repo.py`

- [ ] **Step 1: 실패 테스트 추가 (tests/test_repositories.py)**

파일 끝에 추가:

```python
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

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
from datetime import datetime, date, timedelta


@pytest.fixture(autouse=True)
def setup_db():
    init_db()
    yield
    # 테스트 후 정리
    from data.database import Base, engine
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


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
        recorded_at=datetime.utcnow(), condition="sunny",
        temperature=24.0, humidity=55, lat=37.4979, lng=127.0276
    ))
    db.commit()
    repo = SQLiteWeatherRepo()
    result = repo.get_latest_cached()
    assert result is not None
    assert result["condition"] == "sunny"


def test_nutrition_record_and_retrieve(db):
    """식사 기록 저장 후 조회."""
    db.add(Restaurant(place_id="p003", name="한솥도시락", category="한식",
                      lat=37.498, lng=127.028))
    db.commit()
    repo = SQLiteNutritionRepo()
    repo.record_meal(
        user_id="user_01", restaurant_id="p003",
        meal_name="제육볶음", satisfaction=4
    )
    history = repo.get_meal_history(user_id="user_01", days=7)
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
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
pytest tests/test_repositories.py -v -k "not test_base"
```
Expected: FAIL (ImportError)

- [ ] **Step 3: data/repositories/sqlite/restaurant_repo.py 작성**

```python
from data.repositories.base import BaseRestaurantRepo
from data.database import SessionLocal
from data.repositories.sqlite.models import Restaurant


class SQLiteRestaurantRepo(BaseRestaurantRepo):
    def get_nearby(self, lat, lng, radius, category=None):
        with SessionLocal() as db:
            q = db.query(Restaurant)
            if category:
                q = q.filter(Restaurant.category == category)
            rows = q.all()
            # 간단한 위경도 거리 필터 (실제 Haversine 대신 근사치)
            result = []
            for r in rows:
                if r.lat is None or r.lng is None:
                    continue
                dlat = abs(r.lat - lat) * 111000
                dlng = abs(r.lng - lng) * 88000
                if (dlat ** 2 + dlng ** 2) ** 0.5 <= radius:
                    result.append(self._to_dict(r))
            return result

    def get_by_id(self, place_id):
        with SessionLocal() as db:
            r = db.get(Restaurant, place_id)
            return self._to_dict(r) if r else None

    def search(self, keyword):
        with SessionLocal() as db:
            rows = db.query(Restaurant).filter(
                Restaurant.name.contains(keyword)
            ).all()
            return [self._to_dict(r) for r in rows]

    @staticmethod
    def _to_dict(r: Restaurant) -> dict:
        return {
            "place_id": r.place_id, "name": r.name,
            "category": r.category, "address": r.address,
            "lat": r.lat, "lng": r.lng,
            "rating": r.rating, "review_count": r.review_count,
            "open_time": r.open_time, "close_time": r.close_time,
        }
```

- [ ] **Step 4: data/repositories/sqlite/weather_repo.py 작성**

```python
from data.repositories.base import BaseWeatherRepo
from data.database import SessionLocal
from data.repositories.sqlite.models import WeatherLog


class SQLiteWeatherRepo(BaseWeatherRepo):
    def get_current(self, lat, lng):
        """SQLite 모드에서는 최신 캐시를 반환."""
        return self.get_latest_cached() or {}

    def get_latest_cached(self):
        with SessionLocal() as db:
            row = db.query(WeatherLog).order_by(
                WeatherLog.recorded_at.desc()
            ).first()
            if not row:
                return None
            return {
                "id": row.id, "recorded_at": str(row.recorded_at),
                "condition": row.condition, "temperature": row.temperature,
                "humidity": row.humidity, "wind_speed": row.wind_speed,
                "description": row.description,
            }
```

- [ ] **Step 5: data/repositories/sqlite/nutrition_repo.py 작성**

```python
from datetime import datetime, timedelta
from data.repositories.base import BaseNutritionRepo
from data.database import SessionLocal
from data.repositories.sqlite.models import NutritionInfo, MealHistory


class SQLiteNutritionRepo(BaseNutritionRepo):
    def get_by_category(self, food_category):
        with SessionLocal() as db:
            row = db.query(NutritionInfo).filter(
                NutritionInfo.food_category == food_category
            ).first()
            if not row:
                return None
            return {
                "food_category": row.food_category,
                "avg_calories": row.avg_calories,
                "avg_protein": row.avg_protein,
                "avg_carbs": row.avg_carbs,
                "avg_fat": row.avg_fat,
                "health_score": row.health_score,
            }

    def get_meal_history(self, user_id, days=7):
        since = datetime.utcnow() - timedelta(days=days)
        with SessionLocal() as db:
            rows = db.query(MealHistory).filter(
                MealHistory.user_id == user_id,
                MealHistory.eaten_at >= since,
            ).order_by(MealHistory.eaten_at.desc()).all()
            return [self._to_dict(r) for r in rows]

    def record_meal(self, user_id, restaurant_id, meal_name, satisfaction):
        record = MealHistory(
            user_id=user_id, restaurant_id=restaurant_id,
            meal_name=meal_name, eaten_at=datetime.utcnow(),
            satisfaction=satisfaction,
        )
        with SessionLocal() as db:
            db.add(record)
            db.commit()
            db.refresh(record)
            return self._to_dict(record)

    @staticmethod
    def _to_dict(r: MealHistory) -> dict:
        return {
            "id": r.id, "user_id": r.user_id,
            "restaurant_id": r.restaurant_id, "meal_name": r.meal_name,
            "eaten_at": str(r.eaten_at), "satisfaction": r.satisfaction,
        }
```

- [ ] **Step 6: data/repositories/sqlite/team_repo.py 작성**

```python
import uuid
from datetime import date, datetime
from data.repositories.base import BaseTeamRepo
from data.database import SessionLocal
from data.repositories.sqlite.models import Team, VoteSession, Vote, VisitHistory


class SQLiteTeamRepo(BaseTeamRepo):
    def get_team(self, team_id):
        with SessionLocal() as db:
            t = db.get(Team, team_id)
            if not t:
                return None
            return {"team_id": t.team_id, "name": t.name,
                    "lat": t.lat, "lng": t.lng}

    def get_vote_results(self, team_id, target_date):
        with SessionLocal() as db:
            session = db.query(VoteSession).filter(
                VoteSession.team_id == team_id,
                VoteSession.date == target_date,
            ).first()
            if not session:
                return []
            from sqlalchemy import func
            from data.repositories.sqlite.models import Restaurant
            rows = (
                db.query(Vote.restaurant_id,
                         Restaurant.name,
                         func.count(Vote.id).label("vote_count"))
                .join(Restaurant, Vote.restaurant_id == Restaurant.place_id)
                .filter(Vote.session_id == session.session_id)
                .group_by(Vote.restaurant_id)
                .order_by(func.count(Vote.id).desc())
                .all()
            )
            return [{"restaurant_id": r.restaurant_id,
                     "name": r.name, "vote_count": r.vote_count}
                    for r in rows]

    def cast_vote(self, user_id, team_id, restaurant_id):
        today = date.today()
        with SessionLocal() as db:
            session = db.query(VoteSession).filter(
                VoteSession.team_id == team_id,
                VoteSession.date == today,
                VoteSession.status == "open",
            ).first()
            if not session:
                session = VoteSession(
                    session_id=str(uuid.uuid4()),
                    team_id=team_id, date=today, status="open",
                )
                db.add(session)
                db.flush()
            vote = Vote(
                session_id=session.session_id,
                user_id=user_id, restaurant_id=restaurant_id,
            )
            db.add(vote)
            db.commit()
            return {"result": "투표 완료", "restaurant_id": restaurant_id,
                    "session_id": session.session_id}

    def get_visit_history(self, team_id, days=30):
        since = date.today().__class__.fromordinal(
            date.today().toordinal() - days
        )
        with SessionLocal() as db:
            rows = db.query(VisitHistory).filter(
                VisitHistory.team_id == team_id,
                VisitHistory.visited_at >= since,
            ).order_by(VisitHistory.visited_at.desc()).all()
            return [{"restaurant_id": r.restaurant_id,
                     "visited_at": str(r.visited_at),
                     "headcount": r.headcount} for r in rows]
```

- [ ] **Step 7: 테스트 통과 확인**

```bash
pytest tests/test_repositories.py -v
```
Expected: 전체 PASS (6건)

- [ ] **Step 8: 커밋**

```bash
git add data/repositories/sqlite/ tests/test_repositories.py
git commit -m "feat: SQLite Repository 구현체 4개 (restaurant/weather/nutrition/team)"
```

---

## Task 5: API 스텁 및 팩토리

**Files:**
- Create: `data/repositories/api/__init__.py`
- Create: `data/repositories/api/restaurant_repo.py`
- Create: `data/repositories/api/weather_repo.py`
- Create: `data/repositories/api/nutrition_repo.py`
- Create: `data/repositories/api/team_repo.py`
- Create: `data/repositories/factory.py`

- [ ] **Step 1: data/repositories/api/__init__.py 생성 (빈 파일)**

- [ ] **Step 2: API 스텁 4개 작성**

`data/repositories/api/restaurant_repo.py`:
```python
from data.repositories.base import BaseRestaurantRepo

class KakaoRestaurantRepo(BaseRestaurantRepo):
    """TODO: Kakao 로컬 API 연동. DATA_SOURCE=api 설정 시 사용."""
    def get_nearby(self, lat, lng, radius, category=None):
        raise NotImplementedError("Kakao API 미구현 — DATA_SOURCE=sqlite 사용")
    def get_by_id(self, place_id):
        raise NotImplementedError
    def search(self, keyword):
        raise NotImplementedError
```

`data/repositories/api/weather_repo.py`:
```python
from data.repositories.base import BaseWeatherRepo

class OpenWeatherRepo(BaseWeatherRepo):
    """TODO: OpenWeatherMap API 연동. DATA_SOURCE=api 설정 시 사용."""
    def get_current(self, lat, lng):
        raise NotImplementedError("OpenWeather API 미구현 — DATA_SOURCE=sqlite 사용")
    def get_latest_cached(self):
        raise NotImplementedError
```

`data/repositories/api/nutrition_repo.py`:
```python
from data.repositories.base import BaseNutritionRepo

class FoodSafetyRepo(BaseNutritionRepo):
    """TODO: 식품안전처 Open API 연동. DATA_SOURCE=api 설정 시 사용."""
    def get_by_category(self, food_category):
        raise NotImplementedError("식품안전처 API 미구현 — DATA_SOURCE=sqlite 사용")
    def get_meal_history(self, user_id, days=7):
        raise NotImplementedError
    def record_meal(self, user_id, restaurant_id, meal_name, satisfaction):
        raise NotImplementedError
```

`data/repositories/api/team_repo.py`:
```python
from data.repositories.base import BaseTeamRepo

class InternalAPITeamRepo(BaseTeamRepo):
    """TODO: 내부 팀 관리 API 연동. DATA_SOURCE=api 설정 시 사용."""
    def get_team(self, team_id):
        raise NotImplementedError("내부 API 미구현 — DATA_SOURCE=sqlite 사용")
    def get_vote_results(self, team_id, target_date):
        raise NotImplementedError
    def cast_vote(self, user_id, team_id, restaurant_id):
        raise NotImplementedError
    def get_visit_history(self, team_id, days=30):
        raise NotImplementedError
```

- [ ] **Step 3: data/repositories/factory.py 작성**

```python
"""
DATA_SOURCE 환경변수로 SQLite / API 구현체를 선택한다.
기본값: sqlite
"""
import os
from data.repositories.base import (
    BaseRestaurantRepo, BaseWeatherRepo,
    BaseNutritionRepo, BaseTeamRepo
)


def get_restaurant_repo() -> BaseRestaurantRepo:
    if os.getenv("DATA_SOURCE", "sqlite") == "api":
        from data.repositories.api.restaurant_repo import KakaoRestaurantRepo
        return KakaoRestaurantRepo()
    from data.repositories.sqlite.restaurant_repo import SQLiteRestaurantRepo
    return SQLiteRestaurantRepo()


def get_weather_repo() -> BaseWeatherRepo:
    if os.getenv("DATA_SOURCE", "sqlite") == "api":
        from data.repositories.api.weather_repo import OpenWeatherRepo
        return OpenWeatherRepo()
    from data.repositories.sqlite.weather_repo import SQLiteWeatherRepo
    return SQLiteWeatherRepo()


def get_nutrition_repo() -> BaseNutritionRepo:
    if os.getenv("DATA_SOURCE", "sqlite") == "api":
        from data.repositories.api.nutrition_repo import FoodSafetyRepo
        return FoodSafetyRepo()
    from data.repositories.sqlite.nutrition_repo import SQLiteNutritionRepo
    return SQLiteNutritionRepo()


def get_team_repo() -> BaseTeamRepo:
    if os.getenv("DATA_SOURCE", "sqlite") == "api":
        from data.repositories.api.team_repo import InternalAPITeamRepo
        return InternalAPITeamRepo()
    from data.repositories.sqlite.team_repo import SQLiteTeamRepo
    return SQLiteTeamRepo()
```

- [ ] **Step 4: 팩토리 동작 확인**

```bash
python -c "
from data.repositories.factory import get_restaurant_repo
repo = get_restaurant_repo()
print(type(repo).__name__)
"
```
Expected: `SQLiteRestaurantRepo`

- [ ] **Step 5: 커밋**

```bash
git add data/repositories/api/ data/repositories/factory.py
git commit -m "feat: API 스텁 4개 및 DATA_SOURCE 팩토리 추가"
```

---

## Task 6: Seed 데이터 스크립트

**Files:**
- Create: `data/seed/__init__.py`
- Create: `data/seed/seed_data.py`
- Create: `tests/test_seed.py`

- [ ] **Step 1: 실패 테스트 작성 (tests/test_seed.py)**

```python
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
    Base.metadata.create_all(bind=engine)


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
    assert count >= 15  # 세션 3개, 세션당 5표 이상
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
pytest tests/test_seed.py -v
```
Expected: FAIL (ImportError)

- [ ] **Step 3: data/seed/__init__.py 생성 (빈 파일)**

- [ ] **Step 4: data/seed/seed_data.py 작성**

```python
"""
가상 Seed 데이터 생성.
`python data/seed/seed_data.py` 또는 run_seed() 함수로 실행.
중복 실행 시 기존 데이터를 삭제하고 재삽입한다.
"""
import uuid
from datetime import datetime, date, timedelta
from data.database import SessionLocal, init_db
from data.repositories.sqlite.models import (
    Restaurant, WeatherLog, NutritionInfo, MealHistory,
    Team, User, VoteSession, Vote, VisitHistory, Veto
)


RESTAURANTS = [
    # 한식 6
    {"place_id": "place_001", "name": "명동칼국수", "category": "한식",
     "address": "서울 강남구 역삼동 101", "lat": 37.4981, "lng": 127.0278,
     "rating": 4.5, "review_count": 320, "open_time": "11:00", "close_time": "21:00"},
    {"place_id": "place_002", "name": "한솥도시락 역삼점", "category": "한식",
     "address": "서울 강남구 역삼동 202", "lat": 37.4975, "lng": 127.0265,
     "rating": 3.9, "review_count": 180, "open_time": "10:30", "close_time": "21:30"},
    {"place_id": "place_003", "name": "청국장골", "category": "한식",
     "address": "서울 강남구 역삼동 303", "lat": 37.4970, "lng": 127.0280,
     "rating": 4.3, "review_count": 210, "open_time": "11:00", "close_time": "20:30"},
    {"place_id": "place_004", "name": "제주돼지국밥", "category": "한식",
     "address": "서울 강남구 역삼동 404", "lat": 37.4965, "lng": 127.0272,
     "rating": 4.1, "review_count": 155, "open_time": "08:00", "close_time": "21:00"},
    {"place_id": "place_005", "name": "강남순대국", "category": "한식",
     "address": "서울 강남구 역삼동 505", "lat": 37.4988, "lng": 127.0260,
     "rating": 4.0, "review_count": 98, "open_time": "07:00", "close_time": "20:00"},
    {"place_id": "place_006", "name": "참이맛 한정식", "category": "한식",
     "address": "서울 강남구 역삼동 606", "lat": 37.4972, "lng": 127.0290,
     "rating": 4.6, "review_count": 275, "open_time": "11:30", "close_time": "22:00"},
    # 일식 4
    {"place_id": "place_007", "name": "사쿠라스시", "category": "일식",
     "address": "서울 강남구 역삼동 707", "lat": 37.4983, "lng": 127.0255,
     "rating": 4.4, "review_count": 390, "open_time": "11:30", "close_time": "22:00"},
    {"place_id": "place_008", "name": "라멘하우스", "category": "일식",
     "address": "서울 강남구 역삼동 808", "lat": 37.4962, "lng": 127.0268,
     "rating": 4.2, "review_count": 240, "open_time": "11:00", "close_time": "21:00"},
    {"place_id": "place_009", "name": "돈카츠마루", "category": "일식",
     "address": "서울 강남구 역삼동 909", "lat": 37.4990, "lng": 127.0285,
     "rating": 4.3, "review_count": 310, "open_time": "11:00", "close_time": "21:30"},
    {"place_id": "place_010", "name": "우동야", "category": "일식",
     "address": "서울 강남구 역삼동 1010", "lat": 37.4968, "lng": 127.0295,
     "rating": 3.8, "review_count": 120, "open_time": "11:30", "close_time": "20:30"},
    # 중식 3
    {"place_id": "place_011", "name": "차이나가든", "category": "중식",
     "address": "서울 강남구 역삼동 1111", "lat": 37.4977, "lng": 127.0300,
     "rating": 4.0, "review_count": 195, "open_time": "11:00", "close_time": "22:00"},
    {"place_id": "place_012", "name": "마라탕클럽", "category": "중식",
     "address": "서울 강남구 역삼동 1212", "lat": 37.4958, "lng": 127.0250,
     "rating": 4.5, "review_count": 430, "open_time": "11:00", "close_time": "23:00"},
    {"place_id": "place_013", "name": "짬뽕왕국", "category": "중식",
     "address": "서울 강남구 역삼동 1313", "lat": 37.4985, "lng": 127.0240,
     "rating": 3.7, "review_count": 88, "open_time": "10:30", "close_time": "21:00"},
    # 양식 3
    {"place_id": "place_014", "name": "파스타리아", "category": "양식",
     "address": "서울 강남구 역삼동 1414", "lat": 37.4960, "lng": 127.0310,
     "rating": 4.3, "review_count": 260, "open_time": "11:30", "close_time": "22:00"},
    {"place_id": "place_015", "name": "버거킹 강남역점", "category": "양식",
     "address": "서울 강남구 역삼동 1515", "lat": 37.4995, "lng": 127.0275,
     "rating": 3.5, "review_count": 520, "open_time": "08:00", "close_time": "23:00"},
    {"place_id": "place_016", "name": "더스테이크", "category": "양식",
     "address": "서울 강남구 역삼동 1616", "lat": 37.4973, "lng": 127.0245,
     "rating": 4.7, "review_count": 175, "open_time": "12:00", "close_time": "22:00"},
    # 분식 2
    {"place_id": "place_017", "name": "김밥나라 역삼점", "category": "분식",
     "address": "서울 강남구 역삼동 1717", "lat": 37.4980, "lng": 127.0315,
     "rating": 3.6, "review_count": 340, "open_time": "07:00", "close_time": "22:00"},
    {"place_id": "place_018", "name": "떡볶이왕", "category": "분식",
     "address": "서울 강남구 역삼동 1818", "lat": 37.4967, "lng": 127.0235,
     "rating": 4.1, "review_count": 280, "open_time": "11:00", "close_time": "21:00"},
    # 카페/샐러드 2
    {"place_id": "place_019", "name": "그린볼", "category": "카페",
     "address": "서울 강남구 역삼동 1919", "lat": 37.4992, "lng": 127.0320,
     "rating": 4.4, "review_count": 190, "open_time": "08:00", "close_time": "20:00"},
    {"place_id": "place_020", "name": "써브웨이 역삼점", "category": "카페",
     "address": "서울 강남구 역삼동 2020", "lat": 37.4955, "lng": 127.0325,
     "rating": 3.9, "review_count": 415, "open_time": "07:30", "close_time": "22:30"},
]

WEATHER_CONDITIONS = [
    ("sunny", 26.0, 45, 2.1, "맑고 따뜻한 날씨"),
    ("sunny", 28.0, 40, 1.8, "화창한 날씨"),
    ("cloudy", 22.0, 60, 3.0, "구름 많음"),
    ("cloudy", 20.0, 65, 2.5, "흐린 날씨"),
    ("rainy", 17.0, 85, 4.5, "비 내림"),
    ("sunny", 24.0, 50, 2.0, "맑음"),
    ("hot", 33.0, 55, 1.5, "매우 더운 날씨"),
]

NUTRITION_DATA = [
    ("한식", 580, 28, 72, 18, 1200, 6.5),
    ("일식", 520, 32, 58, 16, 980,  7.2),
    ("중식", 680, 24, 85, 22, 1450, 5.8),
    ("양식", 750, 35, 68, 32, 1100, 5.5),
    ("분식", 620, 18, 95, 14, 1350, 5.0),
    ("카페", 420, 15, 55, 12, 650,  7.8),
    ("패스트푸드", 820, 30, 95, 38, 1600, 4.2),
    ("베트남식", 490, 22, 65, 14, 900, 7.5),
    ("인도식", 640, 20, 80, 24, 1050, 6.8),
    ("멕시코식", 710, 28, 78, 28, 1300, 5.9),
    ("채식", 380, 14, 60, 10, 550, 8.5),
    ("해산물", 440, 42, 35, 12, 750, 8.0),
]


def run_seed():
    """DB를 초기화하고 가상 데이터를 삽입한다."""
    with SessionLocal() as db:
        # 기존 데이터 삭제 (외래키 순서 주의)
        db.query(Veto).delete()
        db.query(VisitHistory).delete()
        db.query(Vote).delete()
        db.query(VoteSession).delete()
        db.query(MealHistory).delete()
        db.query(NutritionInfo).delete()
        db.query(WeatherLog).delete()
        db.query(User).delete()
        db.query(Team).delete()
        db.query(Restaurant).delete()
        db.commit()

        # 식당 20개
        for r in RESTAURANTS:
            db.add(Restaurant(**r))

        # 날씨 7일
        now = datetime.utcnow()
        for i, (cond, temp, hum, wind, desc) in enumerate(WEATHER_CONDITIONS):
            db.add(WeatherLog(
                recorded_at=now - timedelta(days=6 - i),
                condition=cond, temperature=temp,
                humidity=hum, wind_speed=wind, description=desc,
                lat=37.4979, lng=127.0276,
            ))

        # 영양 정보 12개
        for cat, cal, prot, carb, fat, sod, score in NUTRITION_DATA:
            db.add(NutritionInfo(
                food_category=cat, avg_calories=cal, avg_protein=prot,
                avg_carbs=carb, avg_fat=fat, avg_sodium=sod, health_score=score,
            ))

        # 팀 & 유저
        db.add(Team(team_id="team_alpha", name="알파팀",
                    lat=37.4979, lng=127.0276))
        user_names = ["김민준", "이서연", "박지호", "최예은", "정우진"]
        for i, name in enumerate(user_names, 1):
            db.add(User(user_id=f"user_0{i}", name=name, team_id="team_alpha"))
        db.flush()

        # 식사 기록 25개 (5명 × 5일)
        meal_pairs = [
            ("place_001", "칼국수"),  ("place_007", "스시세트"),
            ("place_012", "마라탕"),  ("place_014", "봉골레파스타"),
            ("place_003", "청국장"),
        ]
        for day in range(5):
            eaten = now - timedelta(days=4 - day)
            for u_idx in range(1, 6):
                rid, mname = meal_pairs[(u_idx - 1 + day) % 5]
                db.add(MealHistory(
                    user_id=f"user_0{u_idx}", restaurant_id=rid,
                    meal_name=mname, eaten_at=eaten,
                    calories=550.0 + u_idx * 10,
                    satisfaction=3 + (u_idx + day) % 3,
                ))

        # 투표 세션 3개 (지난 3일)
        vote_restaurants = [
            ["place_001", "place_007", "place_012"],
            ["place_002", "place_008", "place_014"],
            ["place_003", "place_009", "place_015"],
        ]
        for d_offset, picks in enumerate(vote_restaurants):
            session_date = date.today() - timedelta(days=2 - d_offset)
            sid = str(uuid.uuid4())
            status = "closed" if d_offset < 2 else "open"
            db.add(VoteSession(
                session_id=sid, team_id="team_alpha",
                date=session_date, status=status,
            ))
            db.flush()
            for u_idx in range(1, 6):
                picked = picks[(u_idx - 1) % len(picks)]
                db.add(Vote(
                    session_id=sid,
                    user_id=f"user_0{u_idx}",
                    restaurant_id=picked,
                ))

        # 방문 기록 10개
        visit_data = [
            ("place_001", 5), ("place_007", 4), ("place_012", 5),
            ("place_002", 3), ("place_014", 4), ("place_008", 5),
            ("place_003", 4), ("place_009", 3), ("place_015", 5),
            ("place_001", 4),
        ]
        for i, (rid, cnt) in enumerate(visit_data):
            db.add(VisitHistory(
                team_id="team_alpha", restaurant_id=rid,
                visited_at=date.today() - timedelta(days=i),
                headcount=cnt,
            ))

        # 거부 데이터 3개
        for u, r in [("user_01", "place_013"), ("user_02", "place_015"),
                     ("user_03", "place_018")]:
            db.add(Veto(user_id=u, restaurant_id=r, reason="개인 취향"))

        db.commit()
        print("Seed 완료: 식당 20, 날씨 7, 영양 12, 식사기록 25, 투표 25, 방문 10, 거부 3")


if __name__ == "__main__":
    init_db()
    run_seed()
```

- [ ] **Step 5: 테스트 통과 확인**

```bash
pytest tests/test_seed.py -v
```
Expected: 5건 전체 PASS

- [ ] **Step 6: 실제 DB 파일에도 seed 실행**

```bash
python data/seed/seed_data.py
```
Expected: `Seed 완료: 식당 20, 날씨 7, 영양 12, 식사기록 25, 투표 25, 방문 10, 거부 3`

- [ ] **Step 7: 커밋**

```bash
git add data/seed/ tests/test_seed.py
git commit -m "feat: Seed 데이터 스크립트 및 검증 테스트 추가"
```

---

## Task 7: Chatbot 연동 — context_builder.py

**Files:**
- Modify: `chatbot/context_builder.py`

- [ ] **Step 1: context_builder.py 상단 import 교체**

`chatbot/context_builder.py`에서 더미 함수들을 제거하고 repo 팩토리를 사용하도록 수정한다.

기존 `ContextBuilder.__init__` 내부를 아래로 교체:
```python
from data.repositories.factory import get_restaurant_repo, get_weather_repo, get_nutrition_repo

class ContextBuilder:
    def __init__(self):
        self._restaurant_repo = get_restaurant_repo()
        self._weather_repo = get_weather_repo()
        self._nutrition_repo = get_nutrition_repo()
```

- [ ] **Step 2: build_context 내 더미 호출 → repo 호출로 교체**

`_dummy_get_recommendations` 호출 부분을 아래로 교체:
```python
def _get_recommendations(self, category=None):
    return self._restaurant_repo.get_nearby(
        lat=37.4979, lng=127.0276, radius=1000, category=category
    )

def _get_weather(self):
    return self._weather_repo.get_latest_cached() or {}

def _get_meal_history(self, user_id):
    return self._nutrition_repo.get_meal_history(user_id=user_id, days=7)
```

- [ ] **Step 3: 기존 통합 테스트 여전히 통과 확인**

```bash
pytest tests/test_chatbot_core.py -v
```
Expected: 13건 전체 PASS (LunchChatbot 테스트는 get_llm_client mock 사용 — repo는 context_builder 내부에서 처리됨)

- [ ] **Step 4: 커밋**

```bash
git add chatbot/context_builder.py
git commit -m "feat: context_builder 더미 데이터 → SQLite Repository 연동"
```

---

## Task 8: Chatbot 연동 — tools.py

**Files:**
- Modify: `chatbot/tools.py`

- [ ] **Step 1: tools.py ToolExecutor에 repo 주입**

`ToolExecutor.__init__` 내 더미 초기화를 아래로 교체:
```python
from data.repositories.factory import get_team_repo, get_nutrition_repo

class ToolExecutor:
    def __init__(self, user_id: str, team_id: str):
        self._user_id = user_id
        self._team_id = team_id
        self._team_repo = get_team_repo()
        self._nutrition_repo = get_nutrition_repo()
```

- [ ] **Step 2: _vote_restaurant 더미 → 실제 DB 저장으로 교체**

기존 더미 투표 함수를 아래로 교체:
```python
def _vote_restaurant(self, restaurant_name: str) -> dict:
    from data.repositories.sqlite.restaurant_repo import SQLiteRestaurantRepo
    candidates = SQLiteRestaurantRepo().search(restaurant_name)
    if not candidates:
        return {"result": f"'{restaurant_name}' 식당을 찾을 수 없습니다."}
    rid = candidates[0]["place_id"]
    name = candidates[0]["name"]
    result = self._team_repo.cast_vote(
        user_id=self._user_id,
        team_id=self._team_id,
        restaurant_id=rid,
    )
    return {"result": f"✅ {name}에 투표 완료!", "restaurant": name}
```

- [ ] **Step 3: _record_meal 더미 → 실제 DB 저장으로 교체**

기존 더미 식사 기록 함수를 아래로 교체:
```python
def _record_meal(self, restaurant_name: str, satisfaction: int) -> dict:
    from data.repositories.sqlite.restaurant_repo import SQLiteRestaurantRepo
    candidates = SQLiteRestaurantRepo().search(restaurant_name)
    rid = candidates[0]["place_id"] if candidates else None
    self._nutrition_repo.record_meal(
        user_id=self._user_id,
        restaurant_id=rid,
        meal_name=restaurant_name,
        satisfaction=satisfaction,
    )
    return {"result": f"✅ {restaurant_name} 식사 기록 완료! (만족도: {satisfaction}점)"}
```

- [ ] **Step 4: 전체 테스트 통과 확인**

```bash
pytest tests/ -v
```
Expected: 전체 PASS (test_chatbot_core 13건 + test_repositories 6건 + test_seed 5건)

- [ ] **Step 5: 커밋**

```bash
git add chatbot/tools.py
git commit -m "feat: tools.py 더미 투표/식사기록 → SQLite Repository 연동"
```

---

## Task 9: develop 브랜치로 merge 및 PR

- [ ] **Step 1: feature 브랜치 최신 상태 확인**

```bash
git log --oneline
```

- [ ] **Step 2: develop으로 merge**

```bash
git checkout develop
git merge feature/sqlite-seed-db --no-ff -m "feat: SQLite Seed DB + Repository Pattern 완성"
git push origin develop
```

- [ ] **Step 3: 전체 테스트 최종 확인**

```bash
pytest tests/ -v
```
Expected: 전체 PASS

- [ ] **Step 4: GitHub PR 생성**

```bash
gh pr create \
  --base develop \
  --head feature/sqlite-seed-db \
  --title "feat: SQLite Seed DB + Repository Pattern" \
  --body "## Summary
- SQLAlchemy 2.0 ORM 10개 테이블 정의
- Repository Pattern (4개 추상 인터페이스 + SQLite 구현체 + API 스텁)
- 가상 Seed 데이터 삽입 스크립트 (식당 20, 날씨 7일, 식사기록 25, 투표 25)
- context_builder.py + tools.py 더미 → 실제 DB 연동

## Test plan
- [ ] pytest tests/test_repositories.py — CRUD 6건
- [ ] pytest tests/test_seed.py — Seed 결과 검증 5건
- [ ] pytest tests/test_chatbot_core.py — 기존 13건 회귀 없음"
```
