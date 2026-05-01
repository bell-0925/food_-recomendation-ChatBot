from data.repositories.base import BaseRestaurantRepo


class KakaoRestaurantRepo(BaseRestaurantRepo):
    """TODO: Kakao 로컬 API 연동. DATA_SOURCE=api 설정 시 사용."""

    def get_nearby(self, lat: float, lng: float, radius: int,
                   category: str | None = None) -> list[dict]:
        raise NotImplementedError("Kakao API 미구현 — DATA_SOURCE=sqlite 사용")

    def get_by_id(self, place_id: str) -> dict | None:
        raise NotImplementedError

    def search(self, keyword: str) -> list[dict]:
        raise NotImplementedError
