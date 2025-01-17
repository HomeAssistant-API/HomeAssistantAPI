"""Interact with your Homeassistant Instance remotely."""

__all__ = (
    "Client",
    "State",
    "Service",
    "History",
    "Group",
    "Event",
    "Entity",
    "Domain",
    "Processing",
    "LogbookEntry",
    "APIConfigurationError",
    "EndpointNotFoundError",
    "HomeassistantAPIError",
    "MalformedDataError",
    "MalformedInputError",
    "MethodNotAllowedError",
    "ParameterMissingError",
    "RequestError",
    "UnauthorizedError",
    "WebsocketClient",
)

from .client import Client
from .errors import (
    APIConfigurationError,
    EndpointNotFoundError,
    HomeassistantAPIError,
    MalformedDataError,
    MalformedInputError,
    MethodNotAllowedError,
    ParameterMissingError,
    RequestError,
    UnauthorizedError,
)
from .models import Domain, Entity, Event, Group, History, LogbookEntry, Service, State
from .processing import Processing
from .websocket import WebsocketClient

Domain.model_rebuild()
Entity.model_rebuild()
Event.model_rebuild()
Group.model_rebuild()
History.model_rebuild()
Service.model_rebuild()
State.model_rebuild()
