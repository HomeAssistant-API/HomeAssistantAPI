import json
import logging
import time

# import threading

import websockets.sync.client as ws
from typing import Any

from homeassistant_api.errors import ReceivingError, ResponseError, UnauthorizedError


logger = logging.getLogger(__name__)


class RawWebSocketClient:
    api_url: str
    token: str
    _conn: ws.ClientConnection

    def __init__(
        self,
        api_url: str,
        token: str,
    ) -> None:
        self.api_url = api_url
        self.token = token
        self._conn = None
        self._id_counter = 0
        self._result_responses: dict[int, dict[str, Any]] = {}  # id -> response
        self._event_responses: dict[int, list[dict[str, Any]]] = (
            {}
        )  # id -> [response, ...]
        self._ping_responses: dict[int, dict[str, float]] = {}  # id -> (sent, received)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.api_url!r})"

    def __enter__(self):
        self._conn = ws.connect(self.api_url)
        self._conn.__enter__()
        self.authentication_phase()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._conn.__exit__(exc_type, exc_value, traceback)
        self._conn = None

    def _request_id(self) -> int:
        """Get a unique id for a message."""
        self._id_counter += 1
        return self._id_counter

    def _send(self, data: dict[str, Any]) -> None:
        """Send a message to the websocket server."""
        logger.info(f"Sending message: {data}")
        self._conn.send(json.dumps(data))

    def _recv(self) -> dict[str, Any]:
        """Receive a message from the websocket server."""
        _bytes = self._conn.recv()

        # logger.info(f"Received message: {_bytes}")

        return json.loads(_bytes)

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
            match data["type"]:
                case "subscribe_events" | "subscribe_trigger":
                    self._event_responses[data["id"]] = []
                    self._result_responses[data["id"]] = None
                case "ping":
                    self._ping_responses[data["id"]] = {"start": time.perf_counter_ns()}
                case (
                    _
                ):  # anything else is one-time command that returns a "type": "result" entry
                    self._result_responses[data["id"]] = None
            return data["id"]
        return -1  # non-command messages don't have an id

    def check_success(self, data: dict[str, Any]) -> None:
        """Check if a command message was successful."""
        match data:
            case {"type": "result", "success": False, "error": {}}:
                raise ResponseError(data["error"].pop("message"), data["error"])
            case {"type": "result", "success": True}:
                # this is the expected case
                pass
            case {"type": "result"}:
                raise ResponseError(
                    "Wrongly formatted response", data
                )  # because "type": "result" should imply a "success" key
        return data

    def handle_recv(self, data: dict[str, Any]) -> dict[str, Any]:
        """Handle a received message."""
        if "id" not in data:
            raise ReceivingError(
                "Received a message without an id outside the auth phase."
            )

        match data:
            case {"type": "pong"}:
                logger.info("Received pong message")
                self._ping_responses[data["id"]].update(
                    {"end": time.perf_counter_ns(), **data}
                )
                data = self._ping_responses[data["id"]]
            case {"type": "result"}:
                logger.info("Received result message")
                self._result_responses[data["id"]] = data
            case {"type": "event"}:
                logger.info("Received event message")
                self._event_responses[data["id"]].append(data)
            case _:
                logger.warning(f"Received unknown message: {data}")

        return self.check_success(data)

    def recv(self, id: int) -> dict[str, Any]:
        """Receive a response to a message from the websocket server."""
        while True:
            ## have we received a message with the id we're looking for?
            if self._result_responses.get(id) is not None:
                return self._result_responses.pop(id)
            if self._event_responses.get(id, []):
                if len(self._event_responses[id]) > 0:
                    return self._event_responses[id].pop(0)
            if self._ping_responses.get(id, {}).get("end") is not None:
                return self._ping_responses.pop(id)

            ## if not, keep receiving messages until we do
            data = self._recv()

            if "id" not in data:
                raise ResponseError(
                    "Received a message without an id outside the auth phase."
                )

            self.handle_recv(data)

    def authentication_phase(self) -> dict[str, Any]:
        """Authenticate with the websocket server."""
        # Capture the first message from the server saying we need to authenticate
        welcome = self._recv()
        logging.debug(f"Received welcome message: {welcome}")
        if welcome["type"] != "auth_required":
            raise ResponseError("Unexpected response during authentication")

        # Send our authentication token
        self.send("auth", access_token=self.token, include_id=False)
        logging.debug("Sent auth message")
        # Check the response
        match (resp := self._recv())["type"]:
            case "auth_ok":
                return None
            case "auth_invalid":
                raise UnauthorizedError()
            case _:
                raise ResponseError(
                    "Unexpected response during authentication", resp["message"]
                )

    def ping_latency(self) -> float:
        """Get the latency (in milliseconds) of the connection by sending a ping message."""
        pong = self.recv(self.send("ping"))
        return (pong["end"] - pong["start"]) / 1_000_000
