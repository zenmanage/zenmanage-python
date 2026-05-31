"""Top-level SDK facade."""

from __future__ import annotations

from .api_client import ApiClient
from .cache import Cache, FileSystemCache, InMemoryCache, NullCache
from .config import Config
from .errors import ConfigurationError
from .flag_manager import FlagManager
from .rule_engine import RuleEngine


class Zenmanage:
    def __init__(self, config: Config) -> None:
        cache = self._create_cache(config)

        api_client = ApiClient(
            environment_token=config.environment_token,
            api_endpoint=config.api_endpoint,
            logger=config.logger,
            enable_usage_reporting=config.enable_usage_reporting,
        )

        self._flag_manager = FlagManager(
            api_client=api_client,
            cache=cache,
            rule_engine=RuleEngine(),
            cache_ttl=config.cache_ttl,
            logger=config.logger,
        )

    def flags(self) -> FlagManager:
        return self._flag_manager

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
