from datetime import datetime, timedelta, timezone
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
        since = datetime.now(timezone.utc) - timedelta(days=days)
        with SessionLocal() as db:
            rows = db.query(MealHistory).filter(
                MealHistory.user_id == user_id,
                MealHistory.eaten_at >= since,
            ).order_by(MealHistory.eaten_at.desc()).all()
            return [self._to_dict(r) for r in rows]

    def record_meal(self, user_id, restaurant_id, meal_name, satisfaction):
        record = MealHistory(
            user_id=user_id, restaurant_id=restaurant_id,
            meal_name=meal_name, eaten_at=datetime.now(timezone.utc),
            satisfaction=satisfaction,
        )
        with SessionLocal() as db:
            try:
                db.add(record)
                db.commit()
                db.refresh(record)
                return self._to_dict(record)
            except Exception:
                db.rollback()
                raise

    @staticmethod
    def _to_dict(r: MealHistory) -> dict:
        return {
            "id": r.id, "user_id": r.user_id,
            "restaurant_id": r.restaurant_id, "meal_name": r.meal_name,
            "eaten_at": str(r.eaten_at), "satisfaction": r.satisfaction,
        }
