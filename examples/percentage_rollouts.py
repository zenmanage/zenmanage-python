from zenmanage import ConfigBuilder, Context, Zenmanage

zenmanage = Zenmanage(
    ConfigBuilder.from_environment().build()
)

context = Context.single("user", "user-123")

flag = (
    zenmanage.flags()
    .with_context(context)
    .single("new-checkout-flow", False)
)

print(f"new-checkout-flow enabled={flag.is_enabled()}")
