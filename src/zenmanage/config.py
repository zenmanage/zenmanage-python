"""Configuration builder and immutable config model."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, Optional

from .cache import Cache
from .errors import ConfigurationError

SERVER_KEY_PREFIX = "srv_"
CLIENT_KEY_PREFIX = "cli_"
MOBILE_KEY_PREFIX = "mob_"


@dataclass(frozen=True)
class Config:
    environment_token: str
    cache_ttl: int = 3600
    cache_backend: str = "memory"
    cache_directory: Optional[str] = None
    enable_usage_reporting: bool = True
    api_endpoint: str = "https://api.zenmanage.com"
    logger: Any = logging.getLogger("zenmanage")
    custom_cache: Optional[Cache] = None


class ConfigBuilder:
    def __init__(self) -> None:
        # Empty placeholder, not a credential — build() rejects empty tokens.
        self._config = Config(environment_token="")  # nosec B106

    @classmethod
    def create(cls) -> "ConfigBuilder":
        return cls()

    @classmethod
    def from_environment(cls) -> "ConfigBuilder":
        builder = cls.create()

        token = os.getenv("ZENMANAGE_ENVIRONMENT_TOKEN")
        if token:
            builder.with_environment_token(token)

        cache_ttl = os.getenv("ZENMANAGE_CACHE_TTL")
        if cache_ttl and cache_ttl.isdigit():
            builder.with_cache_ttl(int(cache_ttl))

        cache_backend = os.getenv("ZENMANAGE_CACHE_BACKEND")
        if cache_backend in {"memory", "filesystem", "null"}:
            builder.with_cache_backend(cache_backend)

        cache_dir = os.getenv("ZENMANAGE_CACHE_DIR")
        if cache_dir:
            builder.with_cache_directory(cache_dir)

        reporting = os.getenv("ZENMANAGE_ENABLE_USAGE_REPORTING")
        if reporting is not None:
            builder.with_usage_reporting(reporting.lower() in {"1", "true", "yes", "on"})

        api_endpoint = os.getenv("ZENMANAGE_API_ENDPOINT")
        if api_endpoint:
            builder.with_api_endpoint(api_endpoint)

        return builder

    def with_environment_token(self, token: str) -> "ConfigBuilder":
        self._config = Config(**{**self._config.__dict__, "environment_token": token})
        return self

    def with_cache_ttl(self, ttl: int) -> "ConfigBuilder":
        self._config = Config(**{**self._config.__dict__, "cache_ttl": ttl})
        return self

    def with_cache_backend(self, backend: str) -> "ConfigBuilder":
        self._config = Config(**{**self._config.__dict__, "cache_backend": backend})
        return self

    def with_cache_directory(self, directory: str) -> "ConfigBuilder":
        self._config = Config(**{**self._config.__dict__, "cache_directory": directory})
        return self

    def with_usage_reporting(self, enabled: bool) -> "ConfigBuilder":
        self._config = Config(**{**self._config.__dict__, "enable_usage_reporting": enabled})
        return self

    def with_api_endpoint(self, endpoint: str) -> "ConfigBuilder":
        self._config = Config(**{**self._config.__dict__, "api_endpoint": endpoint})
        return self

    def with_cache(self, cache: Cache) -> "ConfigBuilder":
        self._config = Config(**{**self._config.__dict__, "custom_cache": cache})
        return self

    def with_logger(self, logger: Any) -> "ConfigBuilder":
        self._config = Config(**{**self._config.__dict__, "logger": logger})
        return self

    def build(self) -> Config:
        if not self._config.environment_token:
            raise ConfigurationError("Environment token is required")

        self._validate_server_key(self._config.environment_token)

        if self._config.cache_backend == "filesystem" and not (
            self._config.cache_directory or self._config.custom_cache
        ):
            raise ConfigurationError("Cache directory is required for filesystem cache")

        if self._config.cache_ttl < 0:
            raise ConfigurationError("Cache TTL must be a non-negative integer")

        return self._config

    def _validate_server_key(self, token: str) -> None:
        if token.startswith(SERVER_KEY_PREFIX):
            return
        if token.startswith(CLIENT_KEY_PREFIX):
            raise ConfigurationError(
                "Invalid environment token for Python runtime: client key provided. "
                f"Use a server key ({SERVER_KEY_PREFIX}...)."
            )
        if token.startswith(MOBILE_KEY_PREFIX):
            raise ConfigurationError(
                "Invalid environment token for Python runtime: mobile key provided. "
                f"Use a server key ({SERVER_KEY_PREFIX}...)."
            )

        raise ConfigurationError(
            "Invalid environment token format. Expected one of: "
            f"{SERVER_KEY_PREFIX}, {CLIENT_KEY_PREFIX}, or {MOBILE_KEY_PREFIX}."
        )
