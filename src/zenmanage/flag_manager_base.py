"""Shared non-I/O flag-evaluation logic for FlagManager and AsyncFlagManager."""

from __future__ import annotations

import copy
from typing import Optional, TypeVar

from .cache import Cache
from .context import Context
from .defaults_collection import DefaultsCollection
from .flag import Flag
from .rollout import is_in_bucket
from .rule_engine import RuleEngine
from .types import KNOWN_FLAG_TYPES, FlagType, FlagValue, Logger, TargetData, ValueWrapper

CACHE_KEY = "zenmanage_rules"

T = TypeVar("T", bound="BaseFlagManager")


class BaseFlagManager:
    """Holds the flag-lookup, type-parsing, and default-fallback logic shared by
    the sync and async flag managers. Subclasses own I/O (loading rules, reporting
    usage) and must set ``self._api_client`` themselves, since its type differs
    between the sync and async clients.
    """

    def __init__(
        self,
        cache: Cache,
        rule_engine: RuleEngine,
        cache_ttl: int,
        logger: Optional[Logger] = None,
    ) -> None:
        self._cache = cache
        self._rule_engine = rule_engine
        self._cache_ttl = cache_ttl
        self._logger = logger

        self._flags: Optional[list[Flag]] = None
        self._context = Context("anonymous")
        self._defaults = DefaultsCollection()
        self._warned_unknown_types: set[str] = set()

    def with_context(self: T, context: Context) -> T:
        clone = copy.copy(self)
        clone._context = context
        return clone

    def with_defaults(self: T, defaults: DefaultsCollection) -> T:
        clone = copy.copy(self)
        clone._defaults = defaults
        return clone

    def _resolve_effective_default(
        self, key: str, default_value: Optional[FlagValue]
    ) -> Optional[FlagValue]:
        if default_value is not None:
            return default_value
        return self._defaults.get(key) if self._defaults.has(key) else None

    def _known_type_flags(self, flags: list[Flag]) -> list[Flag]:
        known: list[Flag] = []
        for flag in flags:
            if flag.type not in KNOWN_FLAG_TYPES:
                self._warn_unknown_type_once(flag.key, flag.type)
                continue
            known.append(flag)
        return known

    def _warn_unknown_type_once(self, key: str, flag_type: str) -> None:
        if key in self._warned_unknown_types:
            return
        self._warned_unknown_types.add(key)
        if self._logger is not None:
            self._logger.warning(
                "Flag %r has unrecognized type %r; this SDK release does not know how to "
                "evaluate it and will fall back to the caller's default until it is upgraded.",
                key,
                flag_type,
            )

    def _usage_context(self) -> Optional[Context]:
        if (
            self._context.type == "anonymous"
            and self._context.name is None
            and self._context.identifier is None
            and len(self._context.get_attributes()) == 0
        ):
            return None
        return self._context

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
