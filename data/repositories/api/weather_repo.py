from data.repositories.base import BaseWeatherRepo


class OpenWeatherRepo(BaseWeatherRepo):
    """TODO: OpenWeatherMap API 연동. DATA_SOURCE=api 설정 시 사용."""

    def get_current(self, lat: float, lng: float) -> dict:
        raise NotImplementedError("OpenWeather API 미구현 — DATA_SOURCE=sqlite 사용")

    def get_latest_cached(self) -> dict | None:
        raise NotImplementedError
