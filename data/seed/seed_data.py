"""
가상 Seed 데이터 생성.
`python data/seed/seed_data.py` 또는 run_seed() 함수로 실행.
중복 실행 시 기존 데이터를 삭제하고 재삽입한다.
"""
import uuid
from datetime import datetime, date, timedelta, timezone
from data.database import SessionLocal, init_db
from data.repositories.sqlite.models import (
    Restaurant, WeatherLog, NutritionInfo, MealHistory,
    Team, User, VoteSession, Vote, VisitHistory, Veto
)


RESTAURANTS = [
    # 한식 6
    {"place_id": "place_001", "name": "명동칼국수", "category": "한식",
     "address": "서울 강남구 역삼동 101", "lat": 37.4981, "lng": 127.0278,
     "rating": 4.5, "review_count": 320, "open_time": "11:00", "close_time": "21:00"},
    {"place_id": "place_002", "name": "한솥도시락 역삼점", "category": "한식",
     "address": "서울 강남구 역삼동 202", "lat": 37.4975, "lng": 127.0265,
     "rating": 3.9, "review_count": 180, "open_time": "10:30", "close_time": "21:30"},
    {"place_id": "place_003", "name": "청국장골", "category": "한식",
     "address": "서울 강남구 역삼동 303", "lat": 37.4970, "lng": 127.0280,
     "rating": 4.3, "review_count": 210, "open_time": "11:00", "close_time": "20:30"},
    {"place_id": "place_004", "name": "제주돼지국밥", "category": "한식",
     "address": "서울 강남구 역삼동 404", "lat": 37.4965, "lng": 127.0272,
     "rating": 4.1, "review_count": 155, "open_time": "08:00", "close_time": "21:00"},
    {"place_id": "place_005", "name": "강남순대국", "category": "한식",
     "address": "서울 강남구 역삼동 505", "lat": 37.4988, "lng": 127.0260,
     "rating": 4.0, "review_count": 98, "open_time": "07:00", "close_time": "20:00"},
    {"place_id": "place_006", "name": "참이맛 한정식", "category": "한식",
     "address": "서울 강남구 역삼동 606", "lat": 37.4972, "lng": 127.0290,
     "rating": 4.6, "review_count": 275, "open_time": "11:30", "close_time": "22:00"},
    # 일식 4
    {"place_id": "place_007", "name": "사쿠라스시", "category": "일식",
     "address": "서울 강남구 역삼동 707", "lat": 37.4983, "lng": 127.0255,
     "rating": 4.4, "review_count": 390, "open_time": "11:30", "close_time": "22:00"},
    {"place_id": "place_008", "name": "라멘하우스", "category": "일식",
     "address": "서울 강남구 역삼동 808", "lat": 37.4962, "lng": 127.0268,
     "rating": 4.2, "review_count": 240, "open_time": "11:00", "close_time": "21:00"},
    {"place_id": "place_009", "name": "돈카츠마루", "category": "일식",
     "address": "서울 강남구 역삼동 909", "lat": 37.4990, "lng": 127.0285,
     "rating": 4.3, "review_count": 310, "open_time": "11:00", "close_time": "21:30"},
    {"place_id": "place_010", "name": "우동야", "category": "일식",
     "address": "서울 강남구 역삼동 1010", "lat": 37.4968, "lng": 127.0295,
     "rating": 3.8, "review_count": 120, "open_time": "11:30", "close_time": "20:30"},
    # 중식 3
    {"place_id": "place_011", "name": "차이나가든", "category": "중식",
     "address": "서울 강남구 역삼동 1111", "lat": 37.4977, "lng": 127.0300,
     "rating": 4.0, "review_count": 195, "open_time": "11:00", "close_time": "22:00"},
    {"place_id": "place_012", "name": "마라탕클럽", "category": "중식",
     "address": "서울 강남구 역삼동 1212", "lat": 37.4958, "lng": 127.0250,
     "rating": 4.5, "review_count": 430, "open_time": "11:00", "close_time": "23:00"},
    {"place_id": "place_013", "name": "짬뽕왕국", "category": "중식",
     "address": "서울 강남구 역삼동 1313", "lat": 37.4985, "lng": 127.0240,
     "rating": 3.7, "review_count": 88, "open_time": "10:30", "close_time": "21:00"},
    # 양식 3
    {"place_id": "place_014", "name": "파스타리아", "category": "양식",
     "address": "서울 강남구 역삼동 1414", "lat": 37.4960, "lng": 127.0310,
     "rating": 4.3, "review_count": 260, "open_time": "11:30", "close_time": "22:00"},
    {"place_id": "place_015", "name": "버거킹 강남역점", "category": "양식",
     "address": "서울 강남구 역삼동 1515", "lat": 37.4995, "lng": 127.0275,
     "rating": 3.5, "review_count": 520, "open_time": "08:00", "close_time": "23:00"},
    {"place_id": "place_016", "name": "더스테이크", "category": "양식",
     "address": "서울 강남구 역삼동 1616", "lat": 37.4973, "lng": 127.0245,
     "rating": 4.7, "review_count": 175, "open_time": "12:00", "close_time": "22:00"},
    # 분식 2
    {"place_id": "place_017", "name": "김밥나라 역삼점", "category": "분식",
     "address": "서울 강남구 역삼동 1717", "lat": 37.4980, "lng": 127.0315,
     "rating": 3.6, "review_count": 340, "open_time": "07:00", "close_time": "22:00"},
    {"place_id": "place_018", "name": "떡볶이왕", "category": "분식",
     "address": "서울 강남구 역삼동 1818", "lat": 37.4967, "lng": 127.0235,
     "rating": 4.1, "review_count": 280, "open_time": "11:00", "close_time": "21:00"},
    # 카페/샐러드 2
    {"place_id": "place_019", "name": "그린볼", "category": "카페",
     "address": "서울 강남구 역삼동 1919", "lat": 37.4992, "lng": 127.0320,
     "rating": 4.4, "review_count": 190, "open_time": "08:00", "close_time": "20:00"},
    {"place_id": "place_020", "name": "써브웨이 역삼점", "category": "카페",
     "address": "서울 강남구 역삼동 2020", "lat": 37.4955, "lng": 127.0325,
     "rating": 3.9, "review_count": 415, "open_time": "07:30", "close_time": "22:30"},
]

