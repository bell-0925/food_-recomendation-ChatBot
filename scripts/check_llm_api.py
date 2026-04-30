"""
LLM API 연결 확인 스크립트
- 설정된 LLM_PROVIDER에 따라 API 연결 확인
- 간단한 테스트 메시지 전송
- 응답 시간 측정
- 키가 있는 프로바이더 순서대로 테스트
"""

import os
import sys
import time
from pathlib import Path

# Windows 콘솔 UTF-8 출력
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ── env.env 로드 ──────────────────────────────────────
def load_env_file(filepath=None):
    if filepath is None:
        filepath = Path(__file__).parent.parent / "env.env"
    try:
        with open(filepath, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if value:
                        os.environ.setdefault(key, value)
    except FileNotFoundError:
        print(f"⚠️  env 파일을 찾을 수 없습니다: {filepath}")

load_env_file()

TEST_MESSAGE = "안녕, 오늘 점심 추천해줘. 한 문장으로 짧게."

# ── Gemini 테스트 ──────────────────────────────────────
def test_gemini() -> bool:
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        print("  ⏭️  GEMINI_API_KEY 없음 — 건너뜀")
        return False

    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        t0 = time.time()
        response = client.models.generate_content(
            model=os.getenv("LLM_MODEL", "gemini-2.5-flash"),
            contents=TEST_MESSAGE,
        )
        elapsed = (time.time() - t0) * 1000
        print(f"  ✅ Gemini 연결 성공  ({elapsed:.0f}ms)")
        print(f"     응답: {response.text[:80]}...")
        return True
    except Exception as e:
        print(f"  ❌ Gemini 오류: {e}")
        return False


# ── OpenAI 테스트 ──────────────────────────────────────
def test_openai() -> bool:
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        print("  ⏭️  OPENAI_API_KEY 없음 — 건너뜀")
        return False

    try:
        import openai
        client = openai.OpenAI(api_key=api_key)
        t0 = time.time()
        resp = client.chat.completions.create(
            model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            messages=[{"role": "user", "content": TEST_MESSAGE}],
            max_tokens=100,
        )
        elapsed = (time.time() - t0) * 1000
        text = resp.choices[0].message.content or ""
        print(f"  ✅ OpenAI 연결 성공  ({elapsed:.0f}ms)")
        print(f"     응답: {text[:80]}...")
        return True
    except Exception as e:
        print(f"  ❌ OpenAI 오류: {e}")
        return False


# ── Claude 테스트 ──────────────────────────────────────
def test_claude() -> bool:
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("  ⏭️  ANTHROPIC_API_KEY 없음 — 건너뜀")
        return False

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        t0 = time.time()
        msg = client.messages.create(
            model=os.getenv("LLM_MODEL", "claude-haiku-4-5-20251001"),
            max_tokens=100,
            messages=[{"role": "user", "content": TEST_MESSAGE}],
        )
        elapsed = (time.time() - t0) * 1000
        text = msg.content[0].text if msg.content else ""
        print(f"  ✅ Claude 연결 성공  ({elapsed:.0f}ms)")
        print(f"     응답: {text[:80]}...")
        return True
    except Exception as e:
        print(f"  ❌ Claude 오류: {e}")
        return False


# ── 메인 ─────────────────────────────────────────────
def main():
    print("=" * 55)
    print("  LLM API 연결 확인")
    print("=" * 55)
    provider = os.getenv("LLM_PROVIDER", "gemini").lower()
    print(f"  기본 프로바이더: {provider.upper()}")
    print(f"  테스트 메시지: \"{TEST_MESSAGE}\"")
    print()

    results = {}

    print("[ Gemini ]")
    results["gemini"] = test_gemini()
    print()

    print("[ OpenAI ]")
    results["openai"] = test_openai()
    print()

    print("[ Claude ]")
    results["claude"] = test_claude()
    print()

    print("=" * 55)
    ok = sum(v for v in results.values())
    print(f"  결과: {ok}/3 프로바이더 연결 성공")

    if results.get(provider):
        print(f"  ✅ 기본 프로바이더({provider.upper()}) 사용 가능 — 챗봇 실행 준비 완료!")
    else:
        print(f"  ⚠️  기본 프로바이더({provider.upper()}) 연결 실패.")
        print("     env.env 파일에서 API 키를 확인하거나 LLM_PROVIDER를 변경해주세요.")
    print("=" * 55)


if __name__ == "__main__":
    main()
