from zenmanage import DefaultsCollection


def test_defaults_collection_crud() -> None:
    defaults = DefaultsCollection.from_dict({"a": True, "b": "v2"})

    assert defaults.has("a")
    assert defaults.get("b") == "v2"
    assert set(defaults.keys()) == {"a", "b"}
    assert defaults.size() == 2

    assert defaults.delete("a")
    assert not defaults.has("a")

    defaults.clear()
    assert defaults.size() == 0
