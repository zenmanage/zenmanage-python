"""Typed structures used by the SDK."""

from __future__ import annotations

from typing import Literal, Optional, Protocol, TypedDict, Union

FlagType = Literal["boolean", "string", "number"]
FlagValue = Union[bool, str, int, float]


class Logger(Protocol):
    """Minimal logger protocol compatible with stdlib logging.Logger."""

    def debug(self, msg: object, *args: object, **kwargs: object) -> None: ...

    def info(self, msg: object, *args: object, **kwargs: object) -> None: ...

    def warning(self, msg: object, *args: object, **kwargs: object) -> None: ...

    def error(self, msg: object, *args: object, **kwargs: object) -> None: ...


class ContextValueData(TypedDict):
    value: str


class ContextAttributeData(TypedDict):
    key: str
    values: list[ContextValueData]


class ContextData(TypedDict, total=False):
    type: str
    name: str
    identifier: str
    attributes: list[ContextAttributeData]


class RuleContextTarget(TypedDict, total=False):
    identifier: str
    type: Optional[str]


class RuleCondition(TypedDict, total=False):
    # Legacy field names (kept for backward compatibility with unit tests)
    attribute: str
    operator: str
    value: Union[str, list[str], RuleContextTarget, list[RuleContextTarget]]
    # Current API field names
    selector: str
    selector_subtype: Optional[str]
    comparer: str
    values: Union[str, list[str], RuleContextTarget, list[RuleContextTarget]]


class ValueWrapper(TypedDict, total=False):
    boolean: bool
    string: str
    number: float


class RuleValue(TypedDict, total=False):
    version: str
    value: ValueWrapper


class RuleData(TypedDict, total=False):
    version: str
    description: str
    criteria: RuleCondition
    clauses: list[RuleCondition]
    position: int
    value: RuleValue


class TargetData(TypedDict, total=False):
    version: str
    expired_at: Optional[str]
    published_at: Optional[str]
    scheduled_at: Optional[str]
    value: RuleValue


class RolloutData(TypedDict, total=False):
    target: TargetData
    rules: list[RuleData]
    percentage: int
    salt: str
    status: str


class FlagData(TypedDict, total=False):
    version: str
    type: FlagType
    key: str
    name: str
    target: TargetData
    rules: list[RuleData]
    rollout: RolloutData


class RulesResponse(TypedDict):
    version: str
    flags: list[FlagData]
