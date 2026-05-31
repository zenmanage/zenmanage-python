"""No-op cache backend."""

from __future__ import annotations

from typing import Optional


class NullCache:
    def get(self, key: str) -> Optional[str]:
        return None

    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        return None

    def has(self, key: str) -> bool:
        return False

    def delete(self, key: str) -> None:
        return None

    def clear(self) -> None:
        return None
