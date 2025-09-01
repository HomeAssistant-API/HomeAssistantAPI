"""Module for the Entity State model."""

from datetime import datetime, timezone
from typing import Optional

from pydantic import Field

from homeassistant_api.models.base import BaseModel, DatetimeIsoField
from homeassistant_api.utils import JSONType

__all__ = (
    "Context",
    "State",
)


class Context(BaseModel):
    """Model for entity state contexts."""

    id: str = Field(
        max_length=128,  # arbitrary limit
        description="Unique string identifying the context.",
    )
    parent_id: Optional[str] = Field(
        max_length=128,
        description="Unique string identifying the parent context.",
    )
    user_id: Optional[str] = Field(
        max_length=128,
        description="Unique string identifying the user.",
    )

    @classmethod
    def from_json(cls, json: dict[str, JSONType]) -> "Context":
        """Constructs Context model from json data"""
        return cls.model_validate(json)


class State(BaseModel):
    """A model representing a state of an entity."""

    entity_id: str = Field(..., description="The entity_id this state corresponds to.")
    state: str = Field(
        ..., description="The string representation of the state of the entity."
    )
    attributes: dict[str, JSONType] = Field(
        {}, description="A dictionary of extra attributes of the state."
    )
    last_changed: DatetimeIsoField = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="The last time the state was changed.",
    )
    last_updated: Optional[DatetimeIsoField] = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="The last time the state updated.",
    )
    last_reported: Optional[DatetimeIsoField] = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="The last time the state was reported to the server. Only used by some integrations.",
    )
    context: Optional[Context] = Field(
        None, description="Provides information about the context of the state."
    )

    @classmethod
    def from_json(cls, json: dict[str, JSONType]) -> "State":
        """Constructs State model from json data"""
        return cls.model_validate(json)
