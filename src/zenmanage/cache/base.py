"""Cache protocol for pluggable rules caching backends."""

from __future__ import annotations

from typing import Optional, Protocol


class Cache(Protocol):
    def get(self, key: str) -> Optional[str]: ...

    def set(self, key: str, value: str, ttl_seconds: int) -> None: ...

    def has(self, key: str) -> bool: ...

    def delete(self, key: str) -> None: ...

    def clear(self) -> None: ...
