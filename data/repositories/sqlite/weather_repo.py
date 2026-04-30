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
