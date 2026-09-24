from __future__ import annotations

import asyncio
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
        self.reported: list[tuple[str, object, object]] = []

    async def get_rules(self) -> dict:
        return {"version": "2026-01-01", "flags": self.flags}

    async def report_usage(
        self, key: str, context: object = None, default_value: object = None
    ) -> None:
        self.reported.append((key, context, default_value))


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
    assert api.reported[0][2] is None


@pytest.mark.asyncio
async def test_async_single_reports_inline_default_when_flag_found() -> None:
    api = StubAsyncApiClient([_base_flag()])
    manager = AsyncFlagManager(api, StubCache(), RuleEngine(), 300)

    flag = await manager.single("new-ui", False)
    assert flag.as_bool() is False
    assert api.reported[-1] == ("new-ui", None, False)


@pytest.mark.asyncio
async def test_async_single_reports_defaults_collection_value_when_flag_found() -> None:
    api = StubAsyncApiClient([_base_flag()])
    defaults = DefaultsCollection.from_dict({"new-ui": True})
    manager = AsyncFlagManager(api, StubCache(), RuleEngine(), 300).with_defaults(defaults)

    flag = await manager.single("new-ui")
    assert flag.as_bool() is False
    assert api.reported[-1] == ("new-ui", None, True)


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


def test_with_context_and_with_defaults_return_async_flag_manager_instances() -> None:
    manager = AsyncFlagManager(StubAsyncApiClient([]), StubCache(), RuleEngine(), 300)

    assert isinstance(manager.with_context(Context.single("user", "u1")), AsyncFlagManager)
    assert isinstance(manager.with_defaults(DefaultsCollection()), AsyncFlagManager)


@pytest.mark.asyncio
async def test_concurrent_initial_loads_fetch_rules_only_once() -> None:
    """Multiple coroutines calling single()/all() before the first load completes must
    not each trigger their own fetch - only one _load_rules_from_api call should win."""

    class SlowStubAsyncApiClient(StubAsyncApiClient):
        def __init__(self, flags: list[dict]) -> None:
            super().__init__(flags)
            self.get_rules_calls = 0

        async def get_rules(self) -> dict:
            self.get_rules_calls += 1
            await asyncio.sleep(0)
            return await super().get_rules()

    api = SlowStubAsyncApiClient([_base_flag(key="f1")])
    manager = AsyncFlagManager(api, StubCache(), RuleEngine(), 300)

    first, all_flags, second = await asyncio.gather(
        manager.single("f1"), manager.all(), manager.single("f1")
    )

    assert api.get_rules_calls == 1
    assert first.key == "f1"
    assert second.key == "f1"
    assert [f.key for f in all_flags] == ["f1"]


@pytest.mark.asyncio
async def test_refresh_rules_does_not_overlap_with_concurrent_loads() -> None:
    """refresh_rules() must serialize through the same lock as the initial load, so an
    explicit refresh racing with a cold-start single()/all() never fetches in parallel."""

    class ConcurrencyTrackingStubAsyncApiClient(StubAsyncApiClient):
        def __init__(self, flags: list[dict]) -> None:
            super().__init__(flags)
            self.max_concurrent_calls = 0
            self._active_calls = 0

        async def get_rules(self) -> dict:
            self._active_calls += 1
            self.max_concurrent_calls = max(self.max_concurrent_calls, self._active_calls)
            await asyncio.sleep(0)
            try:
                return await super().get_rules()
            finally:
                self._active_calls -= 1

    api = ConcurrencyTrackingStubAsyncApiClient([_base_flag(key="f1")])
    manager = AsyncFlagManager(api, StubCache(), RuleEngine(), 300)

    await asyncio.gather(manager.single("f1"), manager.refresh_rules(), manager.refresh_rules())

    assert api.max_concurrent_calls == 1


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
    api = StubAsyncApiClient([])
    manager = AsyncFlagManager(api, StubCache(), RuleEngine(), 300)
    assert (await manager.single("missing", True)).as_bool() is True
    assert api.reported[-1] == ("missing", None, True)

    defaults = DefaultsCollection.from_dict({"welcome": "hello"})
    with_defaults = manager.with_defaults(defaults)
    assert (await with_defaults.single("welcome")).as_string() == "hello"
    assert api.reported[-1] == ("welcome", None, "hello")


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


class RecordingLogger:
    """Minimal logger stub that records warning() calls for assertions."""

    def __init__(self) -> None:
        self.warnings: list[tuple[object, ...]] = []

    def debug(self, msg: object, *args: object, **kwargs: object) -> None:
        pass

    def info(self, msg: object, *args: object, **kwargs: object) -> None:
        pass

    def warning(self, msg: object, *args: object, **kwargs: object) -> None:
        self.warnings.append((msg, *args))

    def error(self, msg: object, *args: object, **kwargs: object) -> None:
        pass


