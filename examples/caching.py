from pathlib import Path

from zenmanage import ConfigBuilder, Zenmanage

cache_dir = Path(".cache/zenmanage")
cache_dir.mkdir(parents=True, exist_ok=True)

zenmanage = Zenmanage(
    ConfigBuilder.from_environment()
    .with_cache_backend("filesystem")
    .with_cache_directory(str(cache_dir))
    .with_cache_ttl(3600)
    .build()
)

flag = zenmanage.flags().single("new-dashboard", False)
print(f"new-dashboard enabled={flag.is_enabled()}")
