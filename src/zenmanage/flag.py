"""Feature flag model and typed accessors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .types import FlagData, FlagType, FlagValue, RolloutData, RuleData, TargetData


@dataclass(frozen=True)
class Flag:
    version: str
    type: FlagType
    key: str
    name: str
    target: TargetData
    rules: list[RuleData]
    rollout: Optional[RolloutData] = None

    def is_enabled(self) -> bool:
        if self.type != "boolean":
            return False
        return self.as_bool()

    def as_bool(self) -> bool:
        value = self.target["value"]["value"]
        if "boolean" in value:
            return bool(value["boolean"])
        if "number" in value:
            return bool(value["number"])
        if "string" in value:
            return bool(value["string"])
        return bool(next(iter(value.values()), False))

    def as_string(self) -> str:
        value = self.target["value"]["value"]
        if "string" in value:
            return str(value["string"])
        if "boolean" in value:
            return str(value["boolean"])
        if "number" in value:
            return str(value["number"])
        first = next(iter(value.values()), "")
        return str(first)

    def as_number(self) -> float:
        value = self.target["value"]["value"]
        if "number" in value:
            return float(value["number"])
        if "string" in value:
            try:
                return float(value["string"])
            except (TypeError, ValueError):
                return 0.0
        if "boolean" in value:
            return 1.0 if value["boolean"] else 0.0
        first = next(iter(value.values()), None)
        if first is None:
            return 0.0
        if isinstance(first, bool):
            return 1.0 if first else 0.0
        if isinstance(first, (int, float, str)):
            try:
                return float(first)
            except (TypeError, ValueError):
                return 0.0
        return 0.0

    def get_value(self) -> FlagValue:
        value = self.target["value"]["value"]
        if "boolean" in value:
            return value["boolean"]
        if "string" in value:
            return value["string"]
        if "number" in value:
            return value["number"]
        first = next(iter(value.values()), "")
        if isinstance(first, bool):
            return first
        if isinstance(first, (int, float)):
            return first
        return str(first)

    @classmethod
    def from_dict(cls, data: FlagData) -> "Flag":
        return cls(
            version=data["version"],
            type=data["type"],
            key=data["key"],
            name=data["name"],
            target=data["target"],
            rules=data.get("rules", []),
            rollout=data.get("rollout"),
        )

    def to_dict(self) -> FlagData:
        output: FlagData = {
            "version": self.version,
            "type": self.type,
            "key": self.key,
            "name": self.name,
            "target": self.target,
            "rules": self.rules,
        }
        if self.rollout is not None:
            output["rollout"] = self.rollout
        return output
