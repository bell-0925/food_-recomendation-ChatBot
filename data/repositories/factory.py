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
