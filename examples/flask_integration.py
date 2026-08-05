"""Flask integration example (app extension pattern)."""

from flask import Flask

from zenmanage import ConfigBuilder, Context, Zenmanage

app = Flask(__name__)
app.extensions["zenmanage"] = Zenmanage(
    ConfigBuilder.from_environment().build()
)


@app.get("/dashboard")
def dashboard() -> dict[str, bool]:
    client = app.extensions["zenmanage"]
    context = Context.single("user", "guest")
    enabled = client.flags().with_context(context).single("new-dashboard", False).is_enabled()
    return {"newDashboard": enabled}


if __name__ == "__main__":
    app.run()
