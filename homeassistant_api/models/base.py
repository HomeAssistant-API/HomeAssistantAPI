"""Module for Global Base Model Configuration inheritance."""

from datetime import datetime
from typing import Annotated, Any, Union

from pydantic import BaseModel as PydanticBaseModel
from pydantic import ConfigDict, PlainSerializer
from typing_extensions import Self

from homeassistant_api.utils import JSONType

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
        extra="forbid",
        protected_namespaces=(),
    )

    # TODO: Any being accepted is not ideal. Narrow it down.
    @classmethod
    def from_json(cls, json: Union[dict[str, JSONType], Any, None]) -> Self:
        """Constructs Self model from json data"""
        return cls.model_validate(json)
