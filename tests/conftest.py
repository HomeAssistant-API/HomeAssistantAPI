import logging
import os
import time
from collections.abc import AsyncGenerator
from collections.abc import Generator
from http import HTTPMethod

import pytest
import pytest_asyncio
from niquests.exceptions import ConnectionError as RequestsConnectionError
from pytest_niquests_cassettes import Cassette

from homeassistant_api import AsyncClient
from homeassistant_api import AsyncWebsocketClient
from homeassistant_api import Client
from homeassistant_api import WebsocketClient

logger = logging.getLogger(__name__)
TIMEOUT = 300
HA_URL = os.environ.get("HOMEASSISTANTAPI_URL", "http://localhost:8123/api")
HA_WS_URL = os.environ.get(
    "HOMEASSISTANTAPI_WS_URL",
    "ws://localhost:8123/api/websocket",
)
HA_TOKEN = os.environ.get("HOMEASSISTANTAPI_TOKEN", "")


def pytest_sessionstart(session: pytest.Session) -> None:
    """Wait for the HA server to be ready — only needed in record mode."""
    if not session.config.getoption("--record", default=False):
        return
    client = Client(HA_URL, HA_TOKEN)
    deadline = time.monotonic() + TIMEOUT
    while time.monotonic() < deadline:
        try:
            client.request(method=HTTPMethod.GET, path="", timeout=5)
            logger.info("Server is ready.")
        except RequestsConnectionError:  # noqa: PERF203
            logger.info("Server not ready, retrying...")
            time.sleep(2)
        else:
            return
    msg = f"Server at {HA_URL} not ready after {TIMEOUT}s"
    raise TimeoutError(msg)


@pytest.fixture(name="cached_client", scope="session")
def setup_cached_client(cassette: Cassette) -> Generator[Client, None, None]:  # noqa: ARG001
    """Initializes the Client and enters a cached session."""
    with Client(HA_URL, HA_TOKEN) as client:
        yield client


@pytest_asyncio.fixture(name="async_cached_client", scope="session")
async def setup_async_cached_client(
    cassette: Cassette,  # noqa: ARG001
) -> AsyncGenerator[AsyncClient, None]:
    """Initializes the AsyncClient and enters an async cached session."""
    async with AsyncClient(HA_URL, HA_TOKEN) as client:
        yield client


@pytest.fixture(name="websocket_client", scope="session")
def setup_websocket_client(
    cassette: Cassette,  # noqa: ARG001
) -> Generator[WebsocketClient, None, None]:
    """Initializes the Client and enters a WebSocket session."""
    with WebsocketClient(HA_WS_URL, HA_TOKEN) as client:
        yield client


@pytest_asyncio.fixture(name="async_websocket_client", scope="session")
async def setup_async_websocket_client(
    cassette: Cassette,  # noqa: ARG001
) -> AsyncGenerator[AsyncWebsocketClient, None]:
    """Initializes the AsyncWebsocketClient and enters an async WebSocket session."""
    async with AsyncWebsocketClient(HA_WS_URL, HA_TOKEN) as client:
        yield client
