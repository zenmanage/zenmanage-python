"""Async feature flag manager for loading, caching, and evaluating flags."""

from __future__ import annotations

import asyncio
from typing import Optional

from .async_api_client import AsyncApiClient
from .cache import Cache
from .context import Context
from .errors import EvaluationError
from .flag import Flag
from .flag_manager_base import BaseFlagManager
from .rule_engine import RuleEngine
from .types import KNOWN_FLAG_TYPES, FlagValue, Logger


class AsyncFlagManager(BaseFlagManager):
    def __init__(
        self,
        api_client: AsyncApiClient,
        cache: Cache,
        rule_engine: RuleEngine,
        cache_ttl: int,
        logger: Optional[Logger] = None,
    ) -> None:
        super().__init__(cache, rule_engine, cache_ttl, logger)
        self._api_client = api_client
        self._load_lock = asyncio.Lock()

    async def all(self) -> list[Flag]:
        await self._ensure_rules_loaded()
        known = self._known_type_flags(self._flags or [])
        return [self._evaluate_flag(flag) for flag in known]

    async def single(self, key: str, default_value: Optional[FlagValue] = None) -> Flag:
        await self._ensure_rules_loaded()
        effective_default = self._resolve_effective_default(key, default_value)

        for flag in self._flags or []:
            if flag.key == key:
                if flag.type not in KNOWN_FLAG_TYPES:
                    self._warn_unknown_type_once(flag.key, flag.type)
                    break
                await self.report_usage(key, self._usage_context(), effective_default)
                return self._evaluate_flag(flag)

        if effective_default is not None:
            result = self._create_flag_from_default(key, effective_default)
            await self.report_usage(key, self._usage_context(), effective_default)
            return result

        raise EvaluationError(f"Flag not found: {key}")

    async def report_usage(
        self,
        key: str,
        context: Optional[Context] = None,
        default_value: Optional[FlagValue] = None,
    ) -> None:
        await self._api_client.report_usage(key, context, default_value)

    async def refresh_rules(self) -> None:
        """Reload flags from the API into this instance only.

        A manager obtained via ``with_context()``/``with_defaults()`` does
        not share flag storage with the instance it was cloned from, so
        refreshing one never affects the other.
        """
        async with self._load_lock:
            await self._load_rules_from_api()

    async def _ensure_rules_loaded(self) -> None:
        if self._flags is not None:
            return

        async with self._load_lock:
            if self._flags is not None:
                return

            cached_flags = self._load_cached_flags()
            if cached_flags is not None:
                self._flags = cached_flags
                return

            await self._load_rules_from_api()

    async def _load_rules_from_api(self) -> None:
        response = await self._api_client.get_rules()
        self._set_flags_from_response(response)
