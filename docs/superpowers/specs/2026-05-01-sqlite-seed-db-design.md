# SQLite Seed DB 설계 — 점심 추천 챗봇

**날짜:** 2026-05-01  
**브랜치:** feature/sqlite-seed-db  
**상태:** 승인됨

---

## 1. 목표

챗봇이 실제 동작하는 데 필요한 4가지 데이터(식당, 날씨, 영양/식사, 팀/투표)를
SQLite 로컬 DB에 가상 데이터로 채워 넣는다.

Repository Pattern으로 설계하여, 나중에 `DATA_SOURCE=api`로 환경변수 하나만 바꾸면
실제 외부 API(Kakao, OpenWeather, 식품안전처)로 전환된다. chatbot 코드는 변경 없음.

---

## 2. 디렉터리 구조

```
data/
├── repositories/
│   ├── __init__.py
│   ├── base.py                  # 추상 인터페이스 (4개 ABC)
│   ├── sqlite/
│   │   ├── __init__.py
│   │   ├── models.py            # SQLAlchemy 2.0 ORM (10개 테이블)
│   │   ├── restaurant_repo.py   # SQLiteRestaurantRepo
│   │   ├── weather_repo.py      # SQLiteWeatherRepo
│   │   ├── nutrition_repo.py    # SQLiteNutritionRepo
│   │   └── team_repo.py         # SQLiteTeamRepo
│   ├── api/
│   │   ├── __init__.py
│   │   ├── restaurant_repo.py   # KakaoRestaurantRepo (스텁)
│   │   ├── weather_repo.py      # OpenWeatherRepo (스텁)
│   │   ├── nutrition_repo.py    # FoodSafetyRepo (스텁)
│   │   └── team_repo.py         # InternalAPIRepo (스텁)
│   └── factory.py               # DATA_SOURCE 기반 팩토리
├── seed/
│   └── seed_data.py             # 가상 데이터 생성 스크립트
└── database.py                  # SQLAlchemy 엔진/세션 관리
```

---

## 3. DB 스키마 (10개 테이블)

GUIDE 파일 4개의 스키마를 그대로 사용한다.

### 소주제 1 — 식당 (Restaurant)

