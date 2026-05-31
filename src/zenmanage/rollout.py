"""Deterministic percentage rollout bucketing utilities."""

from __future__ import annotations

import zlib
from typing import Optional


def crc32b(input_text: str) -> int:
    """Return an unsigned CRC32B hash matching PHP hash('crc32b', ...)."""
    return zlib.crc32(input_text.encode("utf-8")) & 0xFFFFFFFF


def is_in_bucket(salt: str, context_identifier: Optional[str], percentage: int) -> bool:
    """Return whether a context is in the rollout bucket for the given percentage."""
    if percentage < 0 or percentage > 100:
        raise ValueError("Percentage must be between 0 and 100")

    if context_identifier is None:
        return False

    bucket = crc32b(f"{salt}:{context_identifier}") % 100
    return bucket < percentage
