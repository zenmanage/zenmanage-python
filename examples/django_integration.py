"""Django integration example (service-style helper)."""

from zenmanage import Attribute, ConfigBuilder, Context, Zenmanage

zenmanage = Zenmanage(
    ConfigBuilder.from_environment().build()
)


def new_dashboard_enabled(user_id: str, plan: str = "free") -> bool:
    context = Context.single("user", user_id)
    context.add_attribute(Attribute.from_strings("plan", [plan]))

    return (
        zenmanage.flags()
        .with_context(context)
        .single("new-dashboard", False)
        .is_enabled()
    )


if __name__ == "__main__":
    print(new_dashboard_enabled("user-123", "pro"))
