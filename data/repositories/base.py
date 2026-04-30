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
