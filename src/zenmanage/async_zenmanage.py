"""Top-level async SDK facade."""

from __future__ import annotations

from .async_api_client import AsyncApiClient
from .async_flag_manager import AsyncFlagManager
from .cache import Cache, FileSystemCache, InMemoryCache, NullCache
from .config import Config
from .errors import ConfigurationError
from .rule_engine import RuleEngine


class AsyncZenmanage:
    def __init__(self, config: Config) -> None:
        cache = self._create_cache(config)

        api_client = AsyncApiClient(
            environment_token=config.environment_token,
            api_endpoint=config.api_endpoint,
            logger=config.logger,
            enable_usage_reporting=config.enable_usage_reporting,
        )

        self._api_client = api_client
        self._flag_manager = AsyncFlagManager(
            api_client=api_client,
            cache=cache,
            rule_engine=RuleEngine(),
            cache_ttl=config.cache_ttl,
            logger=config.logger,
        )

    def flags(self) -> AsyncFlagManager:
        return self._flag_manager

    async def aclose(self) -> None:
        await self._api_client.aclose()

    def _create_cache(self, config: Config) -> Cache:
        if config.custom_cache is not None:
            return config.custom_cache

        if config.cache_backend == "filesystem":
            if not config.cache_directory:
                raise ConfigurationError("Cache directory is required for filesystem cache")
            return FileSystemCache(config.cache_directory)
        if config.cache_backend == "memory":
            return InMemoryCache()
        if config.cache_backend == "null":
            return NullCache()

        raise ConfigurationError(f"Invalid cache backend: {config.cache_backend}")
