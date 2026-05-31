from zenmanage import Attribute, Context, Value


def test_value_to_dict() -> None:
    assert Value("x").to_dict() == {"value": "x"}


def test_attribute_roundtrip() -> None:
    attr = Attribute.from_strings("country", ["US"]).add_value("CA")
    assert attr.get_values() == ["US", "CA"]
    assert attr.to_dict()["key"] == "country"


def test_context_serialization_roundtrip() -> None:
    context = Context.single("user", "123", "Jane")
    context.add_attribute(Attribute.from_strings("plan", ["premium"]))

    payload = context.to_dict()
    hydrated = Context.from_dict(payload)

    assert hydrated.type == "user"
    assert hydrated.identifier == "123"
    assert hydrated.get_attribute("plan") is not None
    assert hydrated.get_attribute("plan").get_values() == ["premium"]
