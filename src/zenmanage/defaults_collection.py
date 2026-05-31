"""Default flag value collection."""

from __future__ import annotations

from typing import Optional

from .types import FlagValue


class DefaultsCollection:
    """Container for optional default values when a flag key is unavailable."""

    def __init__(self) -> None:
        self._defaults: dict[str, FlagValue] = {}

    @classmethod
    def from_dict(cls, data: dict[str, FlagValue]) -> "DefaultsCollection":
        collection = cls()
        for key, value in data.items():
            collection.set(key, value)
        return collection

    def set(self, key: str, value: FlagValue) -> "DefaultsCollection":
        self._defaults[key] = value
        return self

    def get(self, key: str) -> Optional[FlagValue]:
        return self._defaults.get(key)

    def has(self, key: str) -> bool:
        return key in self._defaults

    def delete(self, key: str) -> bool:
        return self._defaults.pop(key, None) is not None

    def clear(self) -> None:
        self._defaults.clear()

    def keys(self) -> list[str]:
        return list(self._defaults.keys())

    def size(self) -> int:
        return len(self._defaults)
