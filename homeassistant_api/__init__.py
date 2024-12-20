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
    "WebSocketClient",
)

from .client import Client
from .websocket import WebSocketClient
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

Domain.model_rebuild()
Entity.model_rebuild()
Event.model_rebuild()
Group.model_rebuild()
History.model_rebuild()
Service.model_rebuild()
State.model_rebuild()
