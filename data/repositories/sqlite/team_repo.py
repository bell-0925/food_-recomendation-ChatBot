import uuid
from datetime import date, datetime, timezone, timedelta
from data.repositories.base import BaseTeamRepo
from data.database import SessionLocal
from data.repositories.sqlite.models import Team, VoteSession, Vote, VisitHistory


class SQLiteTeamRepo(BaseTeamRepo):
    def get_team(self, team_id):
        with SessionLocal() as db:
            t = db.get(Team, team_id)
            if not t:
                return None
            return {"team_id": t.team_id, "name": t.name,
                    "lat": t.lat, "lng": t.lng}

    def get_vote_results(self, team_id, target_date):
        with SessionLocal() as db:
            session = db.query(VoteSession).filter(
                VoteSession.team_id == team_id,
                VoteSession.date == target_date,
            ).first()
            if not session:
                return []
            from sqlalchemy import func
            from data.repositories.sqlite.models import Restaurant
            rows = (
                db.query(Vote.restaurant_id,
                         Restaurant.name,
                         func.count(Vote.id).label("vote_count"))
                .join(Restaurant, Vote.restaurant_id == Restaurant.place_id)
                .filter(Vote.session_id == session.session_id)
                .group_by(Vote.restaurant_id)
                .order_by(func.count(Vote.id).desc())
                .all()
            )
            return [{"restaurant_id": r.restaurant_id,
                     "name": r.name, "vote_count": r.vote_count}
                    for r in rows]

    def cast_vote(self, user_id, team_id, restaurant_id):
        today = date.today()
        with SessionLocal() as db:
            session = db.query(VoteSession).filter(
                VoteSession.team_id == team_id,
                VoteSession.date == today,
                VoteSession.status == "open",
            ).first()
            if not session:
                session = VoteSession(
                    session_id=str(uuid.uuid4()),
                    team_id=team_id, date=today, status="open",
                )
                db.add(session)
                db.flush()
            vote = Vote(
                session_id=session.session_id,
                user_id=user_id, restaurant_id=restaurant_id,
            )
            db.add(vote)
            db.commit()
            return {"result": "투표 완료", "restaurant_id": restaurant_id,
                    "session_id": session.session_id}

    def get_visit_history(self, team_id, days=30):
        since = date.today() - timedelta(days=days)
        with SessionLocal() as db:
            rows = db.query(VisitHistory).filter(
                VisitHistory.team_id == team_id,
                VisitHistory.visited_at >= since,
            ).order_by(VisitHistory.visited_at.desc()).all()
            return [{"restaurant_id": r.restaurant_id,
                     "visited_at": str(r.visited_at),
                     "headcount": r.headcount} for r in rows]
