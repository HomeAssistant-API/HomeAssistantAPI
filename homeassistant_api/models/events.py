"""Event Model File"""

from typing import TYPE_CHECKING
from typing import Any

from pydantic import Field
from typing_extensions import Self
from typing_extensions import override

from .base import BaseModel

if TYPE_CHECKING:
    from homeassistant_api import AsyncClient
    from homeassistant_api import Client


class BaseEvent(BaseModel):
    """
    Event class for Home Assistant Event Triggers

    For attribute information see the Data Science docs on Event models
    https://data.home-assistant.io/docs/events
    """

    event: str = Field(..., description="The event name/type.")
    listener_count: int = Field(
        ...,
        description="How many listeners are interested in this event in Home Assistant.",
    )

    @classmethod
    @override
    def from_json(cls, json: dict[str, Any] | Any | None, **kwargs: Any) -> Self:
        msg = f"`{cls.__name__}` does not support `from_json()`. Use `from_json_with_client()`"
        raise NotImplementedError(msg)


class Event(BaseEvent):
    """Sync event with sync fire method."""

    client: "Client" = Field(exclude=True, repr=False)

    @classmethod
    def from_json_with_client(cls, json: dict[str, Any], client: "Client") -> "Event":
        """Constructs Event model from json data"""
        return cls(**json, client=client)

    def fire(self, **event_data: Any) -> str | None:
        """Fires the corresponding event in Home Assistant."""
        return self.client.fire_event(self.event, **event_data)


class AsyncEvent(BaseEvent):
    """Async event with async fire method."""

    client: "AsyncClient" = Field(exclude=True, repr=False)

    @classmethod
    def from_json_with_client(
        cls,
        json: dict[str, Any],
        client: "AsyncClient",
    ) -> "AsyncEvent":
        """Constructs Event model from json data"""
        return cls(**json, client=client)

    async def fire(self, **event_data: Any) -> str:
        """Fires the event type in homeassistant."""
        return await self.client.fire_event(self.event, **event_data)
