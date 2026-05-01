"""
간단한 인메모리 TTL 캐시.
외부 의존성 없이 표준 라이브러리만 사용.
"""
import time


class TTLCache:
    """
    키-값 저장소로 동작하는 TTL(Time-To-Live) 캐시.

    Args:
        ttl_seconds: 캐시 유효 시간(초). 이 시간이 지나면 항목이 만료됨.

    Example::

        cache = TTLCache(ttl_seconds=600)
        cache.set("key", {"data": 1})

        value, hit = cache.get("key")
        if hit:
            return value          # 캐시 히트
        # ... DB 조회 후 cache.set("key", result)
    """

    def __init__(self, ttl_seconds: int) -> None:
        self._ttl = ttl_seconds
        self._store: dict[str, tuple] = {}  # key → (value, expires_at)

    def get(self, key: str) -> tuple:
        """
        Returns:
            (value, True)  — 캐시 히트 (만료되지 않은 항목)
            (None, False)  — 캐시 미스 (없거나 만료)
        """
        entry = self._store.get(key)
        if entry is None:
            return None, False
        value, expires_at = entry
        if time.monotonic() < expires_at:
            return value, True
        # 만료된 항목 제거
        del self._store[key]
        return None, False

    def set(self, key: str, value) -> None:
        """항목을 저장하고 TTL 타이머를 시작합니다."""
        self._store[key] = (value, time.monotonic() + self._ttl)

    def invalidate(self, key: str | None = None) -> None:
        """
        특정 키 또는 전체 캐시를 무효화합니다.

        Args:
            key: None이면 전체 초기화, 문자열이면 해당 키만 삭제.
        """
        if key is None:
            self._store.clear()
        else:
            self._store.pop(key, None)

    def __len__(self) -> int:
        return len(self._store)
