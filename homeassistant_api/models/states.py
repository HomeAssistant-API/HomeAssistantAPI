"""Module for the Entity State model."""

from datetime import datetime
from datetime import timezone
from typing import Any

from pydantic import Field

from homeassistant_api.models.base import BaseModel
from homeassistant_api.models.base import DatetimeIsoField

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
    parent_id: str | None = Field(
        max_length=128,
        description="Unique string identifying the parent context.",
    )
    user_id: str | None = Field(
        max_length=128,
        description="Unique string identifying the user.",
    )


class State(BaseModel):
    """A model representing a state of an entity."""

    entity_id: str = Field(..., description="The entity_id this state corresponds to.")
    state: str = Field(
        ...,
        description="The string representation of the state of the entity.",
    )
    attributes: dict[str, Any] = Field(
        default_factory=dict,
        description="A dictionary of extra attributes of the state.",
    )
    last_changed: DatetimeIsoField = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="The last time the state was changed.",
    )
    last_updated: DatetimeIsoField | None = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="The last time the state updated.",
    )
    last_reported: DatetimeIsoField | None = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="The last time the state was reported to the server. Only used by some integrations.",
    )
    context: Context | None = Field(
        default=None,
        description="Provides information about the context of the state.",
    )
