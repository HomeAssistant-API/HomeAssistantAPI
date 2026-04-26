"""Module for Entity and entity Group data models"""

from datetime import datetime
from typing import TYPE_CHECKING
from typing import Any
from typing import Optional
from typing import Union

from pydantic import Field

from .base import BaseModel
from .history import History
from .states import State

if TYPE_CHECKING:
    from homeassistant_api import AsyncClient
    from homeassistant_api import AsyncWebsocketClient
    from homeassistant_api import Client
    from homeassistant_api import WebsocketClient


class BaseGroup(BaseModel):
    """Represents the groups that entities belong to."""

    group_id: str = Field(
        ...,
        description="A unique string identifying different types/groups of entities.",
    )
    entities: dict[str, "BaseEntity"] = Field(
        default_factory=dict,
        description="A dictionary of all entities belonging to the group "
        "indexed by their :code:`entity_id`.",
    )

    def _add_entity(self, slug: str, state: State) -> None:
        """Registers entities to this Group object"""
        raise NotImplementedError

    def get_entity(self, slug: str) -> Optional["BaseEntity"]:
        """Returns Entity with the given name if it exists. Otherwise returns None"""
        return self.entities.get(slug)

    def __getattr__(self, key: str) -> Any:
        if key in self.entities:
            return self.get_entity(key)
        return super().__getattribute__(key)


class Group(BaseGroup):
    """Sync group that creates sync Entity instances."""

    client: Union["Client", "WebsocketClient"] = Field(exclude=True, repr=False)

    def _add_entity(self, slug: str, state: State) -> None:
        self.entities[slug] = Entity(
            slug=slug,
            state=state,
            group=self,
        )

    def get_entity(self, slug: str) -> Optional["Entity"]:
        """Returns Entity with the given name if it exists. Otherwise returns None"""
        entity = self.entities.get(slug)
        if entity is not None and not isinstance(entity, Entity):
            msg = f"Expected Entity, got {type(entity)}"
            raise TypeError(msg)
        return entity


class AsyncGroup(BaseGroup):
    """Async group that creates async Entity instances."""

    client: Union["AsyncClient", "AsyncWebsocketClient"] = Field(
        exclude=True,
        repr=False,
    )

    def _add_entity(self, slug: str, state: State) -> None:
        self.entities[slug] = AsyncEntity(
            slug=slug,
            state=state,
            group=self,
        )

    def get_entity(self, slug: str) -> Optional["AsyncEntity"]:
        """Returns Entity with the given name if it exists. Otherwise returns None"""
        entity = self.entities.get(slug)
        if entity is not None and not isinstance(entity, AsyncEntity):
            msg = f"Expected AsyncEntity, got {type(entity)}"
            raise TypeError(msg)
        return entity


class BaseEntity(BaseModel):
    """Represents entities inside of homeassistant"""

    slug: str
    state: State
    group: "BaseGroup" = Field(exclude=True, repr=False)

    @property
    def entity_id(self) -> str:
        """Constructs the :code:`entity_id` string from its group and slug"""
        return f"{self.group.group_id}.{self.slug}".strip()


class Entity(BaseEntity):
    """Sync entity with sync client methods."""

    group: Group = Field(exclude=True, repr=False)

    def get_state(self) -> State:
        """Asks Home Assistant for the state of the entity and updates it locally"""
        self.state = self.group.client.get_state(entity_id=self.entity_id)
        return self.state

    def update_state(self) -> State:
        """
        Tells Home Assistant to set its current local State object.
        (You can modify the local state object yourself.)
        """
        self.state = self.group.client.set_state(self.state)
        return self.state

    def get_history(
        self,
        start_timestamp: datetime | None = None,
        end_timestamp: datetime | None = None,
        significant_changes_only: bool = False,
    ) -> History | None:
        """Gets the previous :py:class:`State`'s of the :py:class:`Entity`"""
        for history in self.group.client.get_entity_histories(
            entities=(self,),
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
            significant_changes_only=significant_changes_only,
        ):
            return history
        return None


class AsyncEntity(BaseEntity):
    """Async entity with async client methods."""

    group: AsyncGroup = Field(exclude=True, repr=False)

    async def get_state(self) -> State:
        """Asks Home Assistant for the state of the entity and sets it locally"""
        self.state = await self.group.client.get_state(
            group_id=self.group.group_id,
            slug=self.slug,
        )
        return self.state

    async def update_state(self) -> State:
        """Tells Home Assistant to set the current local State object."""
        self.state = await self.group.client.set_state(self.state)
        return self.state

    async def get_history(
        self,
        start_timestamp: datetime | None = None,
        end_timestamp: datetime | None = None,
        significant_changes_only: bool = False,
    ) -> History | None:
        """
        Gets the :py:class:`History` of previous :py:class:`State`'s of the :py:class:`Entity`.
        """
        async for history in self.group.client.get_entity_histories(
            entities=(self,),
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
            significant_changes_only=significant_changes_only,
        ):
            return history
        return None
