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
            result = []
            for r in rows:
                if r.lat is None or r.lng is None:
                    continue
                dlat = abs(r.lat - lat) * 111000
                dlng = abs(r.lng - lng) * 88000  # ~37°N 기준 경도 1도 ≈ 88km
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
                | Restaurant.address.contains(keyword)
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
