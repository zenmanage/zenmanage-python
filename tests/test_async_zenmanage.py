import pytest

from zenmanage import AsyncZenmanage, Config, ConfigBuilder, InMemoryCache
from zenmanage.errors import ConfigurationError


@pytest.mark.asyncio
async def test_async_zenmanage_builds_and_closes() -> None:
    config = ConfigBuilder.create().with_environment_token("srv_test").build()
    sdk = AsyncZenmanage(config)
    assert sdk.flags() is sdk.flags()
    await sdk.aclose()


def test_async_zenmanage_rejects_invalid_cache_backend() -> None:
    config = (
        ConfigBuilder.create()
        .with_environment_token("srv_test")
        .with_cache_backend("invalid")
        .build()
    )

    with pytest.raises(ConfigurationError):
        AsyncZenmanage(config)


def test_async_zenmanage_supports_cache_variants(tmp_path) -> None:
    memory = ConfigBuilder.create().with_environment_token("srv_test").build()
    assert AsyncZenmanage(memory).flags() is not None

    null_cache = (
        ConfigBuilder.create()
        .with_environment_token("srv_test")
        .with_cache_backend("null")
        .build()
    )
    assert AsyncZenmanage(null_cache).flags() is not None

    fs_cache = (
        ConfigBuilder.create()
        .with_environment_token("srv_test")
        .with_cache_backend("filesystem")
        .with_cache_directory(str(tmp_path))
        .build()
    )
    assert AsyncZenmanage(fs_cache).flags() is not None

    custom = (
        ConfigBuilder.create()
        .with_environment_token("srv_test")
        .with_cache(InMemoryCache())
        .build()
    )
    assert AsyncZenmanage(custom).flags() is not None


def test_async_zenmanage_rejects_filesystem_without_directory_direct_config() -> None:
    config = Config(environment_token="srv_test", cache_backend="filesystem", cache_directory=None)
    with pytest.raises(ConfigurationError):
        AsyncZenmanage(config)
