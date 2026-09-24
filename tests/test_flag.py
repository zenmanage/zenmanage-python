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


JSON_FLAG = Flag(
    version="1",
    type="json",
    key="limits",
    name="Limits",
    target={"value": {"value": {"json": {"max": 10, "tags": ["a", "b"]}}}},
    rules=[],
)


def test_flag_accessors() -> None:
    assert BOOL_FLAG.is_enabled()
    assert BOOL_FLAG.as_bool() is True

    assert STRING_FLAG.as_string() == "one-page"
    assert STRING_FLAG.as_number() == 0.0

    assert NUMBER_FLAG.as_number() == 42.0
    assert NUMBER_FLAG.as_string() == "42"

    assert JSON_FLAG.as_json() == {"max": 10, "tags": ["a", "b"]}
    assert JSON_FLAG.get_value() == {"max": 10, "tags": ["a", "b"]}


def test_as_json_returns_list_when_decoded_value_is_a_list() -> None:
    list_flag = Flag(
        version="1",
        type="json",
        key="ids",
        name="ids",
        target={"value": {"value": {"json": [1, 2, 3]}}},
        rules=[],
    )
    assert list_flag.as_json() == [1, 2, 3]


def test_as_json_safe_zero_value_for_non_json_flags() -> None:
    assert BOOL_FLAG.as_json() == {}
    assert STRING_FLAG.as_json() == {}
    assert NUMBER_FLAG.as_json() == {}


def test_as_json_safe_zero_value_for_bare_scalar_json() -> None:
    scalar_flag = Flag(
        version="1",
        type="json",
        key="odd",
        name="odd",
        target={"value": {"value": {"json": 5}}},
        rules=[],
    )
    assert scalar_flag.as_json() == {}


def test_flag_roundtrip() -> None:
    payload = STRING_FLAG.to_dict()
    hydrated = Flag.from_dict(payload)
    assert hydrated.key == STRING_FLAG.key
    assert hydrated.as_string() == "one-page"


def test_json_flag_roundtrip() -> None:
    payload = JSON_FLAG.to_dict()
    hydrated = Flag.from_dict(payload)
    assert hydrated.key == JSON_FLAG.key
    assert hydrated.as_json() == {"max": 10, "tags": ["a", "b"]}


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
