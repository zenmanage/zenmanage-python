from zenmanage import Attribute, ConfigBuilder, Context, Zenmanage

zenmanage = Zenmanage(
    ConfigBuilder.from_environment().build()
)

org_context = Context.single("organization", "org-42", "Acme Inc")
org_context.add_attribute(Attribute.from_strings("plan", ["enterprise"]))
org_context.add_attribute(Attribute.from_strings("region", ["us-east-1"]))

enabled = (
    zenmanage.flags()
    .with_context(org_context)
    .single("enterprise-analytics", False)
    .is_enabled()
)

print(f"enterprise-analytics enabled={enabled}")
