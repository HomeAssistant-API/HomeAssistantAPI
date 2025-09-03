"""Module for Global Base Model Configuration inheritance."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel as PydanticBaseModel
from pydantic import ConfigDict, PlainSerializer

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
