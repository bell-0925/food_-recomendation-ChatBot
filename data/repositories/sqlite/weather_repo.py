import logging
from data.repositories.base import BaseWeatherRepo
from data.database import SessionLocal
from data.repositories.sqlite.models import WeatherLog
from data.cache import TTLCache

logger = logging.getLogger(__name__)

_WEATHER_TTL = 600  # 10분


class SQLiteWeatherRepo(BaseWeatherRepo):
    def __init__(self) -> None:
        self._cache: TTLCache = TTLCache(ttl_seconds=_WEATHER_TTL)

    def get_current(self, lat, lng):
        """SQLite 모드에서는 최신 캐시를 반환."""
        return self.get_latest_cached() or {}

    def get_latest_cached(self):
        value, hit = self._cache.get("latest")
        if hit:
            logger.debug("Weather cache HIT")
            return value

        with SessionLocal() as db:
            row = db.query(WeatherLog).order_by(
                WeatherLog.recorded_at.desc()
            ).first()
            if not row:
                return None
            result = {
                "id": row.id, "recorded_at": str(row.recorded_at),
                "condition": row.condition, "temperature": row.temperature,
                "humidity": row.humidity, "wind_speed": row.wind_speed,
                "description": row.description,
            }

        self._cache.set("latest", result)
        logger.debug("Weather cache MISS → DB 조회 후 캐시 저장 (TTL %ds)", _WEATHER_TTL)
        return result
