"""Rule engine used to evaluate flag rules against a context."""

from __future__ import annotations

from typing import Callable, Optional, cast

from .context import Context
from .types import RuleCondition, RuleContextTarget, RuleData


class RuleEngine:
    def evaluate(self, rules: list[RuleData], context: Context) -> Optional[RuleData]:
        for rule in rules:
            if self._evaluate_rule(rule, context):
                return rule
        return None

    def _evaluate_rule(self, rule: RuleData, context: Context) -> bool:
        clauses = rule.get("clauses")
        if clauses:
            return all(self._evaluate_clause(clause, context) for clause in clauses)

        criteria = rule.get("criteria")
        if criteria:
            return self._evaluate_clause(criteria, context)

        return True

    def _evaluate_clause(self, clause: RuleCondition, context: Context) -> bool:
        selector = clause.get("selector")
        if selector == "attribute":
            # New API format: selector_subtype holds the actual attribute name
            attribute_name: Optional[str] = clause.get("selector_subtype") or ""
        elif selector is not None:
            attribute_name = selector
        else:
            # Legacy format used in unit tests: attribute holds the name directly
            attribute_name = clause.get("attribute")
        operator = clause.get("comparer") or clause.get("operator")
        clause_value = clause.get("values") if "values" in clause else clause.get("value")

        if not attribute_name or not operator:
            return False

        if attribute_name in {"context", "segment"}:
            values = self._context_values(clause_value, context)
            if not values:
                return False
            return self._evaluate_operator([context.identifier or ""], values, operator)

        attribute = context.get_attribute(attribute_name)
        if attribute is None:
            negated_ops = {
                "notequal", "notin", "notcontains", "notstartswith", "notendswith", "isnull"
            }
            if operator in negated_ops:
                return True
            return False

        values = attribute.get_values()
        if operator == "isnull":
            return not values or all(v == "" for v in values)
        if operator == "notnull":
            return any(v != "" for v in values)

        comparison = self._attribute_values(clause_value)
        if not comparison:
            return False

        return self._evaluate_operator(values, comparison, operator)

    def _context_values(
        self,
        clause_value: Optional[object],
        context: Context,
    ) -> list[str]:
        if context.identifier is None:
            return []

        targets = self._to_context_targets(clause_value)
        if not targets:
            return []

        matching = [
            target["identifier"]
            for target in targets
            if target.get("type") is None or target.get("type") == context.type
        ]
        return matching

    def _to_context_targets(
        self,
        clause_value: Optional[object],
    ) -> list[RuleContextTarget]:
        if clause_value is None:
            return []

        if isinstance(clause_value, str):
            return [{"identifier": clause_value, "type": None}]

        if isinstance(clause_value, dict):
            identifier = clause_value.get("identifier")
            if isinstance(identifier, str):
                return [{"identifier": identifier, "type": clause_value.get("type")}]
            return []

        if not isinstance(clause_value, list):
            return []

        targets: list[RuleContextTarget] = []
        for item in clause_value:
            if isinstance(item, str):
                targets.append({"identifier": item, "type": None})
            elif isinstance(item, dict):
                identifier = item.get("identifier")
                if isinstance(identifier, str):
                    targets.append({"identifier": identifier, "type": item.get("type")})
        return targets

    def _attribute_values(
        self,
        clause_value: Optional[object],
    ) -> list[str]:
        if clause_value is None:
            return []
        if isinstance(clause_value, str):
            return [clause_value]
        if isinstance(clause_value, list) and all(isinstance(item, str) for item in clause_value):
            return cast(list[str], clause_value)
        return []

    def _evaluate_operator(self, values: list[str], targets: list[str], operator: str) -> bool:
        if operator == "equal":
            return any(v == targets[0] for v in values)
        if operator == "notequal":
            return not any(v == targets[0] for v in values)
        if operator == "contains":
            return any(targets[0] in v for v in values)
        if operator == "notcontains":
            return not any(targets[0] in v for v in values)
        if operator == "in":
            return any(v in targets for v in values)
        if operator == "notin":
            return not any(v in targets for v in values)
        if operator == "startswith":
            return any(v.startswith(targets[0]) for v in values)
        if operator == "notstartswith":
            return not any(v.startswith(targets[0]) for v in values)
        if operator == "endswith":
            return any(v.endswith(targets[0]) for v in values)
        if operator == "notendswith":
            return not any(v.endswith(targets[0]) for v in values)
        if operator == "gt":
            return self._compare_numeric(values, targets[0], lambda a, b: a > b)
        if operator == "gte":
            return self._compare_numeric(values, targets[0], lambda a, b: a >= b)
        if operator == "lt":
            return self._compare_numeric(values, targets[0], lambda a, b: a < b)
        if operator == "lte":
            return self._compare_numeric(values, targets[0], lambda a, b: a <= b)
        return False

    def _compare_numeric(
        self, values: list[str], target: str, compare: Callable[[float, float], bool]
    ) -> bool:
        try:
            target_num = float(target)
        except ValueError:
            return False

        for value in values:
            try:
                value_num = float(value)
            except ValueError:
                continue
            if compare(value_num, target_num):
                return True
        return False
