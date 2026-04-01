import os

import aiohttp_client_cache.session
import requests_cache

from homeassistant_api import AsyncClient
from homeassistant_api import AsyncWebsocketClient
from homeassistant_api import Client
from homeassistant_api import WebsocketClient


def test_custom_cached_session() -> None:
    with Client(
        os.environ["HOMEASSISTANTAPI_URL"],
        os.environ["HOMEASSISTANTAPI_TOKEN"],
        session=requests_cache.CachedSession(),
    ):
        pass


def test_default_session() -> None:
    with Client(
        os.environ["HOMEASSISTANTAPI_URL"],
        os.environ["HOMEASSISTANTAPI_TOKEN"],
    ):
        pass


async def test_custom_async_cached_session() -> None:
    async with AsyncClient(
        os.environ["HOMEASSISTANTAPI_URL"],
        os.environ["HOMEASSISTANTAPI_TOKEN"],
        session=aiohttp_client_cache.session.CachedSession(
            cache=aiohttp_client_cache.SQLiteBackend(
                cache_name="test_custom_async_cached_session.sqlite",
                expire_after=10,
            ),
        ),
    ):
        pass


async def test_default_async_session() -> None:
    async with AsyncClient(
        os.environ["HOMEASSISTANTAPI_URL"],
        os.environ["HOMEASSISTANTAPI_TOKEN"],
    ):
        pass


def test_websocket_client_ping() -> None:
    with WebsocketClient(
        os.environ["HOMEASSISTANTAPI_WS_URL"],
        os.environ["HOMEASSISTANTAPI_TOKEN"],
    ) as client:
        assert client.ping_latency() > 0


async def test_async_websocket_client_ping() -> None:
    async with AsyncWebsocketClient(
        os.environ["HOMEASSISTANTAPI_WS_URL"],
        os.environ["HOMEASSISTANTAPI_TOKEN"],
    ) as client:
        assert (await client.ping_latency()) > 0
