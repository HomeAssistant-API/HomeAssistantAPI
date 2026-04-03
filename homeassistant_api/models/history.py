"""Module for the History model."""

from typing import Any

from pydantic import Field

from .base import BaseModel
from .states import State


class History(BaseModel):
    """Model representing past :py:class:`State`'s of an entity."""

    states: tuple[State, ...] = Field(
        ...,
        description="A tuple of previous states of an entity.",
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if not self.states:
            msg = "History requires at least one state"
            raise ValueError(msg)
        entity_ids = {state.entity_id for state in self.states}
        if len(entity_ids) != 1:
            msg = f"All states in a History must share the same entity_id, got {entity_ids}"
            raise ValueError(msg)

    @property
    def entity_id(self) -> str:
        """Returns the shared :code:`entity_id` of states."""
        return self.states[0].entity_id
