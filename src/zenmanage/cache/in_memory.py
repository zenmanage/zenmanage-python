"""In-memory cache backend."""

from __future__ import annotations

import time
from typing import Optional


class InMemoryCache:
    def __init__(self) -> None:
        self._store: dict[str, tuple[float, str]] = {}

    def get(self, key: str) -> Optional[str]:
        item = self._store.get(key)
        if item is None:
            return None

        expires_at, value = item
        if expires_at <= time.time():
            self.delete(key)
            return None

        return value

    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        self._store[key] = (time.time() + ttl_seconds, value)

    def has(self, key: str) -> bool:
        return self.get(key) is not None

    def delete(self, key: str) -> None:
        self._store.pop(key, None)

    def clear(self) -> None:
        self._store.clear()
