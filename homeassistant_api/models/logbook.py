"""Module for the Logbook Entry model."""

from typing import Optional

from pydantic import Field

from .base import BaseModel, DatetimeIsoField


class LogbookEntry(BaseModel):
    """Model representing entries in the Logbook."""

    when: DatetimeIsoField = Field(..., description="When the entry was logged.")
    name: str = Field(..., description="The name of the entry.")
    message: Optional[str] = Field(None, description="Optional message for the entry.")
    entity_id: Optional[str] = Field(None, description="Optional relevant entity_id.")
    state: Optional[str] = Field(
        None, description="The new state information of the entity_id."
    )
    domain: Optional[str] = Field(None, description="When the entry was logged.")
    context_id: Optional[str] = Field(
        None, description="Optional relevant context instead of an entity."
    )
    icon: Optional[str] = Field(
        None, description="An MDI icon associated with the entity_id."
    )
