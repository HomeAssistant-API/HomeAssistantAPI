"""Module for the Logbook Entry model."""

from pydantic import Field

from .base import BaseModel
from .base import DatetimeIsoField


class LogbookEntry(BaseModel):
    """Model representing entries in the Logbook."""

    when: DatetimeIsoField = Field(..., description="When the entry was logged.")
    name: str = Field(..., description="The name of the entry.")
    message: str | None = Field(None, description="Optional message for the entry.")
    entity_id: str | None = Field(None, description="Optional relevant entity_id.")
    state: str | None = Field(
        None,
        description="The new state information of the entity_id.",
    )
    domain: str | None = Field(None, description="When the entry was logged.")
    context_id: str | None = Field(
        None,
        description="Optional relevant context instead of an entity.",
    )
    icon: str | None = Field(
        None,
        description="An MDI icon associated with the entity_id.",
    )
