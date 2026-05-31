# Framework Integrations

This guide provides practical integration patterns for Django, Flask, and async frameworks such as FastAPI.

## Django Integration

Create a singleton client in your app config or startup module.

```python
# myapp/zenmanage_client.py
from zenmanage import ConfigBuilder, Context, Zenmanage

zenmanage = Zenmanage(
    ConfigBuilder.from_environment().build()
)


def new_dashboard_enabled(user) -> bool:
    context = Context.single("user", str(user.id), user.get_full_name() or None)
    context.add_attribute(
        # Example segmentation by subscription tier
        __import__("zenmanage").Attribute.from_strings("plan", [getattr(user, "plan", "free")])
    )
    return zenmanage.flags().with_context(context).single("new-dashboard", False).is_enabled()
```

Use in views:

```python
from django.shortcuts import render
from .zenmanage_client import new_dashboard_enabled


def dashboard(request):
    if new_dashboard_enabled(request.user):
        return render(request, "dashboard_v2.html")
    return render(request, "dashboard.html")
```

## Flask Integration

Initialize once at app factory startup and store on app extensions.

```python
from flask import Flask
from zenmanage import ConfigBuilder, Context, Zenmanage


def create_app() -> Flask:
    app = Flask(__name__)

    app.extensions["zenmanage"] = Zenmanage(
        ConfigBuilder.from_environment().build()
    )

    @app.get("/dashboard")
    def dashboard():
        client = app.extensions["zenmanage"]
        context = Context.single("user", "guest")
        enabled = client.flags().with_context(context).single("new-dashboard", False).is_enabled()
        return {"newDashboard": enabled}

    return app
```

## FastAPI Integration (Async)

Use `AsyncZenmanage` and close it on app shutdown.

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from zenmanage import AsyncZenmanage, ConfigBuilder, Context


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.zenmanage = AsyncZenmanage(
        ConfigBuilder.from_environment().build()
    )
    yield
    await app.state.zenmanage.aclose()


app = FastAPI(lifespan=lifespan)


@app.get("/checkout")
async def checkout(user_id: str):
    context = Context.single("user", user_id)
    flag = await app.state.zenmanage.flags().with_context(context).single("new-checkout-flow", False)
    return {"newCheckout": flag.is_enabled()}
```

## Tips

- Build context consistently (same identifier per user) to preserve rollout determinism.
- Keep client instances singleton-per-process to maximize cache efficiency.
- Prefer defaults for critical kill-switch flags.
