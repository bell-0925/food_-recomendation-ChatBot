# 🐳 Phase 4: Docker 배포 및 운영 — Claude Code 구현 가이드라인

> **목표**: Phase 1~3에서 완성한 점심 추천 챗봇을 Docker Compose로 컨테이너화하고,
> Nginx 리버스 프록시, 헬스체크, 모니터링을 포함한 프로덕션 배포 환경을 구축합니다.

---

## 📋 목차

1. [Phase 4 개요](#1-phase-4-개요)
2. [전체 인프라 아키텍처](#2-전체-인프라-아키텍처)
3. [Step 1 — Dockerfile 작성 (4개 서비스)](#3-step-1--dockerfile-작성-4개-서비스)
4. [Step 2 — Docker Compose 통합](#4-step-2--docker-compose-통합)
5. [Step 3 — Nginx 리버스 프록시](#5-step-3--nginx-리버스-프록시)
6. [Step 4 — 모델 프리로드 및 헬스체크](#6-step-4--모델-프리로드-및-헬스체크)
7. [Step 5 — 환경 분리 (dev / staging / prod)](#7-step-5--환경-분리-dev--staging--prod)
8. [Step 6 — 모니터링 및 로깅](#8-step-6--모니터링-및-로깅)
9. [Step 7 — CI/CD 파이프라인](#9-step-7--cicd-파이프라인)
10. [Step 8 — 보안 강화](#10-step-8--보안-강화)
11. [Step 9 — 운영 매뉴얼](#11-step-9--운영-매뉴얼)
12. [트러블슈팅 가이드](#12-트러블슈팅-가이드)
13. [체크리스트](#13-체크리스트)

---

## 1. Phase 4 개요

### 1.1 배포 대상 서비스

| 서비스 | 설명 | 포트 | 컨테이너명 |
|--------|------|------|-----------|
| **Ollama** | LLM 추론 서버 | 11434 | `lunch-ollama` |
| **FastAPI** | 백엔드 API + 챗봇 코어 | 8000 | `lunch-api` |
| **React** | 프론트엔드 (Nginx 서빙) | 3000 | `lunch-frontend` |
| **Nginx** | 리버스 프록시 + SSL | 80/443 | `lunch-proxy` |
| **Redis** | 응답 캐싱 (선택) | 6379 | `lunch-redis` |

### 1.2 최소 하드웨어 요구사항

| 구성 | 최소 | 권장 |
|------|------|------|
| CPU | 4코어 | 8코어+ |
| RAM | 16GB | 32GB |
| 스토리지 | 30GB | 50GB (모델 포함) |
| GPU | 없어도 가능 | NVIDIA GPU (VRAM 8GB+) |
| OS | Ubuntu 22.04+ | Ubuntu 24.04 LTS |

---

## 2. 전체 인프라 아키텍처

### Claude Code 프롬프트

```
프로젝트 루트에 배포 관련 디렉토리 구조를 생성해줘:

lunch-optimizer/
├── docker/
│   ├── api/
│   │   └── Dockerfile              # FastAPI 백엔드
│   ├── frontend/
│   │   ├── Dockerfile              # React 빌드 + Nginx 서빙
│   │   └── nginx.conf              # 프론트엔드 전용 Nginx 설정
│   ├── ollama/
│   │   ├── Dockerfile              # Ollama + 모델 프리로드
│   │   └── entrypoint.sh           # 모델 다운로드 스크립트
│   └── proxy/
│       ├── nginx.conf              # 리버스 프록시 메인 설정
│       └── ssl/                    # SSL 인증서 (gitignore)
│
├── docker-compose.yml              # 통합 Compose 파일
├── docker-compose.dev.yml          # 개발용 오버라이드
├── docker-compose.prod.yml         # 운영용 오버라이드
├── .env.docker                     # Docker 전용 환경변수
│
├── monitoring/
│   ├── prometheus/
│   │   └── prometheus.yml          # Prometheus 설정
│   └── grafana/
│       └── dashboards/
│           └── lunch-optimizer.json # Grafana 대시보드
│
├── scripts/
│   ├── deploy.sh                   # 원클릭 배포 스크립트
│   ├── backup.sh                   # DB 백업 스크립트
│   └── healthcheck.sh              # 전체 서비스 헬스체크
│
└── .github/
    └── workflows/
        └── deploy.yml              # GitHub Actions CI/CD
```

---

## 3. Step 1 — Dockerfile 작성 (4개 서비스)

### 3.1 FastAPI 백엔드 Dockerfile

```
docker/api/Dockerfile을 작성해줘.

Python 3.12 slim 기반.
멀티스테이지 빌드는 불필요 (Python은 컴파일 없으므로).

FROM python:3.12-slim

WORKDIR /app

# 시스템 의존성
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 (캐시 활용을 위해 requirements.txt 먼저 복사)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 앱 코드 복사
COPY . .

# 비root 사용자로 실행
RUN adduser --disabled-password --gecos '' appuser
USER appuser

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]

주의사항:
- .dockerignore 파일도 생성해줘 (__pycache__, .env, *.db, .git, node_modules 제외)
- requirements.txt의 버전을 모두 고정 (pip freeze 결과 사용)
- CMD에서 --workers는 CPU 코어 수의 절반으로 설정
```

### 3.2 React 프론트엔드 Dockerfile

```
docker/frontend/Dockerfile을 작성해줘.

멀티스테이지 빌드: Node.js로 빌드 → Nginx로 서빙.

# Stage 1: Build
FROM node:20-alpine AS builder
WORKDIR /app
COPY ui/react-chat/package*.json ./
RUN npm ci --production=false
COPY ui/react-chat/ ./
RUN npm run build

# Stage 2: Serve
FROM nginx:1.27-alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY docker/frontend/nginx.conf /etc/nginx/conf.d/default.conf

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -q --spider http://localhost:3000/ || exit 1

EXPOSE 3000
CMD ["nginx", "-g", "daemon off;"]

docker/frontend/nginx.conf도 작성해줘:
- listen 3000
- root /usr/share/nginx/html
- SPA 라우팅 처리 (try_files $uri $uri/ /index.html)
- 정적 파일 캐싱 (js/css: 1년, html: no-cache)
- gzip 압축 활성화
```

### 3.3 Ollama Dockerfile

```
docker/ollama/Dockerfile을 작성해줘.

공식 Ollama 이미지 기반으로 모델을 프리로드하는 커스텀 이미지.

FROM ollama/ollama:latest

# 모델 프리로드 스크립트 복사
COPY docker/ollama/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# 모델 저장 볼륨
VOLUME /root/.ollama

HEALTHCHECK --interval=30s --timeout=10s --retries=5 \
    CMD curl -f http://localhost:11434/api/tags || exit 1

EXPOSE 11434

ENTRYPOINT ["/entrypoint.sh"]

docker/ollama/entrypoint.sh도 작성해줘:

#!/bin/bash
set -e

# Ollama 서버를 백그라운드에서 시작
ollama serve &
SERVER_PID=$!

# 서버가 준비될 때까지 대기
echo "Ollama 서버 시작 대기 중..."
for i in $(seq 1 30); do
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "Ollama 서버 준비 완료!"
        break
    fi
    sleep 1
done

# 모델 다운로드 (환경변수로 지정)
MODEL=${OLLAMA_MODEL:-qwen3.5:7b}
echo "모델 다운로드 중: $MODEL"
if ! ollama list | grep -q "$MODEL"; then
    ollama pull "$MODEL"
    echo "모델 다운로드 완료: $MODEL"
else
    echo "모델 이미 존재: $MODEL"
fi

# 모델을 미리 로드 (Warm-up)
echo "모델 웜업 중..."
ollama run "$MODEL" "" > /dev/null 2>&1 || true
echo "모델 웜업 완료!"

# 서버 프로세스를 포그라운드로 전환
wait $SERVER_PID
```

---

## 4. Step 2 — Docker Compose 통합

### Claude Code 프롬프트

```
docker-compose.yml을 작성해줘.

전체 스택을 하나의 Compose 파일로 정의.
서비스 간 의존성, 네트워크, 볼륨, 환경변수를 포함.

version: '3.8'

services:
  ollama:
    build:
      context: .
      dockerfile: docker/ollama/Dockerfile
    container_name: lunch-ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    environment:
      - OLLAMA_MODEL=${OLLAMA_MODEL:-qwen3.5:7b}
      - OLLAMA_KEEP_ALIVE=-1
      - OLLAMA_NUM_PARALLEL=2
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:11434/api/tags"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 60s
    restart: unless-stopped
    networks:
      - lunch-net

  api:
    build:
      context: .
      dockerfile: docker/api/Dockerfile
    container_name: lunch-api
    ports:
      - "8000:8000"
    environment:
      - OLLAMA_HOST=http://ollama:11434
      - OLLAMA_MODEL=${OLLAMA_MODEL:-qwen3.5:7b}
      - DB_URL=sqlite:///data/lunch_optimizer.db
      - KAKAO_REST_API_KEY=${KAKAO_REST_API_KEY}
      - DATA_GO_KR_SERVICE_KEY=${DATA_GO_KR_SERVICE_KEY}
      - FOOD_SAFETY_API_KEY=${FOOD_SAFETY_API_KEY}
      - REDIS_URL=redis://redis:6379/0
    volumes:
      - api_data:/app/data
    depends_on:
      ollama:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped
    networks:
      - lunch-net

  frontend:
    build:
      context: .
      dockerfile: docker/frontend/Dockerfile
    container_name: lunch-frontend
    ports:
      - "3000:3000"
    depends_on:
      api:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost:3000/"]
      interval: 30s
      timeout: 5s
      retries: 3
    restart: unless-stopped
    networks:
      - lunch-net

  proxy:
    image: nginx:1.27-alpine
    container_name: lunch-proxy
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./docker/proxy/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./docker/proxy/ssl:/etc/nginx/ssl:ro
    depends_on:
      - api
      - frontend
    restart: unless-stopped
    networks:
      - lunch-net

  redis:
    image: redis:7-alpine
    container_name: lunch-redis
    command: >
      redis-server
      --appendonly yes
      --maxmemory 512mb
      --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3
    restart: unless-stopped
    networks:
      - lunch-net

volumes:
  ollama_data:
    driver: local
  api_data:
    driver: local
  redis_data:
    driver: local

networks:
  lunch-net:
    driver: bridge

주의:
- GPU 없는 환경에서는 deploy.resources 섹션을 제거해야 해.
  이를 위해 docker-compose.gpu.yml 오버라이드 파일을 별도로 만들어줘.
- .env.docker 파일에 모든 환경변수 기본값을 정의해줘.
- 서비스 간 통신은 컨테이너명으로 (http://ollama:11434).
```

---

## 5. Step 3 — Nginx 리버스 프록시

### Claude Code 프롬프트

```
docker/proxy/nginx.conf를 작성해줘.

Nginx 리버스 프록시 설정. 외부 접근을 단일 도메인으로 통합.

라우팅 규칙:
- /                → frontend (3000)  : React 앱
- /api/*           → api (8000)       : FastAPI 백엔드
- /api/chat/stream → api (8000)       : SSE 스트리밍 (특별 설정 필요)

핵심 설정:
1. SSE 스트리밍 지원:
   /api/chat/stream 경로에서:
   - proxy_buffering off (버퍼링 비활성화)
   - proxy_cache off
   - proxy_read_timeout 300s (LLM 응답 대기)
   - X-Accel-Buffering: no 헤더 전달
   - chunked_transfer_encoding on

2. WebSocket 지원 (Phase 2 실시간 투표용):
   /ws/* 경로에서:
   - proxy_http_version 1.1
   - Upgrade, Connection 헤더 전달

3. 보안:
   - 요청 본문 크기 제한 (client_max_body_size 10m)
   - 서버 버전 숨기기 (server_tokens off)
   - 보안 헤더 (X-Frame-Options, X-Content-Type-Options 등)

4. 성능:
   - gzip 압축 (text/html, application/json, text/css, application/javascript)
   - 정적 파일 캐싱 (1년)
   - keepalive 연결 유지

5. Rate Limiting:
   - /api/* 경로: 초당 10요청 제한
   - /api/chat/* 경로: 초당 2요청 제한 (LLM 리소스 보호)

6. IP 기반 접근 제어 (선택):
   - 내부 네트워크만 허용 (사내 서비스용)
   - allow 10.0.0.0/8; allow 172.16.0.0/12; allow 192.168.0.0/16; deny all;

SSL 설정은 주석으로 포함하되 기본은 HTTP로 작동하도록 해줘.
Let's Encrypt certbot 사용 가이드도 주석으로 안내.
```

---

## 6. Step 4 — 모델 프리로드 및 헬스체크

### Claude Code 프롬프트

```
scripts/healthcheck.sh를 작성해줘.

전체 서비스 스택의 상태를 한 번에 확인하는 스크립트.

#!/bin/bash
echo "====== Lunch Optimizer Health Check ======"
echo ""

# 색상 정의
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

check_service() {
    local name=$1
    local url=$2
    local response=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$url" 2>/dev/null)
    
    if [ "$response" = "200" ]; then
        echo -e "  ${GREEN}✅ $name${NC} — 정상 (HTTP $response)"
        return 0
    else
        echo -e "  ${RED}❌ $name${NC} — 실패 (HTTP $response)"
        return 1
    fi
}

# 1. Ollama
echo "🤖 LLM 서버"
check_service "Ollama API" "http://localhost:11434/api/tags"

# 모델 로드 상태 확인
MODELS=$(curl -s http://localhost:11434/api/tags 2>/dev/null | python3 -c "import sys,json; data=json.load(sys.stdin); [print(f'    모델: {m[\"name\"]} ({m[\"size\"]//1e9:.1f}GB)') for m in data.get('models',[])]" 2>/dev/null)
if [ -n "$MODELS" ]; then
    echo "$MODELS"
fi

echo ""

# 2. FastAPI
echo "⚙️ 백엔드 API"
check_service "FastAPI" "http://localhost:8000/api/health"

echo ""

# 3. Frontend
echo "🖥️ 프론트엔드"
check_service "React App" "http://localhost:3000"

echo ""

# 4. Redis
echo "📦 캐시"
REDIS_PONG=$(docker exec lunch-redis redis-cli ping 2>/dev/null)
if [ "$REDIS_PONG" = "PONG" ]; then
    echo -e "  ${GREEN}✅ Redis${NC} — 정상 (PONG)"
    REDIS_KEYS=$(docker exec lunch-redis redis-cli dbsize 2>/dev/null | awk '{print $2}')
    echo "    캐시 키: ${REDIS_KEYS:-0}개"
else
    echo -e "  ${RED}❌ Redis${NC} — 실패"
fi

echo ""

# 5. Nginx
echo "🌐 프록시"
check_service "Nginx Proxy" "http://localhost:80"

echo ""

# 6. 디스크 / 메모리 요약
echo "📊 리소스"
echo "  디스크: $(df -h /var/lib/docker | tail -1 | awk '{print $3 "/" $2 " (" $5 " 사용)"}')"
echo "  메모리: $(free -h | grep Mem | awk '{print $3 "/" $2}')"

echo ""
echo "====== 점검 완료 ======"

chmod +x scripts/healthcheck.sh
```

---

## 7. Step 5 — 환경 분리 (dev / staging / prod)

### Claude Code 프롬프트

```
환경별 Docker Compose 오버라이드 파일을 작성해줘.

docker-compose.dev.yml (개발용 오버라이드):
- api: 볼륨 마운트로 코드 실시간 반영 (핫 리로드)
  volumes: ["./:/app"]
  command: ["uvicorn", "api.main:app", "--reload", "--host", "0.0.0.0"]
- frontend: Vite 개발 서버 직접 실행
  build 대신 volumes + command 사용
- ollama: 경량 모델 사용 (gemma4:e2b)
- proxy: 제거 (각 서비스 직접 접근)
- redis: 제거 (캐싱 없이 테스트)

docker-compose.prod.yml (운영용 오버라이드):
- api: workers=4, 로그 레벨 warning
- ollama: 운영 모델 (qwen3.5:7b 또는 gemma4:26b)
- proxy: SSL 활성화
- 모든 서비스: restart: always
- logging 드라이버: json-file, max-size: 50m, max-file: 5

docker-compose.gpu.yml (GPU 오버라이드):
- ollama에 deploy.resources.reservations.devices 추가

.env.docker:
모든 환경변수의 기본값을 정의.

사용법:
# 개발
docker compose -f docker-compose.yml -f docker-compose.dev.yml up

# 운영 (GPU)
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.gpu.yml up -d

# 운영 (CPU only)
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

scripts/deploy.sh도 작성해줘:
환경 인자를 받아 적절한 compose 파일 조합으로 배포하는 스크립트.
./scripts/deploy.sh dev
./scripts/deploy.sh prod
./scripts/deploy.sh prod --gpu
```

---

## 8. Step 6 — 모니터링 및 로깅

### Claude Code 프롬프트

```
모니터링 스택을 추가해줘.

1. FastAPI에 Prometheus 메트릭 엔드포인트 추가:
   api/metrics.py를 생성.
   prometheus-fastapi-instrumentator 패키지 사용.
   
   측정 항목:
   - http_request_duration_seconds: API 응답 시간
   - http_requests_total: 총 요청 수 (경로별, 상태코드별)
   - chatbot_tool_calls_total: Tool 호출 수 (Tool별)
   - chatbot_tool_duration_seconds: Tool 실행 시간
   - chatbot_llm_tokens_total: LLM 사용 토큰 수
   - chatbot_sessions_active: 활성 챗봇 세션 수

2. monitoring/prometheus/prometheus.yml:
   scrape_configs:
   - api 서비스의 /metrics 엔드포인트 (15초 간격)
   - ollama의 상태 (커스텀 exporter 또는 blackbox)

3. docker-compose.monitoring.yml:
   Prometheus + Grafana 서비스 추가.
   
   prometheus:
     image: prom/prometheus:latest
     volumes:
       - ./monitoring/prometheus:/etc/prometheus
       - prometheus_data:/prometheus
     ports:
       - "9090:9090"
   
   grafana:
     image: grafana/grafana:latest
     volumes:
       - grafana_data:/var/lib/grafana
       - ./monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards
     ports:
       - "3001:3000"
     environment:
       - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD:-admin}

4. monitoring/grafana/dashboards/lunch-optimizer.json:
   Grafana 대시보드 JSON.
   
   패널 구성:
   - API 응답 시간 (P50/P95/P99) 시계열
   - Tool별 호출 빈도 파이 차트
   - LLM 토큰 사용량 시계열
   - 활성 세션 수 게이지
   - 에러율 시계열
   - Ollama 모델 메모리 사용량

requirements.txt에 추가:
- prometheus-fastapi-instrumentator==7.0.2

사용법:
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.monitoring.yml up -d
```

---

## 9. Step 7 — CI/CD 파이프라인

### Claude Code 프롬프트

```
.github/workflows/deploy.yml을 작성해줘.

GitHub Actions CI/CD 파이프라인.

트리거:
- main 브랜치 push
- PR 시 테스트만 실행

Jobs:

1. test:
   - Python 3.12 환경
   - pip install -r requirements.txt
   - ruff check . (린트)
   - pytest tests/ -v --tb=short (테스트)
   - 커버리지 리포트 생성

2. build:
   - test 성공 후 실행
   - Docker 이미지 빌드 (api, frontend)
   - Docker Hub 또는 GitHub Container Registry에 push
   - 이미지 태그: git SHA + latest

3. deploy (main push만):
   - SSH로 운영 서버 접속
   - docker compose pull
   - docker compose up -d
   - scripts/healthcheck.sh로 배포 검증
   - 실패 시 이전 이미지로 롤백

환경 시크릿:
- DOCKER_USERNAME, DOCKER_PASSWORD
- DEPLOY_HOST, DEPLOY_KEY (SSH)
- KAKAO_REST_API_KEY, DATA_GO_KR_SERVICE_KEY 등

롤백 전략:
- 이전 성공 이미지 태그를 .last-deploy에 저장
- 헬스체크 실패 시 자동 롤백
```

---

## 10. Step 8 — 보안 강화

### Claude Code 프롬프트

```
보안 관련 설정을 추가해줘.

1. API 인증 (간단한 API Key 방식):
   api/auth.py를 생성.
   - X-API-Key 헤더 검증 미들웨어
   - /api/health와 /api/docs는 인증 제외
   - 나머지 /api/* 경로는 인증 필요
   - 키는 환경변수 API_KEYS (쉼표 구분 복수 키 지원)

2. CORS 강화:
   - 운영: 특정 도메인만 허용
   - 개발: localhost 허용
   - 환경변수 ALLOWED_ORIGINS로 제어

3. Nginx 보안 헤더:
   - X-Frame-Options: DENY
   - X-Content-Type-Options: nosniff
   - X-XSS-Protection: 1; mode=block
   - Content-Security-Policy: default-src 'self'
   - Referrer-Policy: strict-origin-when-cross-origin

4. Docker 보안:
   - 모든 컨테이너 비root 사용자 실행
   - read_only: true (가능한 서비스)
   - 불필요한 capability drop
   - 네트워크 격리 (ollama는 외부 접근 불가, api만 접근)

5. 환경변수 보안:
   - .env 파일 gitignore
   - Docker Secrets 사용 가이드 (주석)
   - 민감 정보 로깅 방지

docker-compose.yml의 네트워크를 2개로 분리해줘:
- frontend-net: proxy ↔ frontend ↔ api
- backend-net: api ↔ ollama ↔ redis
ollama와 redis는 외부에서 직접 접근 불가.
```

---

## 11. Step 9 — 운영 매뉴얼

### Claude Code 프롬프트

```
scripts/deploy.sh를 완성해줘. 원클릭 배포 + 관리 스크립트.

#!/bin/bash
사용법: ./scripts/deploy.sh [command] [options]

Commands:
  up [env]         서비스 시작 (dev|prod, 기본: dev)
  down             서비스 중지
  restart [svc]    특정 서비스 재시작
  logs [svc]       로그 확인 (-f 옵션 포함)
  status           전체 서비스 상태 확인 (healthcheck.sh 호출)
  backup           DB 백업
  restore [file]   DB 복원
  update-model [m] Ollama 모델 변경
  shell [svc]      컨테이너 쉘 접속
  clean            미사용 이미지/볼륨 정리

예시:
  ./scripts/deploy.sh up prod --gpu    # GPU 운영 배포
  ./scripts/deploy.sh logs api         # API 로그 확인
  ./scripts/deploy.sh restart ollama   # Ollama만 재시작
  ./scripts/deploy.sh update-model gemma4:26b  # 모델 변경
  ./scripts/deploy.sh backup           # DB 백업
  ./scripts/deploy.sh status           # 상태 확인

각 command를 case 문으로 구현.
에러 처리 및 컬러 출력 포함.

scripts/backup.sh도 작성해줘:
- SQLite DB 파일을 날짜 포함 파일명으로 복사
- 최근 7일 백업만 유지 (자동 정리)
- 백업 경로: ./backups/
- cron 등록 예시 주석 포함
```

---

## 12. 트러블슈팅 가이드

**문제 1: Ollama 컨테이너 시작이 매우 느림 (2~5분)**

```
Ollama 컨테이너가 시작될 때 모델을 다운로드하느라 오래 걸려.
entrypoint.sh에서 모델이 이미 볼륨에 있는지 확인하는 로직을 추가해줘.
올라마 볼륨(ollama_data)이 유지되면 재시작 시 다운로드를 건너뛰어야 해.
또한 depends_on의 start_period를 120s로 늘려서
다른 서비스가 Ollama 준비를 충분히 기다리도록 해줘.
```

**문제 2: GPU 없는 서버에서 docker-compose.yml 에러**

```
deploy.resources.reservations.devices 섹션 때문에
GPU 없는 서버에서 docker compose up이 실패해.
GPU 설정을 docker-compose.gpu.yml로 분리했는데,
기본 docker-compose.yml에서 해당 섹션을 완전히 제거해줘.
GPU가 필요하면 -f docker-compose.gpu.yml을 추가하는 방식으로.
```

**문제 3: 컨테이너 간 통신에서 "Connection refused"**

```
api 컨테이너에서 http://ollama:11434로 요청하면 Connection refused가 나.
depends_on의 condition: service_healthy를 설정했는데도 안 돼.
원인:
1. Ollama 헬스체크가 통과했지만 실제로 모델 로딩이 안 끝남
2. Docker 네트워크 DNS 해석 지연

해결:
- entrypoint.sh에서 모델 프리로드 완료 후 특정 파일을 생성
- 헬스체크에서 그 파일 존재 여부도 확인
- api의 OllamaChat에 연결 재시도 로직 (최대 30초 대기)
```

**문제 4: SSE 스트리밍이 Nginx 뒤에서 안 됨**

```
Nginx를 거치면 SSE 스트리밍이 한 번에 전체가 내려와.
proxy_buffering off 설정이 제대로 안 되어 있어.
/api/chat/stream 경로에 대해 다음 설정을 확인해줘:
  proxy_buffering off;
  proxy_cache off;
  proxy_set_header X-Accel-Buffering no;
  chunked_transfer_encoding on;
  proxy_read_timeout 300s;
또한 FastAPI 응답 헤더에 X-Accel-Buffering: no를 추가해줘.
```

**문제 5: 디스크 부족으로 서비스 중단**

```
Docker 이미지와 Ollama 모델이 디스크를 너무 많이 차지해.
1. docker system prune --all --force로 미사용 리소스 정리
2. Ollama 모델을 별도 볼륨/디스크에 마운트
3. 로그 로테이션 설정 (max-size: 50m, max-file: 5)
4. 디스크 사용량 모니터링 알림 (80% 초과 시)
이 내용을 scripts/clean.sh로 만들어줘.
```

---

## 13. 체크리스트

### 구현 완료 확인

```
Phase 4의 구현 상태를 점검해줘.
아래 체크리스트 항목별로 현재 상태를 확인하고,
미완료 항목이 있으면 구현해줘.
```

**Dockerfile:**
- [ ] `docker/api/Dockerfile` — Python 3.12, 비root 사용자, 헬스체크
- [ ] `docker/frontend/Dockerfile` — 멀티스테이지 (Node 빌드 → Nginx 서빙)
- [ ] `docker/ollama/Dockerfile` — 모델 프리로드 entrypoint
- [ ] `docker/ollama/entrypoint.sh` — 서버 대기 → 모델 다운로드 → 웜업
- [ ] `docker/frontend/nginx.conf` — SPA 라우팅, gzip, 캐싱
- [ ] `.dockerignore` — __pycache__, .env, *.db, .git, node_modules

**Docker Compose:**
- [ ] `docker-compose.yml` — 5개 서비스 (ollama, api, frontend, proxy, redis)
- [ ] 서비스 간 depends_on + condition: service_healthy
- [ ] 볼륨 3개 (ollama_data, api_data, redis_data) 정의
- [ ] 네트워크 분리 (frontend-net, backend-net)
- [ ] `docker-compose.dev.yml` — 핫 리로드, 경량 모델
- [ ] `docker-compose.prod.yml` — workers 4, restart: always, 로그 제한
- [ ] `docker-compose.gpu.yml` — GPU 리소스 예약
- [ ] `docker-compose.monitoring.yml` — Prometheus + Grafana
- [ ] `.env.docker` — 전체 환경변수 기본값

**Nginx 프록시:**
- [ ] `/` → frontend, `/api/*` → api 라우팅
- [ ] SSE 스트리밍 지원 (proxy_buffering off)
- [ ] WebSocket 지원 (/ws/*)
- [ ] Rate Limiting (API: 10req/s, Chat: 2req/s)
- [ ] 보안 헤더 (X-Frame-Options 등)
- [ ] gzip 압축
- [ ] SSL 설정 (주석 + certbot 안내)

**모니터링:**
- [ ] FastAPI Prometheus 메트릭 (/metrics)
- [ ] Tool 호출 수/시간 커스텀 메트릭
- [ ] LLM 토큰 사용량 메트릭
- [ ] `prometheus.yml` scrape 설정
- [ ] Grafana 대시보드 JSON (6개 패널)

**보안:**
- [ ] API Key 인증 미들웨어
- [ ] CORS 환경별 분리
- [ ] 비root 사용자 실행
- [ ] 네트워크 격리 (ollama 외부 접근 차단)
- [ ] .env gitignore

**CI/CD:**
- [ ] GitHub Actions: test → build → deploy
- [ ] Docker 이미지 레지스트리 push
- [ ] SSH 배포 + 헬스체크 검증
- [ ] 롤백 전략

**운영 스크립트:**
- [ ] `scripts/deploy.sh` — up/down/restart/logs/status/backup 등
- [ ] `scripts/healthcheck.sh` — 5개 서비스 상태 확인
- [ ] `scripts/backup.sh` — DB 백업 + 7일 유지
- [ ] `scripts/clean.sh` — 미사용 리소스 정리

**최종 검증:**
- [ ] `docker compose up -d` 원클릭 실행 성공
- [ ] `scripts/healthcheck.sh` 전체 서비스 정상
- [ ] 브라우저에서 http://localhost 접속 → 챗봇 UI 표시
- [ ] "오늘 뭐 먹지?" 입력 → 추천 응답 스트리밍
- [ ] `docker compose down && docker compose up -d` 재시작 후 데이터 유지

---

## 부록: 최종 프로젝트 산출물 정리

Phase 4까지 완성되면, 프로젝트의 모든 산출물이 갖춰집니다.

### 문서

| 파일 | 내용 |
|------|------|
| `README.md` | 프로젝트 개요 + 기획 + 트렌드 + 아키텍처 |
| `GUIDE_SUBTOPIC_1` | 카카오맵 API 음식점 수집 파이프라인 |
| `GUIDE_SUBTOPIC_2` | 기상청 + 에어코리아 날씨 추천 파이프라인 |
| `GUIDE_SUBTOPIC_3` | 식품안전나라 영양 분석 파이프라인 |
| `GUIDE_SUBTOPIC_4` | 팀 투표 + 통합 추천 엔진 |
| `GUIDE_CHATBOT_INTEGRATION` | Ollama 챗봇 통합 상세 계획 |
| `GUIDE_PHASE1` | Streamlit/React + Ollama 기본 챗봇 |
| `GUIDE_PHASE2` | 8개 Tool Function 연결 |
| `GUIDE_PHASE3` | 멀티턴 대화 + 개인화 고도화 |
| `GUIDE_PHASE4` | Docker 배포 + CI/CD + 모니터링 |

### 코드

| 디렉토리 | 내용 |
|---------|------|
| `pipeline/` | 4개 소주제 ETL 파이프라인 |
| `engine/` | 통합 추천 엔진 |
| `chatbot/` | 챗봇 코어 (14개 모듈) |
| `api/` | FastAPI 백엔드 (26개 엔드포인트) |
| `ui/` | Streamlit + React 프론트엔드 |
| `database/` | SQLAlchemy ORM 모델 (10개 테이블) |
| `docker/` | Dockerfile 4개 + Nginx 설정 |
| `monitoring/` | Prometheus + Grafana |
| `tests/` | 약 150건 테스트 케이스 |
| `scripts/` | 배포/백업/헬스체크 스크립트 |

---

<div align="center">

**🎉 "오늘 뭐 먹지?" 프로젝트가 완성되었습니다!**

*4개 파이프라인 · 8개 Tool · 14개 챗봇 모듈 · Docker 원클릭 배포*

*데이터 수집부터 AI 챗봇, 프로덕션 배포까지*
*하나의 주제로 풀스택 데이터 엔지니어링을 경험합니다.*

```bash
# 이 한 줄이면 전부 시작됩니다
./scripts/deploy.sh up prod
```

</div>
