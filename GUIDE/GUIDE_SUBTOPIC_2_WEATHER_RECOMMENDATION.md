# 🌤️ 소주제 2: 날씨·미세먼지 연동 메뉴 추천 — Claude Code 구현 가이드라인

> **목표**: 기상청 단기예보 API와 에어코리아 대기질 API를 연동하여,
> 당일 날씨 조건에 최적화된 메뉴 유형을 추천하는 파이프라인을 구축합니다.

---

## 📋 목차

1. [사전 준비](#1-사전-준비)
2. [프로젝트 구조 확장](#2-프로젝트-구조-확장)
3. [Step 1 — 기상청 단기예보 API 연동](#3-step-1--기상청-단기예보-api-연동)
4. [Step 2 — 에어코리아 대기질 API 연동](#4-step-2--에어코리아-대기질-api-연동)
5. [Step 3 — 날씨 데이터 통합 및 정제](#5-step-3--날씨-데이터-통합-및-정제)
6. [Step 4 — 날씨 기반 메뉴 적합도 엔진](#6-step-4--날씨-기반-메뉴-적합도-엔진)
7. [Step 5 — DB 적재 및 이력 관리](#7-step-5--db-적재-및-이력-관리)
8. [Step 6 — 테스트 및 검증](#8-step-6--테스트-및-검증)
9. [Step 7 — API 엔드포인트 확장](#9-step-7--api-엔드포인트-확장)
10. [트러블슈팅 가이드](#10-트러블슈팅-가이드)
11. [체크리스트](#11-체크리스트)

---

## 1. 사전 준비

### 1.1 API 키 발급

이 소주제에서는 공공데이터포털의 2개 API를 사용합니다. 두 API 모두 동일한 공공데이터포털 서비스키로 호출합니다.

| API | 신청 페이지 | 승인 방식 |
|-----|-----------|----------|
| 기상청 단기예보 조회서비스 | [공공데이터포털](https://www.data.go.kr/data/15084084/openapi.do) | 자동승인 |
| 에어코리아 대기오염정보 | [공공데이터포털](https://www.data.go.kr/data/15073861/openapi.do) | 자동승인 |
| 에어코리아 측정소정보 | [공공데이터포털](https://www.data.go.kr/data/15073877/openapi.do) | 자동승인 |

**발급 절차:**

1. [공공데이터포털](https://www.data.go.kr/) 회원가입 및 로그인
2. 위 3개 API 각각 "활용신청" 클릭
3. 마이페이지 → 데이터 활용 → Open API → 인증키 확인
4. **일반 인증키(Decoding)** 를 복사하여 `.env` 파일에 저장

### 1.2 핵심 개념 — 기상청 좌표 체계

기상청 API는 위도/경도(WGS84)가 아닌 **격자 좌표(nx, ny)** 를 사용합니다. 위도/경도를 격자 좌표로 변환하는 함수가 반드시 필요합니다.

```
서울시청: 위도 37.5665, 경도 126.9780 → nx=60, ny=127
강남역:   위도 37.4979, 경도 127.0276 → nx=61, ny=126
```

### 1.3 사용할 API 엔드포인트 상세

**기상청 단기예보 — 초단기실황 조회**

```
GET http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtNcst
```

| 파라미터 | 설명 | 예시 |
|---------|------|------|
| serviceKey | 인증키 | (발급받은 키) |
| numOfRows | 한 페이지 결과 수 | 10 |
| pageNo | 페이지 번호 | 1 |
| dataType | 응답 형식 | JSON |
| base_date | 발표 일자 | 20260405 |
| base_time | 발표 시각 | 1100 |
| nx | 격자 X 좌표 | 60 |
| ny | 격자 Y 좌표 | 127 |

**초단기실황 응답 카테고리 코드:**

| 코드 | 의미 | 단위 |
|------|------|------|
| T1H | 기온 | ℃ |
| RN1 | 1시간 강수량 | mm |
| UUU | 동서바람성분 | m/s |
| VVV | 남북바람성분 | m/s |
| REH | 습도 | % |
| PTY | 강수형태 | 코드 (0=없음, 1=비, 2=비/눈, 3=눈, 5=빗방울, 6=빗방울눈날림, 7=눈날림) |
| VEC | 풍향 | deg |
| WSD | 풍속 | m/s |

**기상청 단기예보 — 단기예보 조회**

```
GET http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst
```

**단기예보 추가 카테고리 코드:**

| 코드 | 의미 | 단위/값 |
|------|------|---------|
| POP | 강수확률 | % |
| SKY | 하늘상태 | 1=맑음, 3=구름많음, 4=흐림 |
| TMP | 1시간 기온 | ℃ |
| TMN | 일 최저기온 | ℃ |
| TMX | 일 최고기온 | ℃ |

**에어코리아 — 측정소별 실시간 측정정보 조회**

```
GET http://apis.data.go.kr/B552584/ArpltnInforInqireSvc/getMsrstnAcctoRltmMesureDnsty
```

| 파라미터 | 설명 | 예시 |
|---------|------|------|
| serviceKey | 인증키 | (발급받은 키) |
| returnType | 응답 형식 | json |
| numOfRows | 결과 수 | 1 |
| pageNo | 페이지 번호 | 1 |
| stationName | 측정소명 | 종로구 |
| dataTerm | 데이터 기간 | DAILY |
| ver | 버전 | 1.0 |

**에어코리아 응답 주요 필드:**

| 필드 | 의미 | 단위 |
|------|------|------|
| pm10Value | 미세먼지(PM10) | ㎍/㎥ |
| pm25Value | 초미세먼지(PM2.5) | ㎍/㎥ |
| pm10Grade | PM10 등급 | 1=좋음, 2=보통, 3=나쁨, 4=매우나쁨 |
| pm25Grade | PM2.5 등급 | 1=좋음, 2=보통, 3=나쁨, 4=매우나쁨 |
| khaiValue | 통합대기환경지수 | 수치 |
| khaiGrade | 통합 등급 | 1~4 |
| dataTime | 측정 시각 | 2026-04-05 11:00 |

---

## 2. 프로젝트 구조 확장

### Claude Code 프롬프트

```
소주제 1의 기존 프로젝트 구조에 소주제 2 관련 파일들을 추가해줘.

추가할 파일:
- pipeline/collectors/weather_collector.py     # 기상청 API 수집기
- pipeline/collectors/air_quality_collector.py  # 에어코리아 API 수집기
- pipeline/transformers/weather_scorer.py       # 날씨 기반 메뉴 적합도 산출
- pipeline/utils/coordinate_converter.py        # 위경도 → 격자좌표 변환
- database/models.py에 WeatherLog 모델 추가
- tests/test_weather_collector.py
- tests/test_air_quality_collector.py
- tests/test_weather_scorer.py

.env.example에 다음 변수도 추가해줘:
- DATA_GO_KR_SERVICE_KEY: 공공데이터포털 서비스키
- NEAREST_STATION_NAME: 가장 가까운 에어코리아 측정소명 (기본값: 종로구)
```

---

## 3. Step 1 — 기상청 단기예보 API 연동

### 3.1 좌표 변환 유틸리티 프롬프트

```
pipeline/utils/coordinate_converter.py를 구현해줘.

위경도(WGS84) 좌표를 기상청 격자 좌표(nx, ny)로 변환하는 함수가 필요해.

기상청에서 제공하는 Lambert Conformal Conic 투영 변환 공식을 사용해야 해.
변환 파라미터:
- 지구 반경: 6371.00877 km
- 격자 간격: 5.0 km
- 표준위도1: 30.0
- 표준위도2: 60.0
- 기준점 위도: 38.0
- 기준점 경도: 126.0
- 기준점 격자 X: 43
- 기준점 격자 Y: 136

함수 시그니처:
def latlon_to_grid(lat: float, lon: float) -> tuple[int, int]:
    """위경도를 기상청 격자좌표로 변환합니다.
    
    Args:
        lat: 위도 (예: 37.5665)
        lon: 경도 (예: 126.9780)
    
    Returns:
        (nx, ny) 격자좌표 튜플 (예: (60, 127))
    """

검증 테스트 케이스:
- 서울시청(37.5665, 126.9780) → (60, 127)
- 부산시청(35.1796, 129.0756) → (98, 76)
- 제주시청(33.4996, 126.5312) → (52, 38)
```

### 3.2 기상청 수집기 프롬프트

```
pipeline/collectors/weather_collector.py를 구현해줘.

WeatherCollector 클래스:

1. __init__(self, service_key: str, nx: int, ny: int):
   기상청 API 서비스키와 격자좌표 초기화

2. _get_base_datetime() -> tuple[str, str]:
   현재 시각 기준으로 가장 최근 단기예보 발표 시각을 계산.
   단기예보 발표시각: 0200, 0500, 0800, 1100, 1400, 1700, 2000, 2300
   API 제공 시각은 발표 후 약 10분이므로, 발표시각+10분 이후부터 사용 가능.
   예: 현재 11:05 → base_time=0800 사용 (1100 발표 데이터는 11:10부터 가능)
   예: 현재 11:15 → base_time=1100 사용
   반환: (base_date, base_time) 예: ("20260405", "1100")

3. get_ultra_srt_ncst() -> dict:
   초단기실황 조회 API 호출.
   반환: {"temp": 12.5, "humidity": 55, "rain_type": 0, "rain_1h": 0.0,
          "wind_speed": 2.3, "wind_dir": 270}

4. get_vilage_fcst() -> dict:
   단기예보 조회 API 호출.
   현재 시각부터 가장 가까운 미래 예보 데이터를 파싱.
   반환: {"sky": 4, "pop": 30, "tmp": 13, "tmn": 8, "tmx": 18}
   sky 코드를 문자열로도 변환: 1→"맑음", 3→"구름많음", 4→"흐림"

5. collect() -> dict:
   초단기실황 + 단기예보를 합쳐서 통합 날씨 정보 반환.
   반환:
   {
     "temp": 12.5,
     "humidity": 55,
     "rain_type": 0,
     "rain_type_str": "없음",
     "rain_1h": 0.0,
     "wind_speed": 2.3,
     "sky": 4,
     "sky_str": "흐림",
     "pop": 30,
     "tmn": 8,
     "tmx": 18,
     "collected_at": "2026-04-05T11:30:00"
   }

에러 처리:
- API 응답의 resultCode가 "00"이 아닌 경우 로깅 후 None 반환
- 네트워크 에러 시 최대 3회 재시도 (exponential backoff)
- 공공데이터포털 특유의 XML 에러 응답도 처리
  (가끔 JSON 요청에도 XML 에러가 반환됨)

로깅 및 타입 힌트 포함해줘.
```

### 3.3 테스트 프롬프트

```
tests/test_weather_collector.py에 WeatherCollector의 단위 테스트를 작성해줘.

unittest.mock.patch로 requests.get을 모킹해줘.

테스트 케이스:
1. test_get_base_datetime_morning: 오전 11:15 → ("20260405", "1100")
2. test_get_base_datetime_before_publish: 오전 11:05 → ("20260405", "0800")
3. test_get_base_datetime_midnight: 자정 00:05 → (전날 날짜, "2300")
4. test_get_ultra_srt_ncst_success: 정상 응답 파싱 확인
5. test_get_vilage_fcst_success: 예보 데이터 파싱 및 sky 코드 변환 확인
6. test_collect_integration: collect()가 통합 dict를 올바르게 반환하는지
7. test_api_error_handling: resultCode != "00" 시 None 반환

기상청 API의 실제 응답 형식을 반영한 mock 데이터를 fixture로 정의해줘:
{
  "response": {
    "header": {"resultCode": "00", "resultMsg": "NORMAL_SERVICE"},
    "body": {
      "items": {
        "item": [
          {"category": "T1H", "obsrValue": "12.5", ...},
          {"category": "REH", "obsrValue": "55", ...}
        ]
      }
    }
  }
}
```

---

## 4. Step 2 — 에어코리아 대기질 API 연동

### 4.1 대기질 수집기 프롬프트

```
pipeline/collectors/air_quality_collector.py를 구현해줘.

AirQualityCollector 클래스:

1. __init__(self, service_key: str, station_name: str = "종로구"):
   에어코리아 API 서비스키와 측정소명 초기화

2. get_realtime_data() -> dict | None:
   측정소별 실시간 측정정보 조회 API 호출.
   dataTerm="DAILY", 가장 최근 1건만 조회.

   반환:
   {
     "pm10_value": 45,
     "pm25_value": 22,
     "pm10_grade": 2,
     "pm25_grade": 2,
     "pm10_grade_str": "보통",
     "pm25_grade_str": "보통",
     "khai_value": 68,
     "khai_grade": 2,
     "o3_value": 0.035,
     "data_time": "2026-04-05 11:00"
   }

   등급 문자열 변환:
   1 → "좋음", 2 → "보통", 3 → "나쁨", 4 → "매우나쁨"

   주의: pm10Value가 "-" 또는 빈 문자열인 경우가 있음 → None 처리

3. get_dust_level() -> str:
   PM10, PM2.5 중 더 나쁜 등급을 기준으로 종합 먼지 수준 반환.
   "좋음" | "보통" | "나쁨" | "매우나쁨"

에러 처리:
- 측정소명이 잘못된 경우 빈 응답 처리
- 점검 시간(새벽 1~5시) 데이터 누락 처리
- "-" 값 (장비 점검 등) 방어 코드

로깅 및 타입 힌트 포함해줘.
```

### 4.2 테스트 프롬프트

```
tests/test_air_quality_collector.py에 단위 테스트를 작성해줘.

테스트 케이스:
1. test_get_realtime_data_success: 정상 응답 파싱
2. test_grade_string_conversion: 등급 코드 → 문자열 변환 (1~4)
3. test_missing_value_handling: pm10Value가 "-"인 경우 None 처리
4. test_get_dust_level_worst: PM10=2, PM2.5=3 → "나쁨" (더 나쁜 쪽)
5. test_api_error_response: 에러 응답 시 None 반환

에어코리아 API 실제 응답 형식을 반영한 mock:
{
  "response": {
    "body": {
      "items": [{
        "pm10Value": "45",
        "pm25Value": "22",
        "pm10Grade": "2",
        "pm25Grade": "2",
        "khaiValue": "68",
        "khaiGrade": "2",
        "o3Value": "0.035",
        "dataTime": "2026-04-05 11:00"
      }]
    }
  }
}
```

---

## 5. Step 3 — 날씨 데이터 통합 및 정제

### Claude Code 프롬프트

```
pipeline/transformers/weather_scorer.py의 앞부분을 구현해줘.

WeatherDataIntegrator 클래스를 먼저 만들어줘.
이 클래스는 기상청 데이터와 에어코리아 데이터를 하나의 통합 객체로 합쳐주는 역할이야.

1. integrate(weather_data: dict, air_data: dict | None) -> dict:
   두 API의 결과를 하나의 dict로 합침.

   반환:
   {
     "temp": 12.5,
     "humidity": 55,
     "rain_type": 0,
     "rain_type_str": "없음",
     "rain_1h": 0.0,
     "wind_speed": 2.3,
     "sky": 4,
     "sky_str": "흐림",
     "pop": 30,
     "tmn": 8,
     "tmx": 18,
     "pm10": 45,
     "pm25": 22,
     "dust_grade": "보통",
     "outdoor_comfort": "보통",  # 종합 외출 쾌적도
     "collected_at": "2026-04-05T11:30:00"
   }

   에어코리아 데이터가 None인 경우 pm10/pm25/dust_grade를 None으로 설정.

2. calculate_outdoor_comfort(temp, rain_type, pop, dust_grade, wind_speed) -> str:
   종합 외출 쾌적도 산출:
   - "매우좋음": 기온 15~25, 비 없음, 강수확률 < 20%, 먼지 좋음, 풍속 < 3
   - "좋음": 기온 10~28, 비 없음, 강수확률 < 40%, 먼지 보통 이하
   - "보통": 기온 5~30, 먼지 나쁨 이하
   - "나쁨": 기온 0 미만 또는 35 이상, 비 있음, 먼지 나쁨
   - "매우나쁨": 미세먼지 매우나쁨 또는 폭우/폭설

타입 힌트, docstring 포함해줘.
```

---

## 6. Step 4 — 날씨 기반 메뉴 적합도 엔진

### Claude Code 프롬프트

```
pipeline/transformers/weather_scorer.py에 WeatherMenuScorer 클래스를 추가해줘.
이 클래스가 이 소주제의 핵심 로직이야.

WeatherMenuScorer:

1. calculate_weather_score(restaurant: dict, weather: dict) -> int:
   음식점의 메뉴 타입과 현재 날씨를 기반으로 0~100 적합도 점수를 산출.

   기본 점수: 50점에서 시작

   기온 기반 가산/감산:
   - 기온 < 5°C:
     - 국물/죽/탕 → +30
     - 면류(냉면 제외) → +15
     - 초밥/샐러드 → -10
   - 기온 5~10°C:
     - 국물/죽 → +25
     - 면류 → +10
   - 기온 10~15°C:
     - 대부분 메뉴 적합 → +5
   - 기온 25~30°C:
     - 냉면/초밥/샐러드 → +25
     - 국물/탕 → -10
   - 기온 > 30°C:
     - 냉면/초밥/샐러드 → +30
     - 국물/탕/찌개 → -15

   강수 기반:
   - 비 오는 중(rain_type != 0) 또는 강수확률 > 60%:
     - 거리 200m 이내 → +15 (가까운 곳 우대)
     - 거리 400m 이상 → -15 (먼 곳 페널티)
     - 국물 메뉴 → +10 (비오는 날 국물)

   미세먼지 기반:
   - 먼지 "나쁨" 이상:
     - 실내 식당 → +15
     - (실외 좌석 있는 곳은 별도 처리 가능, Phase 2)

   바람 기반:
   - 풍속 > 8m/s:
     - 거리 300m 이상 → -10

   최종 점수는 0~100 범위로 클램핑.

2. get_weather_tips(weather: dict) -> list[str]:
   현재 날씨 조건에 따른 점심 추천 팁 문자열 리스트 생성.
   
   규칙:
   - temp < 5 → "영하권 강추위! 따뜻한 국물류를 추천합니다"
   - temp < 10 → "쌀쌀한 날씨에는 뜨끈한 국밥이나 찌개가 좋겠어요"
   - temp > 30 → "무더운 날씨! 시원한 냉면이나 초밥은 어떨까요"
   - pop > 60 → "비 올 확률이 높아요. 가까운 곳을 추천합니다"
   - rain_type != 0 → "현재 비가 오고 있어요. 실내 가까운 곳으로!"
   - dust_grade == "나쁨" → "미세먼지가 나쁩니다. 실내 식당을 이용하세요"
   - dust_grade == "매우나쁨" → "미세먼지 매우나쁨! 가급적 실내에서 식사하세요"
   - wind_speed > 8 → "바람이 강해요. 가까운 곳을 선택하세요"
   - 해당 없음 → "오늘은 어떤 메뉴든 좋은 날씨예요!"

3. rank_restaurants_by_weather(restaurants: list[dict], weather: dict) -> list[dict]:
   음식점 리스트에 weather_score를 추가하고 점수 내림차순 정렬.
   각 음식점 dict에 "weather_score" 키를 추가하여 반환.

4. get_menu_type_ranking(weather: dict) -> list[dict]:
   현재 날씨에서 각 메뉴 타입별 평균 적합도를 산출하여 랭킹.
   반환: [{"menu_type": "국물", "avg_score": 85}, {"menu_type": "초밥", "avg_score": 45}, ...]

타입 힌트, docstring, 로깅 포함해줘.
```

### 테스트 프롬프트

```
tests/test_weather_scorer.py에 WeatherMenuScorer의 테스트를 작성해줘.

테스트 케이스:

1. test_cold_weather_soup_bonus: 기온 3°C + 국물 메뉴 → 점수 75 이상
2. test_cold_weather_sushi_penalty: 기온 3°C + 초밥 → 점수 45 이하
3. test_hot_weather_cold_noodle_bonus: 기온 32°C + 냉면 → 점수 75 이상
4. test_rainy_day_nearby_bonus: 비 + 거리 150m → 가산점 확인
5. test_rainy_day_faraway_penalty: 비 + 거리 450m → 감산점 확인
6. test_dusty_day_indoor_bonus: 미세먼지 나쁨 + 실내 → 가산점 확인
7. test_perfect_weather_neutral: 기온 20°C, 맑음, 좋음 → 기본 55점 근처
8. test_get_weather_tips_cold: 기온 3°C → 국물 추천 팁 포함
9. test_get_weather_tips_rain: 강수확률 80% → 가까운 곳 추천 팁 포함
10. test_get_weather_tips_dust: 먼지 나쁨 → 실내 식당 팁 포함
11. test_rank_restaurants: 여러 음식점 랭킹이 점수 내림차순인지 확인

다양한 날씨 조건을 parametrize로 테스트해줘.
```

---

## 7. Step 5 — DB 적재 및 이력 관리

### Claude Code 프롬프트

```
database/models.py에 WeatherLog 모델을 추가해줘.

WeatherLog:
- id: Integer, PK, autoincrement
- collected_at: DateTime, NOT NULL, index=True
- temp: Float
- humidity: Integer
- rain_type: Integer
- rain_1h: Float
- wind_speed: Float
- sky: Integer
- sky_str: String(20)
- pop: Integer (강수확률)
- tmn: Float (일 최저기온)
- tmx: Float (일 최고기온)
- pm10: Integer, NULLABLE
- pm25: Integer, NULLABLE
- dust_grade: String(20), NULLABLE
- outdoor_comfort: String(20)

그리고 pipeline/loaders/db_loader.py에 WeatherLoader 클래스를 추가해줘:

1. save_weather_log(weather: dict) -> WeatherLog:
   통합 날씨 데이터를 DB에 저장하고 생성된 레코드 반환

2. get_latest_weather() -> WeatherLog | None:
   가장 최근 저장된 날씨 데이터 조회

3. get_weather_history(hours: int = 24) -> list[WeatherLog]:
   최근 N시간 이내의 날씨 이력 조회 (시간순 정렬)

4. get_today_weather_summary() -> dict:
   오늘 하루의 날씨 요약 통계:
   {"avg_temp": 14.2, "max_temp": 18, "min_temp": 8,
    "avg_pm10": 42, "rain_occurred": False, "dominant_sky": "흐림"}
```

---

## 8. Step 6 — 테스트 및 검증

### 통합 테스트 프롬프트

```
소주제 2의 전체 파이프라인을 통합 테스트하는 코드를 작성해줘.

테스트 시나리오:
1. WeatherCollector.collect() → mock 데이터 반환
2. AirQualityCollector.get_realtime_data() → mock 데이터 반환
3. WeatherDataIntegrator.integrate() → 통합 dict 생성
4. WeatherMenuScorer.rank_restaurants_by_weather() → 랭킹 생성
5. WeatherLoader.save_weather_log() → DB 저장

전체 흐름이 에러 없이 동작하는지 확인.
인메모리 SQLite DB 사용.

또한 pipeline/scheduler.py에 소주제 2 파이프라인을 추가해줘:
- WeatherPipeline.run_pipeline() 메서드
- 1시간마다 자동 실행 (CronTrigger(minute=0))
- 음식점 데이터와 날씨 데이터를 결합하여 weather_score 갱신
```

---

## 9. Step 7 — API 엔드포인트 확장

### Claude Code 프롬프트

```
api/main.py에 소주제 2 관련 엔드포인트를 추가해줘.

1. GET /api/weather/current
   - 최신 날씨 정보 조회
   - 응답: 통합 날씨 dict + 점심 추천 팁 리스트

2. GET /api/weather/history?hours=24
   - 최근 N시간 날씨 이력 조회

3. GET /api/weather/menu-ranking
   - 현재 날씨 기준 메뉴 타입별 적합도 랭킹
   - 응답: [{"menu_type": "국물", "avg_score": 85, "reason": "쌀쌀한 날씨"}, ...]

4. GET /api/restaurants/weather-ranked
   - 날씨 점수 반영 음식점 랭킹
   - Query params: limit(기본 10), category(선택)
   - 응답: weather_score 포함된 음식점 리스트

5. POST /api/weather/refresh
   - 날씨 데이터 수동 갱신 트리거

Pydantic 응답 모델:
- WeatherResponse: 현재 날씨 + 팁
- MenuRankingResponse: 메뉴 타입별 랭킹
- WeatherRankedRestaurantResponse: 날씨 점수 포함 음식점

각 엔드포인트에 적절한 캐싱 전략 주석도 추가해줘.
(날씨 데이터는 1시간 캐싱 권장)
```

---

## 10. 트러블슈팅 가이드

### 자주 발생하는 문제와 Claude Code 해결 프롬프트

**문제 1: 기상청 API에서 "SERVICE_KEY_IS_NOT_REGISTERED_ERROR" 반환**

```
기상청 API가 SERVICE_KEY_IS_NOT_REGISTERED_ERROR를 반환해.
서비스키의 URL Encoding/Decoding 이슈일 수 있어.
requests 라이브러리가 자동으로 URL 인코딩하면서 이중 인코딩이 발생하는 건 아닌지 확인해줘.
Decoding 키를 사용하고 requests의 params에 직접 전달하는 방식으로 수정해줘.
```

**문제 2: 기상청 API가 JSON 대신 XML 에러 반환**

```
기상청 API에 dataType=JSON으로 요청했는데 가끔 XML 형식의 에러가 반환돼.
응답의 Content-Type을 먼저 확인하고,
XML인 경우 에러 메시지를 파싱해서 로깅하는 방어 코드를 추가해줘.
```

**문제 3: base_time 계산 오류로 "NO_DATA" 반환**

```
기상청 단기예보 API에서 데이터가 없다고 반환해.
base_date와 base_time 계산 로직을 확인해줘.
특히 자정 전후(23:50 ~ 00:10)와 발표 직후(발표시각+10분 이내) 케이스를 처리해줘.
```

**문제 4: 에어코리아 측정소명 불일치**

```
에어코리아 API에서 stationName으로 검색이 안 돼.
측정소명을 "종로구"가 아닌 "종로"로 입력해야 하는 건 아닌지 확인해줘.
근접측정소 목록 조회 API를 사용해서 사무실 좌표 기준 가장 가까운 측정소를
자동으로 찾는 로직도 추가해줘.
```

**문제 5: 미세먼지 값이 "-"로 반환**

```
에어코리아 응답에서 pm10Value가 "-"로 들어와서 int 변환 시 ValueError가 발생해.
측정기 점검 시간에 이런 값이 나온다고 해.
"-" 또는 빈 문자열일 때 None으로 처리하고,
이전 유효 데이터를 fallback으로 사용하는 로직을 추가해줘.
```

---

## 11. 체크리스트

### 구현 완료 확인

```
소주제 2의 구현 상태를 점검해줘.
아래 체크리스트 항목별로 현재 상태를 확인하고,
미완료 항목이 있으면 구현해줘.
```

- [ ] `.env.example`에 `DATA_GO_KR_SERVICE_KEY`, `NEAREST_STATION_NAME` 추가
- [ ] 위경도 → 기상청 격자좌표 변환 함수 구현 및 검증
- [ ] `WeatherCollector._get_base_datetime()`이 자정/발표 직후 등 엣지 케이스 처리
- [ ] 초단기실황 API 호출 및 카테고리 코드(T1H, REH, PTY 등) 파싱
- [ ] 단기예보 API 호출 및 SKY/POP/TMP 파싱
- [ ] sky 코드 → 문자열 변환 (1=맑음, 3=구름많음, 4=흐림)
- [ ] `AirQualityCollector`가 PM10/PM2.5/등급을 정상 조회
- [ ] 등급 코드 → 문자열 변환 (1=좋음 ~ 4=매우나쁨)
- [ ] 결측값("-") 방어 코드 적용
- [ ] `WeatherDataIntegrator`가 두 API 데이터를 하나의 dict로 통합
- [ ] `outdoor_comfort` 종합 쾌적도 산출 로직
- [ ] `WeatherMenuScorer.calculate_weather_score()`가 기온/강수/먼지/바람 반영
- [ ] 메뉴 타입별 가산/감산 규칙이 테스트 통과
- [ ] `get_weather_tips()`이 조건별 팁 문자열 생성
- [ ] `rank_restaurants_by_weather()`가 점수 내림차순 랭킹
- [ ] `WeatherLog` ORM 모델 정의 완료
- [ ] `WeatherLoader`의 save/get_latest/get_history 동작 확인
- [ ] 1시간 주기 자동 갱신 스케줄러 설정
- [ ] FastAPI 엔드포인트 5개 추가 (/weather/current, /history, /menu-ranking 등)
- [ ] 단위 테스트: collector 7건 + air_quality 5건 + scorer 11건
- [ ] 통합 테스트: 전체 파이프라인 흐름 검증
- [ ] 전체 테스트 통과 (`pytest tests/ -v`)

---

## 부록: 소주제 1 ↔ 소주제 2 연동

소주제 2가 완성되면, 소주제 1의 음식점 데이터와 결합하여 **통합 추천 점수**를 산출할 수 있습니다.

```
통합 추천 엔진 연동을 위해 engine/recommender.py를 만들어줘.

CompositeScorer 클래스:

def calculate_composite_score(
    restaurant: dict,
    weather_score: int,
    distance_score: int,
    nutrition_score: int = 50,  # 소주제 3에서 구현
    team_score: int = 0         # 소주제 4에서 구현
) -> int:
    weights = {"distance": 0.3, "weather": 0.2, "nutrition": 0.2, "team": 0.3}
    return round(
        distance_score * weights["distance"] +
        weather_score * weights["weather"] +
        nutrition_score * weights["nutrition"] +
        team_score * weights["team"]
    )

소주제 3, 4가 완성되기 전까지는 nutrition_score=50, team_score=0을 기본값으로 사용해줘.
```

---

<div align="center">

**날씨와 미세먼지까지 고려하면, 점심 추천의 정확도가 한 단계 올라갑니다!**

*다음 단계: 소주제 3 — 영양 균형 분석 파이프라인*

</div>
