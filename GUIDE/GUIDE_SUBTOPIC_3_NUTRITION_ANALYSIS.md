# 📊 소주제 3: 영양 균형 분석 — Claude Code 구현 가이드라인

> **목표**: 식품안전나라 영양성분 API를 연동하여 음식점 메뉴의 영양 정보를 매핑하고,
> 주간 단위 탄·단·지 비율 추적 및 영양 밸런스 자동 진단 파이프라인을 구축합니다.

---

## 📋 목차

1. [사전 준비](#1-사전-준비)
2. [프로젝트 구조 확장](#2-프로젝트-구조-확장)
3. [Step 1 — 식품안전나라 영양성분 API 연동](#3-step-1--식품안전나라-영양성분-api-연동)
4. [Step 2 — 메뉴-영양소 매핑 엔진](#4-step-2--메뉴-영양소-매핑-엔진)
5. [Step 3 — 식사 기록 및 주간 영양 추적](#5-step-3--식사-기록-및-주간-영양-추적)
6. [Step 4 — 영양 밸런스 진단 엔진](#6-step-4--영양-밸런스-진단-엔진)
7. [Step 5 — 영양 기반 추천 점수 산출](#7-step-5--영양-기반-추천-점수-산출)
8. [Step 6 — DB 모델 및 적재](#8-step-6--db-모델-및-적재)
9. [Step 7 — 테스트 및 검증](#9-step-7--테스트-및-검증)
10. [Step 8 — API 엔드포인트 확장](#10-step-8--api-엔드포인트-확장)
11. [트러블슈팅 가이드](#11-트러블슈팅-가이드)
12. [체크리스트](#12-체크리스트)

---

## 1. 사전 준비

### 1.1 API 키 발급

| API | 발급처 | 링크 |
|-----|-------|------|
| 식품영양성분DB (I2790) | 식품안전나라 (식약처) | [식품안전나라 API](https://www.foodsafetykorea.go.kr/api/main.do) |
| 식품영양성분DB (공공데이터포털) | 공공데이터포털 | [공공데이터포털](https://www.data.go.kr/data/15127578/openapi.do) |

**발급 절차 (식품안전나라 직접 발급 권장):**

1. [식품안전나라 데이터활용서비스](https://www.foodsafetykorea.go.kr/api/main.do) 접속
2. 회원가입 및 로그인
3. "인증키 발급" 클릭 → 자동 발급
4. 마이페이지에서 인증키 확인

### 1.2 API 엔드포인트 상세

**식품영양성분DB (I2790)**

```
GET https://openapi.foodsafetykorea.go.kr/api/{KEY}/I2790/json/{startIdx}/{endIdx}
```

| 파라미터 | 설명 | 예시 |
|---------|------|------|
| KEY | 인증키 | (발급받은 키) |
| I2790 | 서비스 ID | 고정값 |
| json | 응답 형식 | json 또는 xml |
| startIdx | 시작 인덱스 | 1 |
| endIdx | 종료 인덱스 | 100 |

**식품명 필터 검색:**

```
GET https://openapi.foodsafetykorea.go.kr/api/{KEY}/I2790/json/1/20/DESC_KOR={식품명}
```

**응답 예시:**

```json
{
  "I2790": {
    "RESULT": { "MSG": "정상처리되었습니다.", "CODE": "INFO-000" },
    "total_count": "59886",
    "row": [
      {
        "NUM": "1",
        "FOOD_CD": "D000006",
        "DESC_KOR": "꿩불고기",
        "SERVING_SIZE": "500",
        "NUTR_CONT1": "368.8",
        "NUTR_CONT2": "39.7",
        "NUTR_CONT3": "33.5",
        "NUTR_CONT4": "8.5",
        "NUTR_CONT5": "16.9",
        "NUTR_CONT6": "1264.31",
        "NUTR_CONT7": "106.18",
        "NUTR_CONT8": "1.9",
        "NUTR_CONT9": "0.1",
        "GROUP_NAME": "",
        "MAKER_NAME": "",
        "SUB_REF_NAME": "식약처('16) 제4권",
        "RESEARCH_YEAR": "2019"
      }
    ]
  }
}
```

**영양성분 필드 매핑:**

| API 필드 | 의미 | 단위 |
|---------|------|------|
| NUTR_CONT1 | 열량(에너지) | kcal |
| NUTR_CONT2 | 탄수화물 | g |
| NUTR_CONT3 | 단백질 | g |
| NUTR_CONT4 | 지방 | g |
| NUTR_CONT5 | 당류 | g |
| NUTR_CONT6 | 나트륨 | mg |
| NUTR_CONT7 | 콜레스테롤 | mg |
| NUTR_CONT8 | 포화지방산 | g |
| NUTR_CONT9 | 트랜스지방 | g |
| SERVING_SIZE | 1회 제공량 | g |
| DESC_KOR | 식품명(한글) | - |
| FOOD_CD | 식품코드 | - |
| GROUP_NAME | 식품 분류 | - |

### 1.3 영양 기준값 (한국인 영양소 섭취기준)

점심 1끼 기준 권장량 (일일 권장량의 약 35%):

| 영양소 | 점심 1끼 권장량 | 일일 권장량 | 비고 |
|--------|--------------|-----------|------|
| 열량 | 600~700 kcal | 2,000 kcal | 성인 남녀 평균 |
| 탄수화물 | 80~100g | 300g | 총 열량의 55~65% |
| 단백질 | 20~30g | 65g | 총 열량의 15~20% |
| 지방 | 15~22g | 54g | 총 열량의 15~30% |
| 나트륨 | < 800mg | < 2,300mg | 과다 섭취 주의 |
| 당류 | < 18g | < 50g | 총 열량의 10% 이내 |

---

## 2. 프로젝트 구조 확장

### Claude Code 프롬프트

```
기존 프로젝트 구조에 소주제 3 관련 파일들을 추가해줘.

추가할 파일:
- pipeline/collectors/nutrition_collector.py     # 식품안전나라 API 수집기
- pipeline/transformers/nutrition_scorer.py       # 영양 분석 및 점수 산출
- pipeline/utils/nutrition_standards.py           # 영양 기준값 상수 정의
- database/models.py에 NutritionInfo, MealHistory 모델 추가
- tests/test_nutrition_collector.py
- tests/test_nutrition_scorer.py

.env.example에 추가:
- FOOD_SAFETY_API_KEY: 식품안전나라 인증키

requirements.txt에 추가:
- fuzzywuzzy==0.18.0 (또는 thefuzz==0.22.1)
- python-Levenshtein==0.26.1 (fuzzy matching 속도 향상)
```

---

## 3. Step 1 — 식품안전나라 영양성분 API 연동

### 3.1 영양 기준 상수 모듈 프롬프트

```
pipeline/utils/nutrition_standards.py를 구현해줘.

점심 1끼 기준 영양소 권장량을 상수로 정의해줘:

LUNCH_STANDARDS = {
    "calories": {"min": 500, "max": 800, "target": 650, "unit": "kcal"},
    "carbs":    {"min": 65, "max": 110, "target": 85, "unit": "g"},
    "protein":  {"min": 20, "max": 40, "target": 28, "unit": "g"},
    "fat":      {"min": 10, "max": 25, "target": 18, "unit": "g"},
    "sodium":   {"max": 800, "unit": "mg"},
    "sugar":    {"max": 18, "unit": "g"},
}

탄단지 이상적 비율도 정의:
IDEAL_MACRO_RATIO = {
    "carbs": 0.55,    # 55~65%
    "protein": 0.20,  # 15~20%
    "fat": 0.25,      # 15~30%
}

영양 상태 판정 기준도 enum으로 정의:
class NutritionStatus(Enum):
    DEFICIENT = "부족"
    ADEQUATE = "적정"
    EXCESSIVE = "과다"

def judge_nutrient(nutrient: str, value: float) -> NutritionStatus:
    기준값 대비 80% 미만이면 DEFICIENT, 120% 초과면 EXCESSIVE, 그 사이면 ADEQUATE
```

### 3.2 영양성분 수집기 프롬프트

```
pipeline/collectors/nutrition_collector.py를 구현해줘.

NutritionCollector 클래스:

1. __init__(self, api_key: str):
   식품안전나라 API 인증키로 초기화.
   base_url = "https://openapi.foodsafetykorea.go.kr/api"

2. search_by_name(food_name: str, max_results: int = 20) -> list[dict]:
   식품명으로 영양성분 검색.
   URL: {base_url}/{api_key}/I2790/json/1/{max_results}/DESC_KOR={food_name}

   반환: 정제된 영양정보 dict 리스트
   [
     {
       "food_code": "D000006",
       "food_name": "꿩불고기",
       "serving_size": 500.0,
       "calories": 368.8,
       "carbs": 39.7,
       "protein": 33.5,
       "fat": 8.5,
       "sugar": 16.9,
       "sodium": 1264.31,
       "cholesterol": 106.18,
       "saturated_fat": 1.9,
       "trans_fat": 0.1,
       "source": "식약처('16) 제4권",
       "year": "2019"
     }
   ]

   주의:
   - NUTR_CONT 필드가 빈 문자열("")인 경우 0.0으로 처리
   - NUTR_CONT 필드가 "N/A"인 경우 None으로 처리
   - SERVING_SIZE가 없으면 100g으로 기본값 설정

3. search_bulk(food_names: list[str]) -> dict[str, list[dict]]:
   여러 식품명을 일괄 검색. API 호출 간 0.5초 sleep.
   반환: {food_name: [nutrition_results]}

4. get_by_code(food_code: str) -> dict | None:
   식품코드로 특정 식품의 영양정보 조회.

에러 처리:
- RESULT.CODE가 "INFO-000"이 아닌 경우:
  - "INFO-200": 해당하는 데이터가 없습니다 → 빈 리스트 반환
  - "INFO-300": 잘못된 요청 → 로깅 후 None 반환
- 네트워크 에러 시 3회 재시도
- 응답이 JSON이 아닌 경우 (가끔 HTML 에러 페이지 반환) 방어 코드

로깅 및 타입 힌트 포함해줘.
```

### 3.3 테스트 프롬프트

```
tests/test_nutrition_collector.py에 단위 테스트를 작성해줘.

테스트 케이스:
1. test_search_by_name_success: "김치찌개" 검색 시 정상 결과 반환
2. test_search_by_name_no_result: 존재하지 않는 식품명 → 빈 리스트
3. test_empty_nutrient_fields: NUTR_CONT1이 ""인 경우 0.0 처리
4. test_na_nutrient_fields: NUTR_CONT3이 "N/A"인 경우 None 처리
5. test_missing_serving_size: SERVING_SIZE가 ""인 경우 100.0 기본값
6. test_search_bulk: 3개 식품명 일괄 검색 결과 확인
7. test_api_error_info200: "INFO-200" 코드 시 빈 리스트

I2790 API 응답 형식을 반영한 mock fixture를 정의해줘.
```

---

## 4. Step 2 — 메뉴-영양소 매핑 엔진

### Claude Code 프롬프트

```
pipeline/transformers/nutrition_scorer.py의 앞부분에
MenuNutritionMapper 클래스를 구현해줘.

이 클래스는 음식점의 메뉴 이름(또는 카테고리)을 영양성분 DB와 매핑하는 역할이야.
정확한 1:1 매핑이 어렵기 때문에 퍼지 매칭을 사용해야 해.

MenuNutritionMapper:

1. __init__(self, collector: NutritionCollector):
   NutritionCollector 인스턴스를 받아 초기화.
   내부에 매핑 캐시(dict)를 유지.

2. find_best_match(menu_name: str) -> dict | None:
   메뉴명으로 영양성분 DB를 검색하고 가장 유사한 결과를 반환.

   매핑 전략 (우선순위 순):
   a. 캐시에 이미 매핑된 결과가 있으면 즉시 반환
   b. 정확히 일치하는 이름이 있으면 반환
   c. fuzzywuzzy의 extractOne으로 유사도 80% 이상인 결과 반환
   d. 메뉴명을 단순화 (예: "서브웨이 이탈리안BMT" → "이탈리안BMT") 후 재검색
   e. 매핑 실패 시 None 반환

3. map_restaurant_to_nutrition(restaurant: dict) -> dict | None:
   음식점의 category + sub_category + menu_type 정보를 기반으로
   대표 메뉴의 영양 정보를 추정.

   매핑 로직:
   - sub_category가 있으면: sub_category로 검색 (예: "도시락" → 도시락 검색)
   - menu_type이 있으면: menu_type으로 검색 (예: "국물" → 국물 대표 메뉴)
   - category만 있으면: 카테고리별 평균 영양 값 사용

4. get_category_avg_nutrition(category: str) -> dict:
   카테고리별 기본 영양 정보 반환 (사전 정의된 기본값 사용).

   기본값 테이블:
   - 한식(밥류): {"calories": 650, "protein": 25, "carbs": 90, "fat": 18}
   - 한식(국물): {"calories": 480, "protein": 20, "carbs": 55, "fat": 12}
   - 일식(초밥): {"calories": 520, "protein": 28, "carbs": 68, "fat": 14}
   - 양식(파스타): {"calories": 680, "protein": 22, "carbs": 85, "fat": 28}
   - 양식(버거): {"calories": 780, "protein": 35, "carbs": 62, "fat": 42}
   - 중식: {"calories": 720, "protein": 24, "carbs": 88, "fat": 30}
   - 동남아: {"calories": 520, "protein": 22, "carbs": 65, "fat": 16}
   (이 값들은 fallback용으로, 실제 API 매핑에 실패했을 때만 사용)

5. build_nutrition_cache(restaurants: list[dict]) -> dict:
   전체 음식점 리스트를 순회하며 영양 정보를 일괄 매핑.
   반환: {restaurant_id: nutrition_dict}
   진행 상황 로깅.

fuzzywuzzy(또는 thefuzz) 사용 시 python-Levenshtein 설치 안내 주석 포함.
타입 힌트, docstring, 로깅 포함해줘.
```

---

## 5. Step 3 — 식사 기록 및 주간 영양 추적

### Claude Code 프롬프트

```
pipeline/transformers/nutrition_scorer.py에
MealTracker 클래스를 추가해줘.

이 클래스는 사용자의 식사 기록을 관리하고 주간 영양 섭취를 추적하는 역할이야.

MealTracker:

1. record_meal(user_id: str, restaurant_id: str, menu_name: str,
               nutrition: dict, meal_date: date = None) -> dict:
   식사 기록을 저장.
   meal_date가 None이면 오늘 날짜 사용.
   반환: 저장된 기록 dict (id 포함)

2. get_weekly_summary(user_id: str, week_offset: int = 0) -> dict:
   특정 주간의 영양 섭취 요약.
   week_offset=0이면 이번 주, -1이면 지난 주.

   반환:
   {
     "period": {"start": "2026-03-30", "end": "2026-04-05"},
     "meal_count": 4,
     "daily_records": [
       {"date": "2026-03-31", "day": "월", "calories": 680, "protein": 28,
        "carbs": 85, "fat": 22, "sodium": 950},
       ...
     ],
     "weekly_avg": {
       "calories": 607.5, "protein": 26.5, "carbs": 73.2,
       "fat": 22.8, "sodium": 1050.3
     },
     "weekly_total": {
       "calories": 2430, "protein": 106, "carbs": 293, "fat": 91
     },
     "macro_ratio": {
       "carbs_pct": 59.8, "protein_pct": 21.6, "fat_pct": 18.6
     },
     "recorded_days": 4,
     "missing_days": ["2026-04-04"]
   }

3. get_daily_detail(user_id: str, meal_date: date) -> dict | None:
   특정 날짜의 상세 식사 기록 조회.

4. get_nutrient_trend(user_id: str, days: int = 14) -> list[dict]:
   최근 N일간의 영양소별 트렌드 데이터.
   대시보드 차트용 시계열 데이터.
   반환: [{"date": "2026-04-01", "calories": 680, "protein": 28, ...}, ...]
```

---

## 6. Step 4 — 영양 밸런스 진단 엔진

### Claude Code 프롬프트

```
pipeline/transformers/nutrition_scorer.py에
NutritionDiagnostic 클래스를 추가해줘.

이 클래스가 소주제 3의 핵심 분석 엔진이야.

NutritionDiagnostic:

1. diagnose_weekly(weekly_summary: dict) -> dict:
   주간 섭취 데이터를 기반으로 종합 영양 진단.

   반환:
   {
     "overall_status": "주의",  # "양호" | "주의" | "경고"
     "overall_score": 72,       # 0~100
     "nutrient_status": {
       "calories": {"status": "적정", "avg": 607.5, "target": 650,
                    "deviation_pct": -6.5},
       "protein":  {"status": "부족", "avg": 18.5, "target": 28,
                    "deviation_pct": -33.9},
       "carbs":    {"status": "과다", "avg": 95.0, "target": 85,
                    "deviation_pct": 11.8},
       "fat":      {"status": "적정", "avg": 20.0, "target": 18,
                    "deviation_pct": 11.1},
       "sodium":   {"status": "과다", "avg": 1200.0, "max": 800,
                    "deviation_pct": 50.0},
     },
     "macro_balance": {
       "status": "불균형",
       "current_ratio": {"carbs": 62.3, "protein": 12.1, "fat": 25.6},
       "ideal_ratio":   {"carbs": 55.0, "protein": 20.0, "fat": 25.0},
       "verdict": "단백질 비율이 권장 범위(15~20%)보다 낮습니다"
     },
     "recommendations": [
       "단백질 섭취를 늘려보세요 (고기, 생선, 두부 등)",
       "나트륨 섭취가 많습니다. 국물을 남기는 습관을 추천합니다",
       "탄수화물 비중이 높습니다. 밥 양을 조금 줄여보세요"
     ],
     "diagnosed_at": "2026-04-05T12:00:00"
   }

2. _calculate_overall_score(nutrient_status: dict) -> int:
   각 영양소의 편차를 기반으로 종합 점수(0~100) 산출.
   모든 영양소가 적정이면 100점.
   부족/과다 1건당 -10~-15점 감산.
   나트륨 과다는 건강 리스크가 높으므로 -15점.

3. _generate_recommendations(nutrient_status: dict, macro_balance: dict) -> list[str]:
   부족/과다 영양소에 따른 실행 가능한 추천 메시지 생성.
   최대 5개까지만 반환 (우선순위: 단백질 부족 > 나트륨 과다 > 탄수화물 과다 > 지방 과다 > 칼로리).

4. compare_with_previous(current: dict, previous: dict) -> dict:
   이번 주와 지난 주 진단 결과를 비교.
   반환:
   {
     "score_change": +5,
     "improved": ["단백질"],
     "worsened": ["나트륨"],
     "unchanged": ["칼로리", "탄수화물", "지방"]
   }

타입 힌트, docstring, 로깅 포함해줘.
```

---

## 7. Step 5 — 영양 기반 추천 점수 산출

### Claude Code 프롬프트

```
pipeline/transformers/nutrition_scorer.py에
NutritionRecommendScorer 클래스를 추가해줘.

이 클래스는 사용자의 주간 영양 섭취 이력을 기반으로,
"오늘 점심에 어떤 음식점이 영양적으로 좋은지" 점수를 산출해.

NutritionRecommendScorer:

1. calculate_nutrition_score(restaurant_nutrition: dict,
                             weekly_summary: dict) -> int:
   음식점의 추정 영양 정보와 이번 주 섭취 이력을 비교하여 0~100 점수 산출.

   점수 산출 로직:
   기본 60점에서 시작.

   보충 점수 (부족한 영양소를 보충하면 가산):
   - 주간 평균 단백질 < 25g인데, 이 음식점 단백질 > 30g → +20
   - 주간 평균 단백질 < 20g인데, 이 음식점 단백질 > 25g → +25
   - 주간 평균 칼로리 < 500인데, 이 음식점 칼로리 적정 범위 → +10

   억제 점수 (과다 영양소를 더 먹으면 감산):
   - 주간 평균 지방 > 30g인데, 이 음식점 지방 > 35g → -15
   - 주간 평균 나트륨 > 1000mg인데, 이 음식점 나트륨 > 1200mg → -15
   - 주간 평균 탄수화물 > 100g인데, 이 음식점 탄수화물 > 90g → -10

   균형 보너스:
   - 이 음식점의 탄단지 비율이 이상 비율(55:20:25)에 가까우면 → +10
   - 칼로리가 적정 범위(500~800)이면 → +5

   최종 0~100 클램핑.

2. rank_by_nutrition(restaurants_with_nutrition: list[dict],
                     weekly_summary: dict) -> list[dict]:
   음식점 리스트에 nutrition_score를 추가하고 내림차순 정렬.

3. get_nutrition_advice_for_restaurant(restaurant_nutrition: dict,
                                       weekly_summary: dict) -> str:
   특정 음식점 선택 시 영양 관점 한줄 코멘트.
   예: "이번 주 단백질이 부족했는데, 이 메뉴는 단백질이 풍부해서 좋은 선택이에요!"
   예: "이번 주 나트륨 섭취가 많았어요. 국물은 남기는 걸 추천합니다."

타입 힌트, docstring, 로깅 포함해줘.
```

---

## 8. Step 6 — DB 모델 및 적재

### Claude Code 프롬프트

```
database/models.py에 소주제 3 관련 모델 2개를 추가해줘.

NutritionInfo 모델 (음식점별 추정 영양 정보 캐시):
- id: Integer, PK, autoincrement
- restaurant_id: String, FK → restaurants.id
- food_name: String(100) (매핑된 식품명)
- food_code: String(20), NULLABLE
- match_type: String(20) (exact/fuzzy/category_avg)
- match_score: Float, NULLABLE (퍼지 매칭 유사도)
- serving_size: Float
- calories: Float
- carbs: Float
- protein: Float
- fat: Float
- sugar: Float, NULLABLE
- sodium: Float, NULLABLE
- mapped_at: DateTime

MealHistory 모델 (사용자 식사 기록):
- id: Integer, PK, autoincrement
- user_id: String(50), index=True
- restaurant_id: String, FK → restaurants.id
- meal_date: Date, NOT NULL, index=True
- menu_name: String(100), NULLABLE
- calories: Float
- carbs: Float
- protein: Float
- fat: Float
- sugar: Float, NULLABLE
- sodium: Float, NULLABLE
- satisfaction: Integer, NULLABLE (1~5점)
- created_at: DateTime

pipeline/loaders/db_loader.py에 NutritionLoader 클래스를 추가해줘:

1. save_nutrition_mapping(restaurant_id: str, nutrition: dict, match_type: str) -> NutritionInfo
2. get_nutrition_by_restaurant(restaurant_id: str) -> NutritionInfo | None
3. save_meal_record(record: dict) -> MealHistory
4. get_meal_history(user_id: str, start_date: date, end_date: date) -> list[MealHistory]
5. get_weekly_stats(user_id: str, week_start: date) -> dict
   (일별 칼로리/탄/단/지 합산 통계)

SQLAlchemy 2.0 스타일, relationship 설정 포함해줘.
```

---

## 9. Step 7 — 테스트 및 검증

### Claude Code 프롬프트

```
tests/test_nutrition_scorer.py에 영양 분석 엔진의 테스트를 작성해줘.

테스트 케이스:

MenuNutritionMapper:
1. test_find_best_match_exact: 정확히 일치하는 식품명 매핑
2. test_find_best_match_fuzzy: 유사한 식품명 퍼지 매칭 (유사도 80%+)
3. test_find_best_match_fail: 유사도 80% 미만 → None 반환
4. test_category_avg_fallback: API 매핑 실패 시 카테고리 평균값 반환

NutritionDiagnostic:
5. test_diagnose_balanced: 모든 영양소 적정 → overall_status="양호", score 85+
6. test_diagnose_protein_deficient: 주간 평균 단백질 15g → status="부족"
7. test_diagnose_sodium_excess: 주간 평균 나트륨 1500mg → status="과다"
8. test_macro_balance_check: 탄단지 비율 70:10:20 → "불균형" 판정
9. test_recommendations_priority: 단백질 부족 추천이 첫 번째로 나오는지

NutritionRecommendScorer:
10. test_score_high_protein_when_deficient: 단백질 부족 주간 + 고단백 메뉴 → 75+
11. test_score_low_fat_when_excess: 지방 과다 주간 + 저지방 메뉴 → 70+
12. test_score_penalty_sodium: 나트륨 과다 주간 + 고나트륨 메뉴 → 50 이하
13. test_rank_restaurants: 랭킹이 nutrition_score 내림차순인지

주간 영양 데이터 fixture를 다양한 시나리오로 정의해줘:
- balanced_week: 균형 잡힌 식사
- protein_deficient_week: 단백질 부족
- carb_heavy_week: 탄수화물 과다
- sodium_heavy_week: 나트륨 과다
```

---

## 10. Step 8 — API 엔드포인트 확장

### Claude Code 프롬프트

```
api/main.py에 소주제 3 관련 엔드포인트를 추가해줘.

1. GET /api/nutrition/restaurant/{restaurant_id}
   - 특정 음식점의 추정 영양 정보 조회
   - 매핑 타입(exact/fuzzy/category_avg)도 포함

2. POST /api/nutrition/meal
   - 식사 기록 저장
   - Body: {"user_id": "user1", "restaurant_id": "12345",
            "menu_name": "김치찌개", "satisfaction": 4}
   - 영양 정보 자동 매핑 후 저장

3. GET /api/nutrition/weekly?user_id=user1&week_offset=0
   - 주간 영양 섭취 요약 조회
   - 일별 칼로리/탄/단/지 + 주간 평균 + 탄단지 비율

4. GET /api/nutrition/diagnosis?user_id=user1
   - 영양 밸런스 진단 결과 조회
   - overall_status, nutrient_status, recommendations 포함

5. GET /api/nutrition/trend?user_id=user1&days=14
   - 최근 N일 영양소 트렌드 (차트용 시계열 데이터)

6. GET /api/restaurants/nutrition-ranked?user_id=user1
   - 사용자의 주간 영양 이력 기반 음식점 영양 점수 랭킹
   - Query params: limit(기본 10), category(선택)

Pydantic 응답 모델:
- NutritionInfoResponse: 음식점 영양 정보
- MealRecordRequest/Response: 식사 기록 요청/응답
- WeeklySummaryResponse: 주간 요약
- DiagnosisResponse: 진단 결과
- NutrientTrendResponse: 트렌드 데이터
```

---

## 11. 트러블슈팅 가이드

### 자주 발생하는 문제와 Claude Code 해결 프롬프트

**문제 1: 식품안전나라 API 인증키 오류**

```
식품안전나라 API에서 "인증키가 유효하지 않습니다" 에러가 발생해.
식품안전나라(foodsafetykorea.go.kr)에서 직접 발급한 키와
공공데이터포털(data.go.kr)에서 발급한 키는 서로 다른 키야.
현재 사용 중인 키가 어느 포털 키인지 확인하고,
올바른 base_url과 매칭되도록 수정해줘.
- 식품안전나라 키: openapi.foodsafetykorea.go.kr
- 공공데이터포털 키: apis.data.go.kr
```

**문제 2: 메뉴-영양소 퍼지 매칭 정확도 낮음**

```
"서브웨이 이탈리안BMT 15cm"를 검색하면 매칭이 안 돼.
메뉴명 전처리 로직을 강화해줘:
1. 브랜드명 제거 (서브웨이, 맥도날드, 롯데리아 등)
2. 사이즈 표기 제거 (15cm, 레귤러, 라지 등)
3. 특수문자 제거
4. 핵심 키워드만 추출하여 검색
예: "서브웨이 이탈리안BMT 15cm" → "이탈리안BMT"로 검색
```

**문제 3: 영양성분 값이 과도하게 크거나 작음**

```
SERVING_SIZE가 "100"인데 NUTR_CONT1(열량)이 "2500"인 데이터가 있어.
이건 100g당 2500kcal이라는 뜻인데 비현실적인 값이야.
이상치 탐지 로직을 추가해줘:
- 열량이 100g당 900kcal 초과 → 이상치로 판단
- 단백질이 100g당 100g 초과 → 이상치로 판단
이상치는 로깅 후 제외하고 다음 매칭 결과를 사용하도록 해줘.
```

**문제 4: 주간 요약에서 미기록 날짜 처리**

```
이번 주 5일 중 3일만 기록했는데 주간 평균이 왜곡돼.
기록이 있는 날짜만으로 평균을 산출하고,
미기록 날짜는 별도로 "missing_days"에 표시하도록 해줘.
또한 "기록 일수가 3일 미만이면 진단 정확도가 낮을 수 있습니다"
경고 메시지를 진단 결과에 포함해줘.
```

**문제 5: 동일 식품명에 여러 결과가 나옴**

```
"김치찌개"를 검색하면 "김치찌개", "참치김치찌개", "두부김치찌개" 등
여러 결과가 나와. 어떤 것을 대표값으로 사용해야 할지 모르겠어.
1. 정확히 일치하는 이름을 우선 선택
2. 정확 일치가 없으면 가장 짧은 이름(=가장 일반적인 메뉴)을 선택
3. GROUP_NAME이 "음식류"인 것을 우선 선택 (가공식품보다 외식 메뉴 우선)
이 로직을 find_best_match에 추가해줘.
```

---

## 12. 체크리스트

### 구현 완료 확인

```
소주제 3의 구현 상태를 점검해줘.
아래 체크리스트 항목별로 현재 상태를 확인하고,
미완료 항목이 있으면 구현해줘.
```

- [ ] `.env.example`에 `FOOD_SAFETY_API_KEY` 추가
- [ ] `nutrition_standards.py`에 점심 1끼 기준 영양 권장량 정의
- [ ] `NutritionCollector.search_by_name()`이 I2790 API를 정상 호출
- [ ] NUTR_CONT 필드의 빈 문자열/N/A 방어 코드 적용
- [ ] API 에러 코드 (INFO-000, INFO-200, INFO-300) 각각 처리
- [ ] `MenuNutritionMapper`의 퍼지 매칭 (유사도 80%+ 기준)
- [ ] 브랜드명/사이즈 제거 등 메뉴명 전처리 로직
- [ ] 카테고리 평균 영양값 fallback 테이블 정의
- [ ] `MealTracker`의 식사 기록 저장/조회 동작
- [ ] 주간 요약 산출 (일별 기록 + 주간 평균 + 탄단지 비율)
- [ ] 미기록 날짜 처리 (기록 있는 날짜만으로 평균 산출)
- [ ] `NutritionDiagnostic.diagnose_weekly()` 종합 진단 동작
- [ ] 영양소별 부족/적정/과다 판정 (기준값 대비 ±20%)
- [ ] 탄단지 비율 균형 판정
- [ ] 추천 메시지 생성 (우선순위: 단백질 > 나트륨 > 탄수화물 > 지방)
- [ ] 이전 주와 비교 분석 (score_change, improved/worsened)
- [ ] `NutritionRecommendScorer`의 보충/억제 점수 산출
- [ ] `NutritionInfo`, `MealHistory` ORM 모델 정의
- [ ] `NutritionLoader`의 CRUD 동작
- [ ] FastAPI 엔드포인트 6개 추가
- [ ] 단위 테스트: collector 7건 + scorer 13건
- [ ] 통합 테스트: 수집 → 매핑 → 기록 → 진단 전체 흐름
- [ ] 전체 테스트 통과 (`pytest tests/ -v`)

---

## 부록: 소주제 1·2·3 통합 시점

소주제 3까지 완성되면, 통합 추천 엔진의 3개 축이 모두 갖춰집니다.

```
engine/recommender.py의 CompositeScorer를 업데이트해줘.

이제 3개 축의 점수를 모두 사용할 수 있어:
- distance_score: 소주제 1에서 산출
- weather_score: 소주제 2에서 산출
- nutrition_score: 소주제 3에서 산출
- team_score: 소주제 4에서 구현 예정 (기본값 0)

composite = (distance * 0.3) + (weather * 0.2) + (nutrition * 0.2) + (team * 0.3)

통합 테스트:
3개 점수가 모두 반영된 종합 랭킹이 올바르게 산출되는지 확인해줘.
team_score=0인 현재 상태에서도 나머지 3개 점수의 가중합이 맞는지 검증해줘.
```

---

<div align="center">

**영양까지 고려하면, 매일의 점심이 건강한 한 끼가 됩니다!**

*다음 단계: 소주제 4 — 팀 투표 & 히스토리 관리*

</div>
