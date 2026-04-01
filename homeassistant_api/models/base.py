"""Module for Global Base Model Configuration inheritance."""

from datetime import datetime
from typing import Annotated
from typing import Any

from pydantic import BaseModel as PydanticBaseModel
from pydantic import ConfigDict
from pydantic import PlainSerializer
from typing_extensions import Self

__all__ = (
    "BaseModel",
    "DatetimeIsoField",
)

DatetimeIsoField = Annotated[
    datetime,
    PlainSerializer(lambda x: x.isoformat(), return_type=str, when_used="json"),
]


class BaseModel(PydanticBaseModel):
    """Base model that all Library Models inherit from."""

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True,
        protected_namespaces=(),
        populate_by_name=True,
        serialize_by_alias=True,
    )

    # TODO: Any being accepted is not ideal. Narrow it down.
    @classmethod
    def from_json(cls, json: dict[str, Any] | Any | None) -> Self:
        """Constructs Self model from json data"""
        return cls.model_validate(json)
