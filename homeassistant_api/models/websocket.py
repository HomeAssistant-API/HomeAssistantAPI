"""A module defining the responses we expect from the websocket API."""

from typing import Any, Literal, Optional, Union

from homeassistant_api.utils import JSONType

from .base import BaseModel, DatetimeIsoField
from .states import Context

__all__ = (
    "AuthRequired",
    "AuthOk",
    "AuthInvalid",
    "PingResponse",
    "ErrorResponse",
    "ResultResponse",
    "EventResponse",
)


class AuthRequired(BaseModel):
    type: Literal["auth_required"]
    ha_version: str


class AuthOk(BaseModel):
    type: Literal["auth_ok"]
    ha_version: str


class AuthInvalid(BaseModel):
    type: Literal["auth_invalid"]
    message: str


class PingResponse(BaseModel):
    """Ping websocket response model."""

    id: int
    type: Literal["pong"]
    start: int  # added by the client, nanoseconds
    end: Optional[int] = None  # added by the client, nanoseconds


class Error(BaseModel):
    code: str
    message: str
    translation_key: str
    translation_placeholders: dict[str, str]
    translation_domain: str


class ErrorResponse(BaseModel):
    """Error websocket response model."""

    id: int
    success: Literal[False]
    type: Literal["result"]
    error: Error


class ResultResponse(BaseModel):
    """Result websocket response model."""

    id: int
    success: Literal[True]
    type: Literal["result"]
    result: Optional[Any]


class FiredEvent(BaseModel):
    """A model to parse the `event` key of fired event websocket responses."""

    event_type: str
    data: dict[str, JSONType]

    origin: Literal["LOCAL", "REMOTE"]
    # REMOTE if another API client or webhook fired the event
    # LOCAL if Home Assistant (or the auth token we used) fired the event

    time_fired: DatetimeIsoField  # datetime.datetime
    context: Optional[Context]


class TemplateEvent(BaseModel):
    result: str
    listeners: dict[str, JSONType]


class FiredTrigger(BaseModel):
    """A model to parse the `trigger` key of fired event websocket responses."""

    context: Optional[Context]
    variables: dict[str, JSONType]


class EventResponse(BaseModel):
    """A model to parse the response of a fired event websocket response."""

    id: int
    type: Literal["event"]
    event: Union[FiredEvent, FiredTrigger, TemplateEvent]
