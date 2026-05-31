from __future__ import annotations

import json

import pytest

from zenmanage.async_flag_manager import AsyncFlagManager
from zenmanage.context import Context
from zenmanage.defaults_collection import DefaultsCollection
from zenmanage.errors import EvaluationError
from zenmanage.rule_engine import RuleEngine


class StubAsyncApiClient:
    def __init__(self, flags: list[dict]) -> None:
        self.flags = flags
        self.reported: list[tuple[str, object]] = []

    async def get_rules(self) -> dict:
        return {"version": "2026-01-01", "flags": self.flags}

    async def report_usage(self, key: str, context: object = None) -> None:
        self.reported.append((key, context))


class StubCache:
    def __init__(self, cached: str | None = None) -> None:
        self.cached = cached
        self.saved: str | None = None

    def get(self, key: str) -> str | None:
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


@pytest.mark.asyncio
async def test_async_single_returns_existing_flag() -> None:
    api = StubAsyncApiClient([_base_flag()])
    manager = AsyncFlagManager(api, StubCache(), RuleEngine(), 300)

    flag = await manager.single("new-ui")
    assert flag.as_bool() is False
    assert api.reported[0][0] == "new-ui"


@pytest.mark.asyncio
async def test_async_single_missing_raises() -> None:
    manager = AsyncFlagManager(StubAsyncApiClient([]), StubCache(), RuleEngine(), 300)
    with pytest.raises(EvaluationError):
        await manager.single("missing")


@pytest.mark.asyncio
async def test_async_rollout() -> None:
    flag_data = _base_flag(
        rollout={
            "target": {"value": {"value": {"boolean": True}}},
            "rules": [],
            "percentage": 100,
            "salt": "salt",
            "status": "active",
        }
    )
    manager = AsyncFlagManager(StubAsyncApiClient([flag_data]), StubCache(), RuleEngine(), 300)
    flag = await manager.with_context(Context.single("user", "user-1")).single("new-ui")
    assert flag.as_bool() is True


@pytest.mark.asyncio
async def test_async_refresh_rules_writes_cache() -> None:
    api = StubAsyncApiClient([_base_flag()])
    cache = StubCache()
    manager = AsyncFlagManager(api, cache, RuleEngine(), 300)
    await manager.refresh_rules()
    assert cache.saved is not None


@pytest.mark.asyncio
async def test_async_all_returns_all_flags() -> None:
    api = StubAsyncApiClient([_base_flag(key="f1"), _base_flag(key="f2")])
    manager = AsyncFlagManager(api, StubCache(), RuleEngine(), 300)
    flags = await manager.all()
    assert [f.key for f in flags] == ["f1", "f2"]


@pytest.mark.asyncio
async def test_async_single_uses_inline_default_and_defaults_collection() -> None:
    manager = AsyncFlagManager(StubAsyncApiClient([]), StubCache(), RuleEngine(), 300)
    assert (await manager.single("missing", True)).as_bool() is True

    defaults = DefaultsCollection.from_dict({"welcome": "hello"})
    with_defaults = manager.with_defaults(defaults)
    assert (await with_defaults.single("welcome")).as_string() == "hello"


@pytest.mark.asyncio
async def test_async_cache_load_and_invalid_cache_fallback() -> None:
    cached = json.dumps({"version": "1", "flags": [_base_flag()]})
    manager = AsyncFlagManager(StubAsyncApiClient([]), StubCache(cached), RuleEngine(), 300)
    assert (await manager.single("new-ui")).key == "new-ui"

    fallback = AsyncFlagManager(
        StubAsyncApiClient([_base_flag()]),
        StubCache("{"),
        RuleEngine(),
        300,
    )
    assert (await fallback.single("new-ui")).key == "new-ui"


@pytest.mark.asyncio
async def test_async_usage_context_for_anonymous_and_named_context() -> None:
    api = StubAsyncApiClient([_base_flag()])
    manager = AsyncFlagManager(api, StubCache(), RuleEngine(), 300)
    await manager.single("new-ui")
    assert api.reported[-1][1] is None

    context = Context.single("user", "user-123")
    await manager.with_context(context).single("new-ui")
    assert api.reported[-1][1] is context


@pytest.mark.asyncio
async def test_async_rollout_outside_bucket_returns_fallback() -> None:
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
    manager = AsyncFlagManager(StubAsyncApiClient([flag_data]), StubCache(), RuleEngine(), 300)
    flag = await manager.with_context(Context.single("user", "u1")).single("new-ui")
    assert flag.as_string() == "fallback"
