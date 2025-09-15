"""Event Model File"""

from typing import TYPE_CHECKING, Any, Optional, Union
from typing_extensions import Self
from pydantic import Field
from typing_extensions import override

from homeassistant_api.utils import JSONType

from .base import BaseModel

if TYPE_CHECKING:
    from homeassistant_api import Client


class Event(BaseModel):
    """
    Event class for Home Assistant Event Triggers

    For attribute information see the Data Science docs on Event models
    https://data.home-assistant.io/docs/events
    """

    _client: "Client"
    event: str = Field(..., description="The event name/type.")
    listener_count: int = Field(
        ...,
        description="How many listeners are interesting in this event in Home Assistant.",
    )

    def __init__(self, *args, _client: Optional["Client"] = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        object.__setattr__(self, "_client", _client)

    def fire(self, **event_data) -> Optional[str]:
        """Fires the corresponding event in Home Assistant."""
        return self._client.fire_event(self.event, **event_data)

    async def async_fire(self, **event_data) -> str:
        """Fires the event type in homeassistant. Ex. `on_startup`"""
        return await self._client.async_fire_event(self.event, **event_data)

    @classmethod
    @override
    def from_json(cls, json: Union[dict[str, JSONType], Any, None], **kwargs) -> Self:
        raise ValueError(
            f"`{cls.__name__}` does not support `from_json()`. Use `from_json_with_client()`"
        )

    @classmethod
    def from_json_with_client(
        cls, json: dict[str, JSONType], client: "Client"
    ) -> "Event":
        """Constructs Event model from json data"""
        return cls(**json, _client=client)
