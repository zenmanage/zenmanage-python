"""Main feature flag manager for loading, caching, and evaluating flags."""

from __future__ import annotations

import copy
import json
from typing import Optional

from .api_client import ApiClient
from .cache import Cache
from .context import Context
from .defaults_collection import DefaultsCollection
from .errors import EvaluationError
from .flag import Flag
from .rollout import is_in_bucket
from .rule_engine import RuleEngine
from .types import FlagType, FlagValue, TargetData, ValueWrapper

CACHE_KEY = "zenmanage_rules"


class FlagManager:
    def __init__(
        self,
        api_client: ApiClient,
        cache: Cache,
        rule_engine: RuleEngine,
        cache_ttl: int,
        logger: Optional[object] = None,
    ) -> None:
        self._api_client = api_client
        self._cache = cache
        self._rule_engine = rule_engine
        self._cache_ttl = cache_ttl
        self._logger = logger

        self._flags: Optional[list[Flag]] = None
        self._context = Context("anonymous")
        self._defaults = DefaultsCollection()

    def all(self) -> list[Flag]:
        self._ensure_rules_loaded()
        return [self._evaluate_flag(flag) for flag in (self._flags or [])]

    def single(self, key: str, default_value: Optional[FlagValue] = None) -> Flag:
        self._ensure_rules_loaded()
        effective_default = self._resolve_effective_default(key, default_value)

        for flag in self._flags or []:
            if flag.key == key:
                self.report_usage(key, self._usage_context(), effective_default)
                return self._evaluate_flag(flag)

        if effective_default is not None:
            result = self._create_flag_from_default(key, effective_default)
            self.report_usage(key, self._usage_context(), effective_default)
            return result

        raise EvaluationError(f"Flag not found: {key}")

    def with_context(self, context: Context) -> "FlagManager":
        clone = copy.copy(self)
        clone._context = context
        return clone

    def with_defaults(self, defaults: DefaultsCollection) -> "FlagManager":
        clone = copy.copy(self)
        clone._defaults = defaults
        return clone

    def report_usage(
        self,
        key: str,
        context: Optional[Context] = None,
        default_value: Optional[FlagValue] = None,
    ) -> None:
        self._api_client.report_usage(key, context, default_value)

    def refresh_rules(self) -> None:
        self._load_rules_from_api()

    def _resolve_effective_default(
        self, key: str, default_value: Optional[FlagValue]
    ) -> Optional[FlagValue]:
        if default_value is not None:
            return default_value
        return self._defaults.get(key) if self._defaults.has(key) else None

    def _usage_context(self) -> Optional[Context]:
        if (
            self._context.type == "anonymous"
            and self._context.name is None
            and self._context.identifier is None
            and len(self._context.get_attributes()) == 0
        ):
            return None
        return self._context

    def _ensure_rules_loaded(self) -> None:
        if self._flags is not None:
            return

        cached = self._cache.get(CACHE_KEY)
        if cached is not None:
            try:
                data = json.loads(cached)
                if isinstance(data, dict) and isinstance(data.get("flags"), list):
                    self._flags = [Flag.from_dict(item) for item in data["flags"]]
                    return
            except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                pass

        self._load_rules_from_api()

    def _load_rules_from_api(self) -> None:
        response = self._api_client.get_rules()
        self._flags = [Flag.from_dict(flag_data) for flag_data in response["flags"]]
        self._cache.set(CACHE_KEY, json.dumps(response), self._cache_ttl)

    def _evaluate_flag(self, flag: Flag) -> Flag:
        rollout = flag.rollout
        target = flag.target
        rules = flag.rules

        if rollout:
            in_bucket = is_in_bucket(
                rollout.get("salt", ""),
                self._context.identifier,
                int(rollout.get("percentage", 0)),
            )
            if in_bucket:
                target = rollout["target"]
                rules = rollout.get("rules", [])

        if not rules:
            if target == flag.target and rollout is None:
                return flag
            return Flag(flag.version, flag.type, flag.key, flag.name, target, rules)

        matched_rule = self._rule_engine.evaluate(rules, self._context)
        if matched_rule is not None:
            new_target: TargetData = {"value": matched_rule["value"]}
            if "version" in target:
                new_target["version"] = target["version"]
            if "expired_at" in target:
                new_target["expired_at"] = target["expired_at"]
            if "published_at" in target:
                new_target["published_at"] = target["published_at"]
            if "scheduled_at" in target:
                new_target["scheduled_at"] = target["scheduled_at"]
            return Flag(flag.version, flag.type, flag.key, flag.name, new_target, rules)

        if target == flag.target and rollout is None:
            return flag
        return Flag(flag.version, flag.type, flag.key, flag.name, target, rules)

    def _create_flag_from_default(self, key: str, default_value: FlagValue) -> Flag:
        if isinstance(default_value, bool):
            flag_type: FlagType = "boolean"
            value_payload: ValueWrapper = {"boolean": default_value}
        elif isinstance(default_value, (int, float)):
            flag_type = "number"
            value_payload = {"number": float(default_value)}
        else:
            flag_type = "string"
            value_payload = {"string": str(default_value)}

        target: TargetData = {"value": {"value": value_payload}}
        return Flag(version="default", type=flag_type, key=key, name=key, target=target, rules=[])
