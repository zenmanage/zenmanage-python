from zenmanage import Flag

BOOL_FLAG = Flag(
    version="1",
    type="boolean",
    key="feature",
    name="Feature",
    target={"value": {"value": {"boolean": True}}},
    rules=[],
)


STRING_FLAG = Flag(
    version="1",
    type="string",
    key="checkout-flow",
    name="Checkout",
    target={"value": {"value": {"string": "one-page"}}},
    rules=[],
)


NUMBER_FLAG = Flag(
    version="1",
    type="number",
    key="timeout",
    name="Timeout",
    target={"value": {"value": {"number": 42}}},
    rules=[],
)


def test_flag_accessors() -> None:
    assert BOOL_FLAG.is_enabled()
    assert BOOL_FLAG.as_bool() is True

    assert STRING_FLAG.as_string() == "one-page"
    assert STRING_FLAG.as_number() == 0.0

    assert NUMBER_FLAG.as_number() == 42.0
    assert NUMBER_FLAG.as_string() == "42"


def test_flag_roundtrip() -> None:
    payload = STRING_FLAG.to_dict()
    hydrated = Flag.from_dict(payload)
    assert hydrated.key == STRING_FLAG.key
    assert hydrated.as_string() == "one-page"


def test_flag_bool_and_number_cross_casts() -> None:
    numeric = Flag(
        version="1",
        type="number",
        key="n",
        name="n",
        target={"value": {"value": {"number": 0}}},
        rules=[],
    )
    assert numeric.as_bool() is False

    as_bool_string = Flag(
        version="1",
        type="string",
        key="s",
        name="s",
        target={"value": {"value": {"string": ""}}},
        rules=[],
    )
    assert as_bool_string.as_bool() is False


def test_flag_number_fallback_branches() -> None:
    bool_payload = Flag(
        version="1",
        type="boolean",
        key="b",
        name="b",
        target={"value": {"value": {"boolean": True}}},
        rules=[],
    )
    assert bool_payload.as_number() == 1.0

    invalid_string = Flag(
        version="1",
        type="string",
        key="s",
        name="s",
        target={"value": {"value": {"string": "not-a-number"}}},
        rules=[],
    )
    assert invalid_string.as_number() == 0.0


def test_flag_get_value_unknown_shape_fallback() -> None:
    odd = Flag(
        version="1",
        type="string",
        key="odd",
        name="odd",
        target={"value": {"value": {"other": "x"}}},
        rules=[],
    )
    assert odd.get_value() == "x"


def test_is_enabled_false_for_non_boolean() -> None:
    assert not STRING_FLAG.is_enabled()


def test_as_string_from_boolean_and_number() -> None:
    assert BOOL_FLAG.as_string() == "True"
    assert NUMBER_FLAG.as_string() == "42"


def test_as_number_from_first_fallback_variants() -> None:
    bool_first = Flag(
        version="1",
        type="string",
        key="x",
        name="x",
        target={"value": {"value": {"other": True}}},
        rules=[],
    )
    assert bool_first.as_number() == 1.0

    str_first = Flag(
        version="1",
        type="string",
        key="x",
        name="x",
        target={"value": {"value": {"other": "7.5"}}},
        rules=[],
    )
    assert str_first.as_number() == 7.5

    none_first = Flag(
        version="1",
        type="string",
        key="x",
        name="x",
        target={"value": {"value": {}}},
        rules=[],
    )
    assert none_first.as_number() == 0.0


def test_get_value_prefers_typed_values() -> None:
    assert BOOL_FLAG.get_value() is True
    assert STRING_FLAG.get_value() == "one-page"
    assert NUMBER_FLAG.get_value() == 42


def test_to_dict_includes_rollout_when_present() -> None:
    rollout_flag = Flag(
        version="1",
        type="boolean",
        key="feature",
        name="Feature",
        target={"value": {"value": {"boolean": False}}},
        rules=[],
        rollout={
            "target": {"value": {"value": {"boolean": True}}},
            "rules": [],
            "percentage": 100,
            "salt": "salt",
            "status": "active",
        },
    )
    assert "rollout" in rollout_flag.to_dict()
