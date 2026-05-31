"""Context objects used for flag evaluation and usage reporting."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .types import ContextAttributeData, ContextData, ContextValueData


@dataclass(frozen=True)
class Value:
    value: str

    def to_dict(self) -> ContextValueData:
        return {"value": self.value}


@dataclass
class Attribute:
    key: str
    values: list[Value] = field(default_factory=list)

    @classmethod
    def from_strings(cls, key: str, values: Optional[list[str]] = None) -> "Attribute":
        return cls(key=key, values=[Value(v) for v in (values or [])])

    def add_value(self, value: str) -> "Attribute":
        self.values.append(Value(value))
        return self

    def get_values(self) -> list[str]:
        return [item.value for item in self.values]

    def to_dict(self) -> ContextAttributeData:
        return {
            "key": self.key,
            "values": [value.to_dict() for value in self.values],
        }


@dataclass
class Context:
    type: str
    name: Optional[str] = None
    identifier: Optional[str] = None
    _attributes: dict[str, Attribute] = field(default_factory=dict)

    @classmethod
    def single(cls, type: str, identifier: str, name: Optional[str] = None) -> "Context":
        return cls(type=type, name=name, identifier=identifier)

    @classmethod
    def from_dict(cls, data: ContextData) -> "Context":
        context = cls(
            type=data["type"],
            name=data.get("name"),
            identifier=data.get("identifier"),
        )
        for attr in data.get("attributes", []):
            values = [v["value"] for v in attr.get("values", [])]
            context.add_attribute(Attribute.from_strings(attr["key"], values))
        return context

    def add_attribute(self, attribute: Attribute) -> "Context":
        self._attributes[attribute.key] = attribute
        return self

    def get_attribute(self, key: str) -> Optional[Attribute]:
        return self._attributes.get(key)

    def has_attribute(self, key: str) -> bool:
        return key in self._attributes

    def get_attributes(self) -> list[Attribute]:
        return list(self._attributes.values())

    def to_dict(self) -> ContextData:
        result: ContextData = {"type": self.type}
        if self.name is not None:
            result["name"] = self.name
        if self.identifier is not None:
            result["identifier"] = self.identifier

        attrs = self.get_attributes()
        if attrs:
            result["attributes"] = [attr.to_dict() for attr in attrs]

        return result
