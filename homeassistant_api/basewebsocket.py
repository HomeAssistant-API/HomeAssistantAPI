import logging
import time
import urllib.parse as urlparse
from typing import Any
from typing import cast

from pydantic import ValidationError

from homeassistant_api.errors import ReceivingError
from homeassistant_api.errors import ResponseError
from homeassistant_api.models.websocket import ErrorResponse
from homeassistant_api.models.websocket import EventResponse
from homeassistant_api.models.websocket import PingResponse
from homeassistant_api.models.websocket import ResultResponse

logger = logging.getLogger(__name__)


class BaseWebsocketClient:
    """Shared methods for Websocket clients."""

    api_url: str
    token: str
    max_size: int
    _id_counter: int
    _result_responses: dict[int, ResultResponse | None]
    _event_responses: dict[int, list[EventResponse]]
    _ping_responses: dict[int, PingResponse]

    def __init__(self, api_url: str, token: str, *, max_size: int = 2**24) -> None:
        parsed = urlparse.urlparse(api_url)
        if parsed.scheme not in {"ws", "wss"}:
            msg = f"Unknown scheme {parsed.scheme} in {api_url}"
            raise ValueError(msg)
        self.api_url = api_url
        self.token = token.strip()
        self.max_size = max_size

        self._id_counter = 0
        self._result_responses = {}  # id -> response
        self._event_responses = {}  # id -> [response, ...]
        self._ping_responses = {}  # id -> (sent, received)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.api_url!r})"

    def _request_id(self) -> int:
        """Get a unique id for a message."""
        self._id_counter += 1
        return self._id_counter

    def check_success(self, data: dict[str, Any]) -> None:
        """Check if a command message was successful."""
        try:
            error_resp = ErrorResponse.model_validate(data)
            msg = f"[{error_resp.error.code}] {error_resp.error.message}"
            raise ResponseError(msg)
        except ValidationError:
            pass

    def handle_recv(self, data: dict[str, Any]) -> None:
        """Handle a received message."""
        if "id" not in data:
            msg = "Received a message without an id outside the auth phase."
            raise ReceivingError(msg)
        self.check_success(data)
        self.parse_response(data)

    def parse_response(self, data: dict[str, Any]) -> None:
        data_id = cast("int", data["id"])
        if data.get("type") == "pong":
            logger.info("Received pong message")
            self._ping_responses[data_id].end = time.perf_counter_ns()
        elif data.get("type") == "result":
            logger.info("Received result message")
            if data.get("success"):
                self._result_responses[data_id] = ResultResponse.model_validate(data)
            else:
                error_resp = ErrorResponse.model_validate(data)
                msg = f"[{error_resp.error.code}] {error_resp.error.message}"
                raise ResponseError(msg)
        elif data.get("type") == "event":
            logger.info("Received event message %s", data["event"])
            self._event_responses[data_id].append(EventResponse.model_validate(data))
        else:
            msg = f"Received unexpected message type: {data}"
            raise ReceivingError(msg)