WEATHER_CONDITIONS = [
    ("sunny", 26.0, 45, 2.1, "맑고 따뜻한 날씨"),
    ("sunny", 28.0, 40, 1.8, "화창한 날씨"),
    ("cloudy", 22.0, 60, 3.0, "구름 많음"),
    ("cloudy", 20.0, 65, 2.5, "흐린 날씨"),
    ("rainy", 17.0, 85, 4.5, "비 내림"),
    ("sunny", 24.0, 50, 2.0, "맑음"),
    ("hot", 33.0, 55, 1.5, "매우 더운 날씨"),
]

NUTRITION_DATA = [
    ("한식", 580, 28, 72, 18, 1200, 6.5),
    ("일식", 520, 32, 58, 16, 980,  7.2),
    ("중식", 680, 24, 85, 22, 1450, 5.8),
    ("양식", 750, 35, 68, 32, 1100, 5.5),
    ("분식", 620, 18, 95, 14, 1350, 5.0),
    ("카페", 420, 15, 55, 12, 650,  7.8),
    ("패스트푸드", 820, 30, 95, 38, 1600, 4.2),
    ("베트남식", 490, 22, 65, 14, 900, 7.5),
    ("인도식", 640, 20, 80, 24, 1050, 6.8),
    ("멕시코식", 710, 28, 78, 28, 1300, 5.9),
    ("채식", 380, 14, 60, 10, 550, 8.5),
    ("해산물", 440, 42, 35, 12, 750, 8.0),
]


