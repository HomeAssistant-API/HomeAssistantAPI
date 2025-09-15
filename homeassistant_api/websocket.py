"""Module containing the primary Client class."""

import logging
import urllib.parse as urlparse

from .rawasyncwebsocket import RawAsyncWebsocketClient
from .rawwebsocket import RawWebsocketClient

logger = logging.getLogger(__name__)


class WebsocketClient(RawWebsocketClient, RawAsyncWebsocketClient):
    """

    The main class for interacting with the Home Assistant WebSocket API client.

    Here's a quick example of how to use the :py:class:`WebsocketClient` class:

    .. code-block:: python

        from homeassistant_api import WebsocketClient

        with WebsocketClient(
            '<WS API Server URL>', # i.e. 'ws://homeassistant.local:8123/api/websocket'
            '<Your Long Lived Access-Token>'
        ) as ws_client:
            light = ws_client.trigger_service('light', 'turn_on', entity_id="light.living_room")
    """

    def __init__(self, api_url: str, token: str, use_async: bool = False) -> None:
        parsed = urlparse.urlparse(api_url)

        if parsed.scheme in {"ws", "wss"}:
            if use_async:
                RawAsyncWebsocketClient.__init__(self, api_url, token)
                client_type = "Async"
            else:
                RawWebsocketClient.__init__(self, api_url, token)
                client_type = ""
        else:
            raise ValueError(f"Unknown scheme {parsed.scheme} in {api_url}")

        logger.debug(
            f"{client_type}WebSocketClient initialized with api_url: {api_url}"
        )
