from zenmanage import ConfigBuilder, Zenmanage

zenmanage = Zenmanage(
    ConfigBuilder.from_environment().build()
)

new_dashboard = zenmanage.flags().single("new-dashboard", False).is_enabled()
print(f"new-dashboard enabled={new_dashboard}")
