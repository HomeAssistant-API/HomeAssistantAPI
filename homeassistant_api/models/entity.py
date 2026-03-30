"""Module for Entity and entity Group data models"""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional

from pydantic import Field

from .base import BaseModel
from .history import History
from .states import State

if TYPE_CHECKING:
    from homeassistant_api import Client


class Group(BaseModel):
    """Represents the groups that entities belong to."""

    def __init__(self, *args, _client: Optional["Client"] = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        object.__setattr__(self, "_client", _client)

    group_id: str = Field(
        ...,
        description="A unique string identifying different types/groups of entities.",
    )
    _client: "Client"
    entities: Dict[str, "Entity"] = Field(
        {},
        description="A dictionary of all entities belonging to the group "
        "indexed by their :code:`entity_id`.",
    )

    def _add_entity(self, slug: str, state: State) -> None:
        """Registers entities to this Group object"""
        self.entities[slug] = Entity(
            slug=slug,
            state=state,
            group=self,
        )

    def get_entity(self, slug: str) -> Optional["Entity"]:
        """Returns Entity with the given name if it exists. Otherwise returns None"""
        return self.entities.get(slug)

    def __getattr__(self, key: str) -> Any:
        if key in self.entities:
            return self.get_entity(key)
        return super().__getattribute__(key)


class Entity(BaseModel):
    """Represents entities inside of homeassistant"""

    slug: str
    state: State
    group: Group = Field(exclude=True, repr=False)

    def get_state(self) -> State:
        """Asks Home Assistant for the state of the entity and updates it locally"""
        self.state = self.group._client.get_state(entity_id=self.entity_id)
        return self.state

    def update_state(self) -> State:
        """
        Tells Home Assistant to set its current local State object.
        (You can modify the local state object yourself.)
        """
        self.state = self.group._client.set_state(self.state)
        return self.state

    @property
    def entity_id(self) -> str:
        """Constructs the :code:`entity_id` string from its group and slug"""
        return f"{self.group.group_id}.{self.slug}".strip()

    def get_history(
        self,
        start_timestamp: Optional[datetime] = None,
        # Defaults to 1 day before. https://developers.home-assistant.io/docs/api/rest/
        end_timestamp: Optional[datetime] = None,
        significant_changes_only: bool = False,
    ) -> Optional[History]:
        """Gets the previous :py:class:`State`'s of the :py:class:`Entity`"""
        for history in self.group._client.get_entity_histories(
            entities=(self,),
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
            significant_changes_only=significant_changes_only,
        ):
            return history
        return None

    async def async_get_state(self) -> State:
        """Asks Home Assistant for the state of the entity and sets it locally"""
        self.state = await self.group._client.get_state(
            group_id=self.group.group_id,
            slug=self.slug,
        )
        return self.state

    async def async_update_state(self) -> State:
        """Tells Home Assistant to set the current local State object."""
        self.state = await self.group._client.set_state(self.state)
        return self.state

    async def async_get_history(
        self,
        start_timestamp: Optional[datetime] = None,
        # Defaults to 1 day before. https://developers.home-assistant.io/docs/api/rest/
        end_timestamp: Optional[datetime] = None,
        significant_changes_only: bool = False,
    ) -> Optional[History]:
        """
        Gets the :py:class:`History` of previous :py:class:`State`'s of the :py:class:`Entity`.
        """
        async for history in self.group._client.get_entity_histories(
            entities=(self,),
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
            significant_changes_only=significant_changes_only,
        ):
            return history
        return None
