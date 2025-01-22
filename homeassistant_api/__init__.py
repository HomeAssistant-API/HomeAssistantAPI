"""Interact with your Homeassistant Instance remotely."""

__all__ = (
    "Client",
    "State",
    "Context",
    "Domain",
    "Service",
    "Group",
    "Entity",
    "History",
    "Event",
    "LogbookEntry",
    "WebsocketClient",
    "AuthInvalid",
    "AuthOk",
    "AuthRequired",
    "ResultResponse",
    "ErrorResponse",
    "PingResponse",
    "EventResponse",
)

from .client import Client
from .models.domains import Domain, Service
from .models.entity import Entity, Group
from .models.events import Event
from .models.history import History
from .models.logbook import LogbookEntry
from .models.states import Context, State
from .models.websocket import (
    AuthInvalid,
    AuthOk,
    AuthRequired,
    ErrorResponse,
    EventResponse,
    PingResponse,
    ResultResponse,
)
from .websocket import WebsocketClient

Domain.model_rebuild()
Entity.model_rebuild()
Event.model_rebuild()
Group.model_rebuild()
History.model_rebuild()
Service.model_rebuild()
State.model_rebuild()
