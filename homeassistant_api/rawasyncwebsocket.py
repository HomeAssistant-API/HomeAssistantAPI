import json
import logging
import time
from typing import Any, Optional, Union, cast

import websockets.asyncio.client as ws
from pydantic import ValidationError

from homeassistant_api.errors import (
    ReceivingError,
    ResponseError,
    UnauthorizedError,
)
from homeassistant_api.models.websocket import (
    AuthInvalid,
    AuthOk,
    AuthRequired,
    EventResponse,
    PingResponse,
    ResultResponse,
)
from homeassistant_api.rawbasewebsocket import RawBaseWebsocketClient
from homeassistant_api.utils import JSONType

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class RawAsyncWebsocketClient(RawBaseWebsocketClient):
    api_url: str
    token: str
    _conn: Optional[ws.ClientConnection]

    def __init__(
        self,
        api_url: str,
        token: str,
    ) -> None:
        super().__init__(api_url, token)
        self._conn = None

    async def __aenter__(self):
        self._conn = await ws.connect(self.api_url)
        await self._conn.__aenter__()
        okay = await self.authentication_phase()
        logging.info("Authenticated with Home Assistant (%s)", okay.ha_version)
        await self.supported_features_phase()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        if not self._conn:
            raise ReceivingError("Connection is not open!")
        await self._conn.__aexit__(exc_type, exc_value, traceback)
        self._conn = None

    async def _send(self, data: dict[str, JSONType]) -> None:
        """Send a message to the websocket server."""
        logger.debug(f"Sending message: {data}")
        if self._conn is None:
            raise ReceivingError("Connection is not open!")
        await self._conn.send(json.dumps(data))

    async def _recv(self) -> dict[str, JSONType]:
        """Receive a message from the websocket server."""
        if self._conn is None:
            raise ReceivingError("Connection is not open!")
        _bytes = await self._conn.recv()
        logger.debug("Received message: %s", _bytes)
        return cast(dict[str, JSONType], json.loads(_bytes))

    async def send(self, type: str, include_id: bool = True, **data: Any) -> int:
        """
        Send a command message to the websocket server and wait for a "result" response.

        Returns the id of the message sent.
        """
        if include_id:  # auth messages don't have an id
            data["id"] = self._request_id()

        data["type"] = type
        await self._send(data)

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

    async def recv(self, id: int) -> Union[EventResponse, ResultResponse, PingResponse]:
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
            self.handle_recv(await self._recv())

    async def authentication_phase(self) -> AuthOk:
        """Authenticate with the websocket server."""
        # Capture the first message from the server saying we need to authenticate
        try:
            welcome = AuthRequired.model_validate(await self._recv())
            logger.debug(f"Received welcome message: {welcome}")
        except ValidationError as e:
            raise ResponseError("Unexpected response during authentication") from e

        # Send our authentication token
        await self.send("auth", access_token=self.token, include_id=False)
        logger.debug("Sent auth message")

        # Check the response
        resp = await self._recv()
        try:
            return AuthOk.model_validate(resp)
        except ValidationError as e:
            error_resp = AuthInvalid.model_validate(resp)
            raise UnauthorizedError(error_resp.message) from e
        except Exception as e:
            raise ResponseError(
                "Unexpected response during authentication", resp["message"]
            ) from e

    async def supported_features_phase(self) -> None:
        """Get the supported features from the websocket server."""
        resp = await self.recv(
            await self.send(
                "supported_features",
                features={
                    # "coalesce_messages": 42, # including this key sets it to True
                },
            )
        )
        assert cast(ResultResponse, resp).result is None

    async def ping_latency(self) -> float:
        """Get the latency (in milliseconds) of the connection by sending a ping message."""
        pong = cast(PingResponse, await self.recv(await self.send("ping")))
        assert pong.end is not None
        return (pong.end - pong.start) / 1_000_000
