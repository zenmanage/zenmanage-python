from zenmanage import Attribute, Context
from zenmanage.rule_engine import RuleEngine


def _rule(attribute: str, operator: str, value: object, result: bool = True) -> dict:
    return {
        "clauses": [{"attribute": attribute, "operator": operator, "value": value}],
        "value": {"value": {"boolean": result}},
    }


def test_returns_first_matching_rule() -> None:
    engine = RuleEngine()
    context = Context.single("user", "u-1")
    context.add_attribute(Attribute.from_strings("country", ["US"]))

    rules = [_rule("country", "equal", "US"), _rule("country", "equal", "CA")]
    assert engine.evaluate(rules, context) == rules[0]


def test_numeric_operators() -> None:
    engine = RuleEngine()
    context = Context.single("user", "u-1")
    context.add_attribute(Attribute.from_strings("age", ["21"]))

    assert engine.evaluate([_rule("age", "gt", "18")], context) is not None
    assert engine.evaluate([_rule("age", "gte", "21")], context) is not None
    assert engine.evaluate([_rule("age", "lt", "25")], context) is not None
    assert engine.evaluate([_rule("age", "lte", "21")], context) is not None


def test_context_target_rule_matching() -> None:
    engine = RuleEngine()
    context = Context.single("organization", "org-1")

    rule = _rule(
        "context",
        "equal",
        [
            {"identifier": "org-1", "type": "organization"},
            {"identifier": "user-2", "type": "user"},
        ],
    )

    assert engine.evaluate([rule], context) is not None


def test_non_matching_rule_returns_none() -> None:
    engine = RuleEngine()
    context = Context.single("user", "u-1")
    context.add_attribute(Attribute.from_strings("plan", ["free"]))

    assert engine.evaluate([_rule("plan", "equal", "pro")], context) is None


def test_rule_without_conditions_matches() -> None:
    engine = RuleEngine()
    context = Context.single("user", "u-1")
    rule = {"value": {"value": {"boolean": True}}}
    assert engine.evaluate([rule], context) == rule


def test_criteria_mode_works() -> None:
    engine = RuleEngine()
    context = Context.single("user", "u-1")
    context.add_attribute(Attribute.from_strings("email", ["a@acme.com"]))
    rule = {
        "criteria": {"attribute": "email", "operator": "contains", "value": "@acme.com"},
        "value": {"value": {"boolean": True}},
    }
    assert engine.evaluate([rule], context) == rule


def test_all_string_operators() -> None:
    engine = RuleEngine()
    context = Context.single("user", "u-1")
    context.add_attribute(Attribute.from_strings("email", ["test@acme.com"]))
    context.add_attribute(Attribute.from_strings("country", ["US"]))

    assert engine.evaluate([_rule("email", "contains", "@acme")], context) is not None
    assert engine.evaluate([_rule("email", "contains", "@other")], context) is None
    assert engine.evaluate([_rule("email", "notcontains", "@other")], context) is not None
    assert engine.evaluate([_rule("email", "notcontains", "@acme")], context) is None
    assert engine.evaluate([_rule("country", "in", ["US", "CA"])], context) is not None
    assert engine.evaluate([_rule("country", "notin", ["FR", "DE"])], context) is not None
    assert engine.evaluate([_rule("email", "startswith", "test")], context) is not None
    assert engine.evaluate([_rule("email", "notstartswith", "admin")], context) is not None
    assert engine.evaluate([_rule("email", "notstartswith", "test")], context) is None
    assert engine.evaluate([_rule("email", "endswith", ".com")], context) is not None
    assert engine.evaluate([_rule("email", "notendswith", ".org")], context) is not None
    assert engine.evaluate([_rule("email", "notendswith", ".com")], context) is None


def test_invalid_operator_or_clause_value_returns_none() -> None:
    engine = RuleEngine()
    context = Context.single("user", "u-1")
    context.add_attribute(Attribute.from_strings("age", ["x"]))

    assert engine.evaluate([_rule("age", "unknown", "1")], context) is None
    assert engine.evaluate([_rule("age", "gt", "not-num")], context) is None


def test_clause_missing_attribute_or_operator_returns_false() -> None:
    engine = RuleEngine()
    context = Context.single("user", "u-1")
    rule = {"clauses": [{"attribute": "x"}], "value": {"value": {"boolean": True}}}
    assert engine.evaluate([rule], context) is None


def test_context_rule_fails_without_identifier() -> None:
    engine = RuleEngine()
    context = Context("user")
    rule = _rule("context", "equal", {"identifier": "u-1", "type": "user"})
    assert engine.evaluate([rule], context) is None


def test_context_target_parsing_with_malformed_values() -> None:
    engine = RuleEngine()
    context = Context.single("user", "u-1")
    malformed = _rule("context", "equal", [{"bad": "value"}, 1, None])
    assert engine.evaluate([malformed], context) is None


def test_attribute_value_rejects_non_string_list() -> None:
    engine = RuleEngine()
    context = Context.single("user", "u-1")
    context.add_attribute(Attribute.from_strings("country", ["US"]))
    rule = _rule("country", "in", [{"identifier": "x"}])
    assert engine.evaluate([rule], context) is None


def test_isnull_with_absent_attribute() -> None:
    engine = RuleEngine()
    context = Context.single("user", "u-1")
    assert engine.evaluate([_rule("tag", "isnull", None)], context) is not None


def test_isnull_with_empty_value() -> None:
    engine = RuleEngine()
    context = Context.single("user", "u-1")
    context.add_attribute(Attribute.from_strings("tag", [""]))
    assert engine.evaluate([_rule("tag", "isnull", None)], context) is not None


def test_isnull_with_nonempty_value_does_not_match() -> None:
    engine = RuleEngine()
    context = Context.single("user", "u-1")
    context.add_attribute(Attribute.from_strings("tag", ["active"]))
    assert engine.evaluate([_rule("tag", "isnull", None)], context) is None


def test_notnull_with_value_matches() -> None:
    engine = RuleEngine()
    context = Context.single("user", "u-1")
    context.add_attribute(Attribute.from_strings("tag", ["active"]))
    assert engine.evaluate([_rule("tag", "notnull", None)], context) is not None


def test_notnull_with_absent_attribute_does_not_match() -> None:
    engine = RuleEngine()
    context = Context.single("user", "u-1")
    assert engine.evaluate([_rule("tag", "notnull", None)], context) is None


def test_notequal_with_absent_attribute_matches() -> None:
    engine = RuleEngine()
    context = Context.single("user", "u-1")
    assert engine.evaluate([_rule("missing", "notequal", "x")], context) is not None


def test_negative_operators_with_absent_attribute_match() -> None:
    engine = RuleEngine()
    context = Context.single("user", "u-1")
    for op in ("notequal", "notin", "notcontains", "notstartswith", "notendswith"):
        result = engine.evaluate([_rule("missing", op, "x")], context)
        assert result is not None, f"{op} should match absent attr"
