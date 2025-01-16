"""A module defining the responses we expect from the websocket API."""

from typing import Any, Literal, Optional
from .base import BaseModel
from .states import Context, DatetimeIsoField


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
    start: Optional[float] = None  # added by the client
    end: Optional[float] = None  # added by the client


class Error(BaseModel):
    code: str
    message: str


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
    result: Optional[dict[str, Any]]


class FiredEvent(BaseModel):
    """A model to parse the `event` key of fired event websocket responses."""

    event_type: str
    data: dict[str, Any]
    origin: Literal["LOCAL", "REMOTE"]
    time_fired: DatetimeIsoField
    context: Optional[Context]


class EventResponse(BaseModel):
    """A model to parse the response of a fired event websocket response."""

    id: int
    type: Literal["event"]
    event: FiredEvent