def run_seed():
    """DB를 초기화하고 가상 데이터를 삽입한다."""
    with SessionLocal() as db:
        try:
            # 기존 데이터 삭제 (외래키 순서 주의)
            db.query(Veto).delete()
            db.query(VisitHistory).delete()
            db.query(Vote).delete()
            db.query(VoteSession).delete()
            db.query(MealHistory).delete()
            db.query(NutritionInfo).delete()
            db.query(WeatherLog).delete()
            db.query(User).delete()
            db.query(Team).delete()
            db.query(Restaurant).delete()
            db.commit()

            # 식당 20개
            for r in RESTAURANTS:
                db.add(Restaurant(**r))

            # 날씨 7일
            now = datetime.now(timezone.utc)
            for i, (cond, temp, hum, wind, desc) in enumerate(WEATHER_CONDITIONS):
                db.add(WeatherLog(
                    recorded_at=now - timedelta(days=6 - i),
                    condition=cond, temperature=temp,
                    humidity=hum, wind_speed=wind, description=desc,
                    lat=37.4979, lng=127.0276,
                ))

            # 영양 정보 12개
            for cat, cal, prot, carb, fat, sod, score in NUTRITION_DATA:
                db.add(NutritionInfo(
                    food_category=cat, avg_calories=cal, avg_protein=prot,
                    avg_carbs=carb, avg_fat=fat, avg_sodium=sod, health_score=score,
                ))

            # 팀 & 유저
            db.add(Team(team_id="team_alpha", name="알파팀",
                        lat=37.4979, lng=127.0276))
            user_names = ["김민준", "이서연", "박지호", "최예은", "정우진"]
            for i, name in enumerate(user_names, 1):
                db.add(User(user_id=f"user_0{i}", name=name, team_id="team_alpha"))
            db.flush()

            # 식사 기록 25개 (5명 × 5일)
            meal_pairs = [
                ("place_001", "칼국수"),   ("place_007", "스시세트"),
                ("place_012", "마라탕"),   ("place_014", "봉골레파스타"),
                ("place_003", "청국장"),
            ]
            for day in range(5):
                eaten = now - timedelta(days=4 - day)
                for u_idx in range(1, 6):
                    rid, mname = meal_pairs[(u_idx - 1 + day) % 5]
                    db.add(MealHistory(
                        user_id=f"user_0{u_idx}", restaurant_id=rid,
                        meal_name=mname, eaten_at=eaten,
                        calories=550.0 + u_idx * 10,
                        satisfaction=3 + (u_idx + day) % 3,
                    ))

            # 투표 세션 3개 (지난 3일)
            vote_restaurants = [
                ["place_001", "place_007", "place_012"],
                ["place_002", "place_008", "place_014"],
                ["place_003", "place_009", "place_015"],
            ]
            for d_offset, picks in enumerate(vote_restaurants):
                session_date = date.today() - timedelta(days=2 - d_offset)
                sid = str(uuid.uuid4())
                status = "closed" if d_offset < 2 else "open"
                db.add(VoteSession(
                    session_id=sid, team_id="team_alpha",
                    date=session_date, status=status,
                ))
                db.flush()
                for u_idx in range(1, 6):
                    picked = picks[(u_idx - 1) % len(picks)]
                    db.add(Vote(
                        session_id=sid,
                        user_id=f"user_0{u_idx}",
                        restaurant_id=picked,
                    ))

            # 방문 기록 10개
            visit_data = [
                ("place_001", 5), ("place_007", 4), ("place_012", 5),
                ("place_002", 3), ("place_014", 4), ("place_008", 5),
                ("place_003", 4), ("place_009", 3), ("place_015", 5),
                ("place_001", 4),
            ]
            for i, (rid, cnt) in enumerate(visit_data):
                db.add(VisitHistory(
                    team_id="team_alpha", restaurant_id=rid,
                    visited_at=date.today() - timedelta(days=i),
                    headcount=cnt,
                ))

            # 거부 데이터 3개
            for u, r in [("user_01", "place_013"), ("user_02", "place_015"),
                         ("user_03", "place_018")]:
                db.add(Veto(user_id=u, restaurant_id=r, reason="개인 취향"))

            db.commit()
            print("Seed 완료: 식당 20, 날씨 7, 영양 12, 식사기록 25, 투표 25, 방문 10, 거부 3")
        except Exception:
            db.rollback()
            raise


if __name__ == "__main__":
    init_db()
    run_seed()
