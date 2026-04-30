from data.repositories.base import BaseNutritionRepo


class FoodSafetyRepo(BaseNutritionRepo):
    """TODO: 식품안전처 Open API 연동. DATA_SOURCE=api 설정 시 사용."""

    def get_by_category(self, food_category: str) -> dict | None:
        raise NotImplementedError("식품안전처 API 미구현 — DATA_SOURCE=sqlite 사용")

    def get_meal_history(self, user_id: str, days: int = 7) -> list[dict]:
        raise NotImplementedError

    def record_meal(self, user_id: str, restaurant_id: str,
                    meal_name: str, satisfaction: int) -> dict:
        raise NotImplementedError