def _enum_flag(**overrides: object) -> dict:
    """A flag using a type the API may start serving before this SDK knows about it."""
    payload = {
        "version": "fla_enum",
        "type": "enum",
        "key": "enum-flag",
        "name": "enum-flag",
        "target": {"value": {"value": {"enum": "north-america"}}},
        "rules": [],
    }
    payload.update(overrides)
    return payload


def _mixed_type_payload() -> list[dict]:
    return [
        _base_flag(key="bool-flag", type="boolean", target={"value": {"value": {"boolean": True}}}),
        _base_flag(key="str-flag", type="string", target={"value": {"value": {"string": "hello"}}}),
        _base_flag(key="num-flag", type="number", target={"value": {"value": {"number": 42}}}),
        _base_flag(
            key="json-flag",
            type="json",
            target={"value": {"value": {"json": {"nested": "value", "count": 3}}}},
        ),
        _enum_flag(),
    ]


@pytest.mark.asyncio
async def test_async_single_unrecognized_flag_type_resolves_to_inline_default() -> None:
    """A rules payload with a future/unknown flag type (e.g. "enum") must not raise, and the
    unknown flag must resolve to the caller's default rather than a garbage/mis-parsed value —
    while every other flag in the same payload evaluates normally."""
    api = StubAsyncApiClient(_mixed_type_payload())
    manager = AsyncFlagManager(api, StubCache(), RuleEngine(), 300)

    assert (await manager.single("bool-flag", False)).is_enabled() is True
    assert (await manager.single("str-flag", "fallback")).as_string() == "hello"
    assert (await manager.single("num-flag", 0)).as_number() == 42.0
    assert (await manager.single("json-flag", {})).as_json() == {"nested": "value", "count": 3}

    enum_flag = await manager.single("enum-flag", "my-default")
    assert enum_flag.as_string() == "my-default"
    assert enum_flag.get_value() == "my-default"

    enum_flag_bool_default = await manager.single("enum-flag", True)
    assert enum_flag_bool_default.is_enabled() is True


@pytest.mark.asyncio
async def test_async_single_unrecognized_flag_type_resolves_to_defaults_collection() -> None:
    api = StubAsyncApiClient(_mixed_type_payload())
    defaults = DefaultsCollection.from_dict({"enum-flag": "collection-default"})
    manager = AsyncFlagManager(api, StubCache(), RuleEngine(), 300).with_defaults(defaults)

    flag = await manager.single("enum-flag")
    assert flag.as_string() == "collection-default"


@pytest.mark.asyncio
async def test_async_single_unrecognized_flag_type_raises_when_no_default() -> None:
    api = StubAsyncApiClient(_mixed_type_payload())
    manager = AsyncFlagManager(api, StubCache(), RuleEngine(), 300)

    with pytest.raises(EvaluationError):
        await manager.single("enum-flag")


@pytest.mark.asyncio
async def test_async_all_skips_unrecognized_flag_type_but_returns_the_rest() -> None:
    api = StubAsyncApiClient(_mixed_type_payload())
    manager = AsyncFlagManager(api, StubCache(), RuleEngine(), 300)

    flags = await manager.all()
    assert sorted(f.key for f in flags) == ["bool-flag", "json-flag", "num-flag", "str-flag"]


@pytest.mark.asyncio
async def test_async_single_unrecognized_flag_type_logs_once() -> None:
    logger = RecordingLogger()
    api = StubAsyncApiClient(_mixed_type_payload())
    manager = AsyncFlagManager(api, StubCache(), RuleEngine(), 300, logger=logger)

    await manager.single("enum-flag", "a")
    await manager.single("enum-flag", "b")
    await manager.all()

    assert len(logger.warnings) == 1
    assert "enum-flag" in logger.warnings[0]
    assert "enum" in logger.warnings[0]


@pytest.mark.asyncio
async def test_async_single_json_flag_evaluates_normally() -> None:
    api = StubAsyncApiClient(_mixed_type_payload())
    manager = AsyncFlagManager(api, StubCache(), RuleEngine(), 300)

    flag = await manager.single("json-flag")
    assert flag.as_json() == {"nested": "value", "count": 3}


@pytest.mark.asyncio
async def test_async_default_value_type_inference_dict_and_list() -> None:
    manager = AsyncFlagManager(StubAsyncApiClient([]), StubCache(), RuleEngine(), 300)

    dict_flag = await manager.single("d", {"a": 1})
    assert dict_flag.type == "json"
    assert dict_flag.as_json() == {"a": 1}

    list_flag = await manager.single("l", [1, 2, 3])
    assert list_flag.type == "json"
    assert list_flag.as_json() == [1, 2, 3]


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
