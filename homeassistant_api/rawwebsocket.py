import json
import logging
import time
from typing import Any, Optional, Union, cast

import websockets.sync.client as ws
from pydantic import ValidationError

from homeassistant_api.errors import (
    ReceivingError,
    RequestError,
    ResponseError,
    UnauthorizedError,
)
from homeassistant_api.models.websocket import (
    AuthInvalid,
    AuthOk,
    AuthRequired,
    ErrorResponse,
    EventResponse,
    PingResponse,
    ResultResponse,
)
from homeassistant_api.utils import JSONType

logger = logging.getLogger(__name__)


class RawWebsocketClient:
    api_url: str
    token: str
    _conn: Optional[ws.ClientConnection]

    def __init__(
        self,
        api_url: str,
        token: str,
    ) -> None:
        self.api_url = api_url
        self.token = token.strip()
        self._conn = None

        self._id_counter = 0
        self._result_responses: dict[int, Optional[ResultResponse]] = (
            {}
        )  # id -> response
        self._event_responses: dict[int, list[EventResponse]] = (
            {}
        )  # id -> [response, ...]
        self._ping_responses: dict[int, PingResponse] = {}  # id -> (sent, received)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.api_url!r})"

    def __enter__(self):
        self._conn = ws.connect(self.api_url)
        self._conn.__enter__()
        okay = self.authentication_phase()
        logging.info("Authenticated with Home Assistant (%s)", okay.ha_version)
        self.supported_features_phase()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if not self._conn:
            raise ReceivingError("Connection is not open!")
        self._conn.__exit__(exc_type, exc_value, traceback)
        self._conn = None

    def _request_id(self) -> int:
        """Get a unique id for a message."""
        self._id_counter += 1
        return self._id_counter

    def _send(self, data: dict[str, JSONType]) -> None:
        """Send a message to the websocket server."""
        logger.debug(f"Sending message: {data}")
        if self._conn is None:
            raise ReceivingError("Connection is not open!")
        self._conn.send(json.dumps(data))

    def _recv(self) -> dict[str, JSONType]:
        """Receive a message from the websocket server."""
        if self._conn is None:
            raise ReceivingError("Connection is not open!")
        _bytes = self._conn.recv()
        logger.debug("Received message: %s", _bytes)
        return cast(dict[str, JSONType], json.loads(_bytes))

    def send(self, type: str, include_id: bool = True, **data: Any) -> int:
        """
        Send a command message to the websocket server and wait for a "result" response.

        Returns the id of the message sent.
        """
        if include_id:  # auth messages don't have an id
            data["id"] = self._request_id()

        data["type"] = type
        self._send(data)

        if "id" in data:
            assert isinstance(data["id"], int)
            if data["type"] == "ping":
                self._ping_responses[data["id"]] = PingResponse(
                    start=time.perf_counter_ns(),
                    id=data["id"],
                    type="pong",
                )
            else:
                self._event_responses[data["id"]] = []
                self._result_responses[data["id"]] = None
            return data["id"]
        return -1  # non-command messages don't have an id

    def check_success(self, data: dict[str, JSONType]) -> None:
        """Check if a command message was successful."""
        try:
            error_resp = ErrorResponse.model_validate(data)
            raise RequestError(error_resp.error.code, error_resp.error.message)
        except ValidationError:
            pass

    def handle_recv(self, data: dict[str, JSONType]) -> None:
        """Handle a received message."""
        if "id" not in data:
            raise ReceivingError(
                "Received a message without an id outside the auth phase."
            )
        self.check_success(data)
        self.parse_response(data)

    def parse_response(self, data: dict[str, JSONType]) -> None:
        data_id = cast(int, data["id"])
        if data.get("type") == "pong":
            logger.info("Received pong message")
            self._ping_responses[data_id].end = time.perf_counter_ns()
        elif data.get("type") == "result":
            logger.info("Received result message")
            if data.get("success"):
                self._result_responses[data_id] = ResultResponse.model_validate(data)
            else:
                error_resp = ErrorResponse.model_validate(data)
                raise RequestError(error_resp.error.code, error_resp.error.message)
        elif data.get("type") == "event":
            logger.info("Received event message %s", data["event"])
            self._event_responses[data_id].append(EventResponse.model_validate(data))
        else:
            raise ReceivingError(f"Received unexpected message type: {data}")

    def recv(self, id: int) -> Union[EventResponse, ResultResponse, PingResponse]:
        """Receive a response to a message from the websocket server."""
        while True:
            ## have we received a message with the id we're looking for?
            if self._result_responses.get(id) is not None:
                return cast(dict[int, ResultResponse], self._result_responses).pop(
                    id
                )  # ughhh why can't mypy figure this out
            if self._event_responses.get(id, []):
                return self._event_responses[id].pop(0)
            if self._ping_responses.get(id) is not None:
                if self._ping_responses[id].end is not None:
                    return self._ping_responses.pop(id)

            ## if not, keep receiving messages until we do
            self.handle_recv(self._recv())

    def authentication_phase(self) -> AuthOk:
        """Authenticate with the websocket server."""
        # Capture the first message from the server saying we need to authenticate
        try:
            welcome = AuthRequired.model_validate(self._recv())
            logger.debug(f"Received welcome message: {welcome}")
        except ValidationError as e:
            raise ResponseError("Unexpected response during authentication") from e

        # Send our authentication token
        self.send("auth", access_token=self.token, include_id=False)
        logger.debug("Sent auth message")

        # Check the response
        resp = self._recv()
        try:
            return AuthOk.model_validate(resp)
        except ValidationError as e:
            error_resp = AuthInvalid.model_validate(resp)
            raise UnauthorizedError(error_resp.message) from e
        except Exception as e:
            raise ResponseError(
                "Unexpected response during authentication", resp["message"]
            ) from e

    def supported_features_phase(self) -> None:
        """Get the supported features from the websocket server."""
        resp = self.recv(
            self.send(
                "supported_features",
                features={
                    # "coalesce_messages": 42, # including this key sets it to True
                },
            )
        )
        assert cast(ResultResponse, resp).result is None

    def ping_latency(self) -> float:
        """Get the latency (in milliseconds) of the connection by sending a ping message."""
        pong = cast(PingResponse, self.recv(self.send("ping")))
        assert pong.end is not None
        return (pong.end - pong.start) / 1_000_000
