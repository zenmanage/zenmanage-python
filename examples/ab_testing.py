from zenmanage import Attribute, ConfigBuilder, Context, Zenmanage

zenmanage = Zenmanage(
    ConfigBuilder.from_environment().build()
)

user = {
    "id": "user-123",
    "name": "Jane",
    "country": "US",
    "plan": "pro",
}

context = Context.single("user", user["id"], user["name"])
context.add_attribute(Attribute.from_strings("country", [user["country"]]))
context.add_attribute(Attribute.from_strings("plan", [user["plan"]]))

variant = (
    zenmanage.flags()
    .with_context(context)
    .single("checkout-flow", "multi-page")
    .as_string()
)

print(f"checkout-flow variant={variant}")
