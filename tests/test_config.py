
import pytest

from zenmanage import ConfigBuilder
from zenmanage.errors import ConfigurationError


def test_config_builder_requires_token() -> None:
    with pytest.raises(ConfigurationError):
        ConfigBuilder.create().build()


def test_config_builder_rejects_non_server_key() -> None:
    with pytest.raises(ConfigurationError):
        ConfigBuilder.create().with_environment_token("cli_abc").build()


def test_config_builder_accepts_server_key() -> None:
    config = ConfigBuilder.create().with_environment_token("srv_abc").build()
    assert config.environment_token == "srv_abc"


def test_config_builder_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ZENMANAGE_ENVIRONMENT_TOKEN", "srv_env")
    monkeypatch.setenv("ZENMANAGE_CACHE_TTL", "120")
    monkeypatch.setenv("ZENMANAGE_ENABLE_USAGE_REPORTING", "false")

    config = ConfigBuilder.from_environment().build()
    assert config.cache_ttl == 120
    assert not config.enable_usage_reporting


def test_filesystem_cache_requires_directory() -> None:
    with pytest.raises(ConfigurationError):
        ConfigBuilder.create().with_environment_token("srv_abc").with_cache_backend("filesystem").build()


def test_invalid_mobile_key_rejected() -> None:
    with pytest.raises(ConfigurationError):
        ConfigBuilder.create().with_environment_token("mob_abc").build()


def test_invalid_unknown_key_rejected() -> None:
    with pytest.raises(ConfigurationError):
        ConfigBuilder.create().with_environment_token("abc").build()


def test_negative_ttl_rejected() -> None:
    with pytest.raises(ConfigurationError):
        ConfigBuilder.create().with_environment_token("srv_abc").with_cache_ttl(-1).build()


def test_from_environment_with_full_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ZENMANAGE_ENVIRONMENT_TOKEN", "srv_env")
    monkeypatch.setenv("ZENMANAGE_CACHE_TTL", "60")
    monkeypatch.setenv("ZENMANAGE_CACHE_BACKEND", "filesystem")
    monkeypatch.setenv("ZENMANAGE_CACHE_DIR", "/tmp/zen-cache")
    monkeypatch.setenv("ZENMANAGE_ENABLE_USAGE_REPORTING", "true")
    monkeypatch.setenv("ZENMANAGE_API_ENDPOINT", "https://api.example.com")

    config = ConfigBuilder.from_environment().build()
    assert config.cache_backend == "filesystem"
    assert config.cache_directory == "/tmp/zen-cache"
    assert config.enable_usage_reporting is True
    assert config.api_endpoint == "https://api.example.com"
