from __future__ import annotations

import json
from typing import Optional

import pytest

from zenmanage import Attribute, Context, DefaultsCollection
from zenmanage.errors import EvaluationError
from zenmanage.flag_manager import FlagManager
from zenmanage.rule_engine import RuleEngine


class StubApiClient:
    def __init__(self, flags: list[dict]) -> None:
        self.flags = flags
        self.reported: list[tuple[str, object]] = []

    def get_rules(self) -> dict:
        return {"version": "2026-01-01", "flags": self.flags}

    def report_usage(self, key: str, context: object = None) -> None:
        self.reported.append((key, context))


class StubCache:
    def __init__(self, cached: Optional[str] = None) -> None:
        self.cached = cached
        self.saved: Optional[str] = None

    def get(self, key: str) -> Optional[str]:
        return self.cached

    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        self.saved = value

    def has(self, key: str) -> bool:
        return self.cached is not None

    def delete(self, key: str) -> None:
        self.cached = None

    def clear(self) -> None:
        self.cached = None


def _base_flag(**overrides: object) -> dict:
    payload = {
        "version": "fla_1",
        "type": "boolean",
        "key": "new-ui",
        "name": "new-ui",
        "target": {"value": {"value": {"boolean": False}}},
        "rules": [],
    }
    payload.update(overrides)
    return payload


def test_single_returns_existing_flag() -> None:
    api = StubApiClient([_base_flag()])
    cache = StubCache()

    manager = FlagManager(api, cache, RuleEngine(), 300)
    flag = manager.single("new-ui")

    assert flag.as_bool() is False
    assert api.reported[0][0] == "new-ui"


def test_single_uses_inline_default() -> None:
    api = StubApiClient([])
    manager = FlagManager(api, StubCache(), RuleEngine(), 300)

    flag = manager.single("missing", True)
    assert flag.as_bool() is True


def test_single_uses_defaults_collection() -> None:
    api = StubApiClient([])
    defaults = DefaultsCollection.from_dict({"welcome": "hello"})
    manager = FlagManager(api, StubCache(), RuleEngine(), 300).with_defaults(defaults)

    flag = manager.single("welcome")
    assert flag.as_string() == "hello"


def test_single_missing_raises() -> None:
    manager = FlagManager(StubApiClient([]), StubCache(), RuleEngine(), 300)
    with pytest.raises(EvaluationError):
        manager.single("missing")


def test_rollout_path_evaluates_rollout_target() -> None:
    flag_data = _base_flag(
        rollout={
            "target": {"value": {"value": {"boolean": True}}},
            "rules": [],
            "percentage": 100,
            "salt": "salt",
            "status": "active",
        }
    )
    manager = FlagManager(StubApiClient([flag_data]), StubCache(), RuleEngine(), 300)
    flag = manager.with_context(Context.single("user", "user-1")).single("new-ui")
    assert flag.as_bool() is True


def test_rule_match_overrides_target_value() -> None:
    flag_data = _base_flag(
        type="string",
        target={"value": {"value": {"string": "fallback"}}},
        rules=[
            {
                "clauses": [{"attribute": "country", "operator": "equal", "value": "US"}],
                "value": {"value": {"string": "match"}},
            }
        ],
    )

    context = Context.single("user", "user-1")
    context.add_attribute(Attribute.from_strings("country", ["US"]))

    manager = FlagManager(StubApiClient([flag_data]), StubCache(), RuleEngine(), 300)
    flag = manager.with_context(context).single("new-ui")
    assert flag.as_string() == "match"


def test_loads_from_cache_before_api() -> None:
    cached = json.dumps({"version": "1", "flags": [_base_flag()]})
    api = StubApiClient([])
    manager = FlagManager(api, StubCache(cached), RuleEngine(), 300)

    flag = manager.single("new-ui")
    assert flag.key == "new-ui"


def test_refresh_rules_fetches_again() -> None:
    api = StubApiClient([_base_flag()])
    cache = StubCache()
    manager = FlagManager(api, cache, RuleEngine(), 300)

    manager.refresh_rules()
    assert cache.saved is not None


def test_all_returns_evaluated_flags() -> None:
    api = StubApiClient([_base_flag(key="f1"), _base_flag(key="f2")])
    manager = FlagManager(api, StubCache(), RuleEngine(), 300)
    flags = manager.all()
    assert [f.key for f in flags] == ["f1", "f2"]


def test_cached_invalid_json_falls_back_to_api() -> None:
    api = StubApiClient([_base_flag()])
    manager = FlagManager(api, StubCache("{"), RuleEngine(), 300)
    assert manager.single("new-ui").key == "new-ui"


def test_usage_context_included_for_non_anonymous() -> None:
    api = StubApiClient([_base_flag()])
    manager = FlagManager(api, StubCache(), RuleEngine(), 300)
    context = Context.single("user", "u1")
    manager.with_context(context).single("new-ui")
    assert api.reported[-1][1] is context


def test_rollout_outside_bucket_with_rules_returns_fallback_target() -> None:
    flag_data = _base_flag(
        type="string",
        target={"value": {"value": {"string": "fallback"}}},
        rules=[],
        rollout={
            "target": {"value": {"value": {"string": "rollout"}}},
            "rules": [],
            "percentage": 0,
            "salt": "salt",
            "status": "active",
        },
    )
    manager = FlagManager(StubApiClient([flag_data]), StubCache(), RuleEngine(), 300)
    flag = manager.with_context(Context.single("user", "u1")).single("new-ui")
    assert flag.as_string() == "fallback"


def test_default_value_type_inference() -> None:
    manager = FlagManager(StubApiClient([]), StubCache(), RuleEngine(), 300)
    assert manager.single("n", 3.14).as_number() == 3.14
    assert manager.single("s", "hello").as_string() == "hello"
