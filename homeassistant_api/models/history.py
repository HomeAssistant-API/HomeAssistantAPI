"""Module for the History model."""

from typing import Tuple

from pydantic import Field

from .base import BaseModel
from .states import State


class History(BaseModel):
    """Model representing past :py:class:`State`'s of an entity."""

    states: Tuple[State, ...] = Field(
        ..., description="A tuple of previous states of an entity."
    )

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        assert self.entity_id is not None

    @property
    def entity_id(self) -> str:
        """Returns the shared :code:`entity_id` of states."""
        entity_ids = [state.entity_id for state in self.states]
        result, *_ = set(entity_ids)
        return result
