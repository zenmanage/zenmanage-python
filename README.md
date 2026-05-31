# Zenmanage Python SDK

[![PyPI version](https://badge.fury.io/py/zenmanage.svg)](https://pypi.org/project/zenmanage/)
[![CI](https://github.com/zenmanage/zenmanage-python/actions/workflows/ci.yml/badge.svg)](https://github.com/zenmanage/zenmanage-python/actions/workflows/ci.yml)
[![Codacy Badge](https://app.codacy.com/project/badge/Grade/66861c5e33c04e208f9a779efedfce14)](https://app.codacy.com/gh/zenmanage/zenmanage-python/dashboard?utm_source=gh&utm_medium=referral&utm_content=&utm_campaign=Badge_grade)
[![Coverage](https://img.shields.io/badge/coverage-90%25%2B-brightgreen)](#development)

Add feature flags to your Python application in minutes. Control feature rollouts, A/B test, and manage configurations without deploying code.

## Why Zenmanage?

- Fast: rules cached locally for low-latency evaluation
- Targeted: roll out by user, organization, or custom attributes
- Safe: graceful defaults and typed accessors
- Insightful: optional usage reporting
- Testable: deterministic rollout logic and isolated rule engine

## Installation

```bash
pip install zenmanage
```

Requirements: Python 3.9+

## Key Compatibility

- Supported in Python SDK: case-sensitive server keys prefixed with `srv_`
- Not supported in Python SDK: client keys (`cli_`) and mobile keys (`mob_`) (initialization fails fast)

## Get Started in 60 Seconds

1. Get your server key (`srv_...`) from [zenmanage.com](https://zenmanage.com)
2. Initialize the SDK:

```python
from zenmanage import ConfigBuilder, Zenmanage

zenmanage = Zenmanage(
    ConfigBuilder.create()
    .with_environment_token("srv_your_server_key_here")
    .build()
)
```

3. Check a feature flag:

```python
flag = zenmanage.flags().single("new-dashboard", False)

if flag.is_enabled():
    show_new_dashboard()
else:
    show_old_dashboard()
```

## Common Use Cases

### Async Frameworks (FastAPI, Starlette, etc.)

```python
from zenmanage import AsyncZenmanage, ConfigBuilder, Context

zenmanage = AsyncZenmanage(
    ConfigBuilder.from_environment().build()
)

async def is_enabled_for_user(user_id: str) -> bool:
    context = Context.single("user", user_id)
    flag = await zenmanage.flags().with_context(context).single("new-dashboard", False)
    return flag.is_enabled()
```

Remember to close the async client on shutdown:

```python
await zenmanage.aclose()
```

### Roll Out a New Feature Gradually

```python
from zenmanage import Context

context = Context.single("user", user_id, user_name)

beta_access = (
    zenmanage.flags()
    .with_context(context)
    .single("beta-program", False)
    .is_enabled()
)

if beta_access:
    enable_beta_features()
```

### A/B Testing

```python
from zenmanage import Attribute, Context

context = Context.single("user", user.id, user.name)
context.add_attribute(Attribute.from_strings("country", [user.country]))
context.add_attribute(Attribute.from_strings("plan", [user.subscription_plan]))

variant = (
    zenmanage.flags()
    .with_context(context)
    .single("checkout-flow", "multi-page")
    .as_string()
)

if variant == "one-page":
    render_one_page_checkout()
else:
    render_multi_page_checkout()
```

### Percentage Rollouts

```python
from zenmanage import Context

context = Context.single("user", user_id)

flag = (
    zenmanage.flags()
    .with_context(context)
    .single("new-checkout-flow", False)
)

if flag.is_enabled():
    render_new_checkout()
else:
    render_classic_checkout()
```

How it works:

- Configure rollout percentage (0-100) and salt in Zenmanage
- SDK computes CRC32B bucket from `salt:contextIdentifier`
- Same user always lands in same bucket
- Increasing percentage only adds users, never removes included users

### Use Defaults Across Many Flags

```python
from zenmanage import DefaultsCollection

defaults = DefaultsCollection.from_dict(
    {
        "new-ui": True,
        "api-version": "v2",
        "max-items": 100,
    }
)

flag_manager = zenmanage.flags().with_defaults(defaults)
new_ui = flag_manager.single("new-ui").as_bool()
```

### Fetch All Flags

```python
for flag in zenmanage.flags().all():
    print(flag.key, flag.get_value())
```

## Configuration

```python
import logging

config = (
    ConfigBuilder.create()
    .with_environment_token("srv_your_server_key_here")
    .with_cache_ttl(3600)
    .with_cache_backend("memory")  # memory | filesystem | null
    .with_cache_directory(".cache/zenmanage")  # required for filesystem
    .with_usage_reporting(True)
    .with_api_endpoint("https://api.zenmanage.com")
    .with_logger(logging.getLogger("my-app"))
    .build()
)
```

You can also load from environment variables:

- `ZENMANAGE_ENVIRONMENT_TOKEN`
- `ZENMANAGE_CACHE_TTL`
- `ZENMANAGE_CACHE_BACKEND`
- `ZENMANAGE_CACHE_DIR`
- `ZENMANAGE_ENABLE_USAGE_REPORTING`
- `ZENMANAGE_API_ENDPOINT`

```python
config = ConfigBuilder.from_environment().build()
```

## Cache Backends

- `memory`: default, fastest, process-local
- `filesystem`: durable between process restarts
- `null`: disables caching

Custom cache objects are supported with `with_cache(...)` as long as they implement `get`, `set`, `has`, `delete`, and `clear`.

## Examples

See [examples/README.md](examples/README.md) for runnable examples:

- simple-flags
- ab-testing
- caching
- context-based-flags
- defaults
- percentage-rollouts
- django-integration
- flask-integration
- fastapi-async

Framework integrations: [docs/FRAMEWORK_INTEGRATIONS.md](docs/FRAMEWORK_INTEGRATIONS.md)

## License

MIT
