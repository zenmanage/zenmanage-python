"""Main feature flag manager for loading, caching, and evaluating flags."""

from __future__ import annotations

from typing import Optional

from .api_client import ApiClient
from .cache import Cache
from .context import Context
from .errors import EvaluationError, FetchRulesError, InvalidRulesError
from .flag import Flag
from .flag_manager_base import BaseFlagManager
from .rule_engine import RuleEngine
from .types import KNOWN_FLAG_TYPES, FlagValue, Logger


class FlagManager(BaseFlagManager):
    def __init__(
        self,
        api_client: ApiClient,
        cache: Cache,
        rule_engine: RuleEngine,
        cache_ttl: int,
        logger: Optional[Logger] = None,
    ) -> None:
        super().__init__(cache, rule_engine, cache_ttl, logger)
        self._api_client = api_client
        self._last_load_error: Optional[Exception] = None

    def all(self) -> list[Flag]:
        self._ensure_rules_loaded()
        known = self._known_type_flags(self._flags or [])
        return [self._evaluate_flag(flag) for flag in known]

    def single(self, key: str, default_value: Optional[FlagValue] = None) -> Flag:
        effective_default = self._resolve_effective_default(key, default_value)
        flags = self._load_flags_or_fall_back_to_defaults()

        for flag in flags:
            if flag.key == key:
                if flag.type not in KNOWN_FLAG_TYPES:
                    self._warn_unknown_type_once(flag.key, flag.type)
                    break
                self.report_usage(key, self._usage_context(), effective_default)
                return self._evaluate_flag(flag)

        if effective_default is not None:
            result = self._create_flag_from_default(key, effective_default)
            self.report_usage(key, self._usage_context(), effective_default)
            return result

        if self._last_load_error is not None:
            raise EvaluationError(
                f"Flag not found: {key} (rules failed to load: {self._last_load_error})"
            ) from self._last_load_error

        raise EvaluationError(f"Flag not found: {key}")

    def report_usage(
        self,
        key: str,
        context: Optional[Context] = None,
        default_value: Optional[FlagValue] = None,
    ) -> None:
        self._api_client.report_usage(key, context, default_value)

    def refresh_rules(self) -> None:
        """Reload flags from the API into this instance only.

        A manager obtained via ``with_context()``/``with_defaults()`` does
        not share flag storage with the instance it was cloned from, so
        refreshing one never affects the other.
        """
        self._load_rules_from_api()

    def _ensure_rules_loaded(self) -> None:
        if self._flags is not None:
            return

        cached_flags = self._load_cached_flags()
        if cached_flags is not None:
            self._flags = cached_flags
            return

        self._load_rules_from_api()

    def _load_flags_or_fall_back_to_defaults(self) -> list[Flag]:
        """Load the current flag set, falling back to an empty list (so callers
        fall through to their own default handling) if rule-loading fails
        outright, e.g. an invalid or unreachable environment key.
        """
        try:
            self._ensure_rules_loaded()
        except (FetchRulesError, InvalidRulesError) as error:
            self._last_load_error = error
            if self._logger is not None:
                self._logger.warning(
                    "Failed to load rules, falling back to configured defaults: %s",
                    error,
                )
            return []

        self._last_load_error = None
        return self._flags or []

    def _load_rules_from_api(self) -> None:
        response = self._api_client.get_rules()
        self._set_flags_from_response(response)
