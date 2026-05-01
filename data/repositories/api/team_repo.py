from datetime import date
from data.repositories.base import BaseTeamRepo


class InternalAPITeamRepo(BaseTeamRepo):
    """TODO: 내부 팀 관리 API 연동. DATA_SOURCE=api 설정 시 사용."""

    def get_team(self, team_id: str) -> dict | None:
        raise NotImplementedError("내부 API 미구현 — DATA_SOURCE=sqlite 사용")

    def get_vote_results(self, team_id: str, target_date: date) -> list[dict]:
        raise NotImplementedError

    def cast_vote(self, user_id: str, team_id: str, restaurant_id: str) -> dict:
        raise NotImplementedError

    def get_visit_history(self, team_id: str, days: int = 30) -> list[dict]:
        raise NotImplementedError