```sql
CREATE TABLE restaurants (
    place_id        TEXT PRIMARY KEY,   -- Kakao place_id (가상: "place_001" 등)
    name            TEXT NOT NULL,
    category        TEXT,               -- 한식 | 일식 | 중식 | 양식 | 분식 | 카페
    address         TEXT,
    lat             REAL,
    lng             REAL,
    phone           TEXT,
    rating          REAL,               -- 0.0~5.0
    review_count    INTEGER DEFAULT 0,
    open_time       TEXT,
    close_time      TEXT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 소주제 2 — 날씨 (WeatherLog)

```sql
CREATE TABLE weather_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    recorded_at     DATETIME NOT NULL,
    condition       TEXT,   -- sunny | cloudy | rainy | hot | cold | snowy
    temperature     REAL,
    humidity        INTEGER,
    wind_speed      REAL,
    description     TEXT,
    lat             REAL,
    lng             REAL
);
CREATE INDEX idx_weather_recorded ON weather_logs(recorded_at DESC);
```

### 소주제 3 — 영양 & 식사 기록

```sql
CREATE TABLE nutrition_info (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    food_category   TEXT NOT NULL,      -- 한식, 일식 등
    avg_calories    REAL,
    avg_protein     REAL,
    avg_carbs       REAL,
    avg_fat         REAL,
    avg_sodium      REAL,
    health_score    REAL,               -- 0~10
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE meal_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         TEXT NOT NULL,
    restaurant_id   TEXT REFERENCES restaurants(place_id),
    meal_name       TEXT,
    eaten_at        DATETIME NOT NULL,
    calories        REAL,
    satisfaction    INTEGER,            -- 1~5
    notes           TEXT
);
```

### 소주제 4 — 팀 & 투표

```sql
CREATE TABLE teams (
    team_id     TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    lat         REAL,
    lng         REAL,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE users (
    user_id     TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    team_id     TEXT REFERENCES teams(team_id),
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE vote_sessions (
    session_id  TEXT PRIMARY KEY,
    team_id     TEXT REFERENCES teams(team_id),
    date        DATE NOT NULL,
    status      TEXT DEFAULT 'open',   -- open | closed
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE votes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT REFERENCES vote_sessions(session_id),
    user_id         TEXT REFERENCES users(user_id),
    restaurant_id   TEXT REFERENCES restaurants(place_id),
    voted_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(session_id, user_id)
);

CREATE TABLE visit_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id         TEXT REFERENCES teams(team_id),
    restaurant_id   TEXT REFERENCES restaurants(place_id),
    visited_at      DATE NOT NULL,
    headcount       INTEGER
);

CREATE TABLE vetoes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         TEXT REFERENCES users(user_id),
    restaurant_id   TEXT REFERENCES restaurants(place_id),
    reason          TEXT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## 4. Repository 레이어

### 추상 인터페이스 (`base.py`)

```python
class BaseRestaurantRepo(ABC):
    def get_nearby(self, lat, lng, radius, category=None) -> list: ...
    def get_by_id(self, place_id: str) -> dict | None: ...
    def search(self, keyword: str) -> list: ...

class BaseWeatherRepo(ABC):
    def get_current(self, lat, lng) -> dict: ...
    def get_latest_cached(self) -> dict | None: ...

class BaseNutritionRepo(ABC):
    def get_by_category(self, food_category: str) -> dict | None: ...
    def get_meal_history(self, user_id: str, days=7) -> list: ...
    def record_meal(self, user_id, restaurant_id, meal_name, satisfaction): ...

class BaseTeamRepo(ABC):
    def get_team(self, team_id: str) -> dict | None: ...
    def get_vote_results(self, team_id, date) -> list: ...
    def cast_vote(self, user_id, session_id, restaurant_id): ...
    def get_visit_history(self, team_id, days=30) -> list: ...
```

### 팩토리 (`factory.py`)

```python
def get_restaurant_repo() -> BaseRestaurantRepo:
    if os.getenv("DATA_SOURCE", "sqlite") == "api":
        return KakaoRestaurantRepo()      # 나중에 구현
    return SQLiteRestaurantRepo()

def get_weather_repo() -> BaseWeatherRepo: ...
def get_nutrition_repo() -> BaseNutritionRepo: ...
def get_team_repo() -> BaseTeamRepo: ...
```

### API 스텁 패턴

```python
# api/restaurant_repo.py
class KakaoRestaurantRepo(BaseRestaurantRepo):
    """
    TODO: Kakao 로컬 API 연동
    https://developers.kakao.com/docs/latest/ko/local/dev-guide
    """
    def get_nearby(self, lat, lng, radius, category=None):
        raise NotImplementedError("Kakao API 미구현 — DATA_SOURCE=sqlite 사용")
```

---

## 5. Seed 데이터

`python data/seed/seed_data.py` 한 번 실행으로 모두 삽입.

| 테이블 | 건수 | 비고 |
|---|---|---|
| teams | 1 | team_alpha, 강남구 기준 위경도 |
| users | 5 | user_01 ~ user_05 |
| restaurants | 20 | 한식 6, 일식 4, 중식 3, 양식 3, 분식 2, 카페/샐러드 2 |
| weather_logs | 7 | 최근 7일, 맑음 3·흐림 2·비 1·더움 1 |
| nutrition_info | 12 | 카테고리별 평균 영양소 |
| meal_history | 25 | 5명 × 5일 (만족도 포함) |
| vote_sessions | 3 | 지난 3일 |
| votes | 25 | 세션당 5~10표 |
| visit_history | 10 | 팀 방문 기록 |
| vetoes | 3 | 테스트용 거부 데이터 |

---

## 6. Chatbot 연동

### context_builder.py

```python
# 더미 함수 → repo 팩토리로 교체
from data.repositories.factory import get_restaurant_repo, get_weather_repo

class ContextBuilder:
    def __init__(self):
        self._restaurant_repo = get_restaurant_repo()
        self._weather_repo = get_weather_repo()

    def build_context(self, intent, user_id, team_id) -> str:
        weather = self._weather_repo.get_latest_cached()
        restaurants = self._restaurant_repo.get_nearby(lat=37.4979, lng=127.0276, radius=1000)
        ...
```

### tools.py

```python
from data.repositories.factory import get_team_repo, get_nutrition_repo

class ToolExecutor:
    def __init__(self, user_id, team_id):
        self._team_repo = get_team_repo()
        self._nutrition_repo = get_nutrition_repo()

    def _vote_restaurant(self, restaurant_name) -> dict:
        self._team_repo.cast_vote(self._user_id, session_id, restaurant_name)
        return {"result": f"✅ {restaurant_name} 투표 완료!"}

    def _record_meal(self, restaurant_name, satisfaction) -> dict:
        self._nutrition_repo.record_meal(self._user_id, restaurant_name, satisfaction)
        return {"result": "✅ 식사 기록 완료!"}
```

---

## 7. 환경변수

```bash
# env.env 추가 항목
DATA_SOURCE=sqlite        # sqlite | api
DATABASE_URL=sqlite:///data/lunch_chatbot.db
```

---

## 8. 테스트 계획

- `tests/test_repositories.py` — SQLite repo CRUD 테스트 (각 repo당 3~4건)
- `tests/test_seed.py` — seed 실행 후 레코드 수 검증
- 기존 `tests/test_chatbot_core.py` — repo mock 추가하여 연동 확인
