"""Filesystem cache backend for long-running services."""

from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path
from typing import Optional


class FileSystemCache:
    def __init__(self, directory: str) -> None:
        self._directory = Path(directory)
        self._directory.mkdir(parents=True, exist_ok=True)

    def _path_for(self, key: str) -> Path:
        safe_key = key.replace("/", "_").replace("..", "_")
        return self._directory / f"{safe_key}.json"

    def get(self, key: str) -> Optional[str]:
        path = self._path_for(key)
        if not path.exists():
            return None

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            self.delete(key)
            return None

        expires_at = payload.get("expires_at")
        if not isinstance(expires_at, (int, float)) or expires_at <= time.time():
            self.delete(key)
            return None

        value = payload.get("value")
        return value if isinstance(value, str) else None

    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        path = self._path_for(key)
        payload = {
            "expires_at": time.time() + ttl_seconds,
            "value": value,
        }

        fd, temp_path = tempfile.mkstemp(prefix="zenmanage-", suffix=".tmp", dir=self._directory)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle)
            Path(temp_path).replace(path)
        finally:
            if Path(temp_path).exists():
                Path(temp_path).unlink(missing_ok=True)

    def has(self, key: str) -> bool:
        return self.get(key) is not None

    def delete(self, key: str) -> None:
        self._path_for(key).unlink(missing_ok=True)

    def clear(self) -> None:
        for file in self._directory.glob("*.json"):
            file.unlink(missing_ok=True)
