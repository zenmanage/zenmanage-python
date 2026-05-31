"""FastAPI integration example using AsyncZenmanage."""

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
async def checkout(user_id: str) -> dict[str, bool]:
    context = Context.single("user", user_id)
    flag = await (
        app.state.zenmanage.flags()
        .with_context(context)
        .single("new-checkout-flow", False)
    )
    return {"newCheckout": flag.is_enabled()}
