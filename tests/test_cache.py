import json
import time

from zenmanage.cache import FileSystemCache, InMemoryCache, NullCache


def test_in_memory_cache_ttl() -> None:
    cache = InMemoryCache()
    cache.set("a", "1", 1)
    assert cache.get("a") == "1"
    assert cache.has("a")
    cache.delete("a")
    assert not cache.has("a")

    cache.set("a", "1", 1)
    cache.clear()
    assert cache.get("a") is None

    assert cache.get("missing") is None

    time.sleep(1.1)
    assert cache.get("a") is None


def test_null_cache_behavior() -> None:
    cache = NullCache()
    cache.set("a", "1", 10)
    assert cache.get("a") is None
    assert not cache.has("a")


def test_filesystem_cache_roundtrip(tmp_path) -> None:
    cache = FileSystemCache(str(tmp_path))
    cache.set("rules", "payload", 30)
    assert cache.get("rules") == "payload"
    assert cache.has("rules")

    cache.delete("rules")
    assert cache.get("rules") is None


def test_filesystem_cache_clear(tmp_path) -> None:
    cache = FileSystemCache(str(tmp_path))
    cache.set("one", "1", 30)
    cache.set("two", "2", 30)

    cache.clear()
    assert cache.get("one") is None
    assert cache.get("two") is None


def test_filesystem_cache_invalid_json_is_evicted(tmp_path) -> None:
    cache = FileSystemCache(str(tmp_path))
    path = tmp_path / "rules.json"
    path.write_text("not-json", encoding="utf-8")
    assert cache.get("rules") is None


def test_filesystem_cache_expired_entry_is_evicted(tmp_path) -> None:
    cache = FileSystemCache(str(tmp_path))
    path = tmp_path / "rules.json"
    path.write_text(json.dumps({"expires_at": 0, "value": "x"}), encoding="utf-8")
    assert cache.get("rules") is None


def test_null_cache_delete_and_clear_noop() -> None:
    cache = NullCache()
    cache.delete("x")
    cache.clear()
