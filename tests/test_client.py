import os
from datetime import datetime
from pathlib import Path

import aiohttp_client_cache.session
import requests_cache

from homeassistant_api import AsyncClient
from homeassistant_api import AsyncWebsocketClient
from homeassistant_api import Client
from homeassistant_api import WebsocketClient
from homeassistant_api.baseclient import BaseClient


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


async def test_custom_async_cached_session(tmp_path: Path) -> None:
    cache_path = tmp_path / "test_custom_async_cached_session.sqlite"
    async with AsyncClient(
        os.environ["HOMEASSISTANTAPI_URL"],
        os.environ["HOMEASSISTANTAPI_TOKEN"],
        session=aiohttp_client_cache.session.CachedSession(
            cache=aiohttp_client_cache.SQLiteBackend(
                cache_name=str(cache_path),
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


# --- BaseClient: prepare_get_entity_histories_params with naive timestamps ---


def test_prepare_entity_histories_naive_timestamps() -> None:
    """Tests that naive (tzinfo=None) timestamps are converted to local timezone."""
    naive_start = datetime(2024, 1, 1, 12, 0, 0)  # noqa: DTZ001
    naive_end = datetime(2024, 6, 1, 12, 0, 0)  # noqa: DTZ001
    params, url = BaseClient.prepare_get_entity_histories_params(
        start_timestamp=naive_start,
        end_timestamp=naive_end,
    )
    # Naive timestamps should get a timezone attached
    assert "+" in url or "-" in url.split("T")[-1], (
        "start_timestamp should have timezone offset"
    )
    assert "+" in params["end_time"] or "-" in params["end_time"].split("T")[-1], (
        "end_time should have timezone offset"
    )


# --- BaseClient: prepare_get_logbook_entry_params ---


def test_prepare_logbook_entry_no_start_timestamp() -> None:
    """Tests logbook params without a start_timestamp return base 'logbook' path."""
    params, url = BaseClient.prepare_get_logbook_entry_params(
        filter_entities=["light.kitchen", "light.bedroom"],
        end_timestamp=datetime(2024, 6, 1, 12, 0, 0),  # noqa: DTZ001
    )
    assert url == "logbook"
    assert "light.kitchen,light.bedroom" in params["entity"]
    assert "end_time" in params


def test_prepare_logbook_entry_string_timestamps() -> None:
    """Tests logbook params with string timestamps pass through unchanged."""
    params, url = BaseClient.prepare_get_logbook_entry_params(
        start_timestamp="2024-01-01T00:00:00",
        end_timestamp="2024-06-01T00:00:00",
    )
    assert "2024-01-01T00:00:00" in url
    assert params["end_time"] == "2024-06-01T00:00:00"
