from zenmanage import ConfigBuilder, DefaultsCollection, Zenmanage

zenmanage = Zenmanage(
    ConfigBuilder.from_environment().build()
)

defaults = DefaultsCollection.from_dict(
    {
        "new-ui": True,
        "api-version": "v2",
        "max-items": 100,
    }
)

flags = zenmanage.flags().with_defaults(defaults)

print(flags.single("new-ui").as_bool())
print(flags.single("api-version").as_string())
print(flags.single("max-items").as_number())
