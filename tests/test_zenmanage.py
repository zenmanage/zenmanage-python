import pytest

from zenmanage import Config, ConfigBuilder, InMemoryCache, Zenmanage
from zenmanage.errors import ConfigurationError


def test_zenmanage_builds_with_memory_cache() -> None:
    config = ConfigBuilder.create().with_environment_token("srv_test").build()
    sdk = Zenmanage(config)
    assert sdk.flags() is sdk.flags()


def test_zenmanage_supports_null_cache() -> None:
    config = (
        ConfigBuilder.create()
        .with_environment_token("srv_test")
        .with_cache_backend("null")
        .build()
    )
    sdk = Zenmanage(config)
    assert sdk.flags() is not None


def test_zenmanage_supports_filesystem_cache(tmp_path) -> None:
    config = (
        ConfigBuilder.create()
        .with_environment_token("srv_test")
        .with_cache_backend("filesystem")
        .with_cache_directory(str(tmp_path))
        .build()
    )
    sdk = Zenmanage(config)
    assert sdk.flags() is not None


def test_zenmanage_supports_custom_cache() -> None:
    config = (
        ConfigBuilder.create()
        .with_environment_token("srv_test")
        .with_cache(InMemoryCache())
        .build()
    )
    sdk = Zenmanage(config)
    assert sdk.flags() is not None


def test_zenmanage_rejects_invalid_cache_backend() -> None:
    config = (
        ConfigBuilder.create()
        .with_environment_token("srv_test")
        .with_cache_backend("invalid")
        .build()
    )

    with pytest.raises(ConfigurationError):
        Zenmanage(config)


def test_zenmanage_rejects_filesystem_without_directory_direct_config() -> None:
    config = Config(environment_token="srv_test", cache_backend="filesystem", cache_directory=None)
    with pytest.raises(ConfigurationError):
        Zenmanage(config)
