import os
from datetime import datetime

import niquests

from homeassistant_api import AsyncClient
from homeassistant_api import AsyncWebsocketClient
from homeassistant_api import Client
from homeassistant_api import WebsocketClient
from homeassistant_api.baseclient import BaseClient

HA_URL = os.environ.get("HOMEASSISTANTAPI_URL", "http://localhost:8123/api")
HA_WS_URL = os.environ.get(
    "HOMEASSISTANTAPI_WS_URL",
    "ws://localhost:8123/api/websocket",
)
HA_TOKEN = os.environ.get("HOMEASSISTANTAPI_TOKEN", "")


def test_custom_session(nimax_session: niquests.Session) -> None:
    with Client(
        HA_URL,
        HA_TOKEN,
        session=nimax_session,
    ):
        pass


def test_default_session(nimax_session: niquests.Session) -> None:  # noqa: ARG001
    with Client(
        HA_URL,
        HA_TOKEN,
    ):
        pass


async def test_custom_async_session(nimax_async_session: niquests.AsyncSession) -> None:
    async with AsyncClient(
        HA_URL,
        HA_TOKEN,
        session=nimax_async_session,
    ):
        pass


async def test_default_async_session(
    nimax_async_session: niquests.AsyncSession,
) -> None:
    async with AsyncClient(
        HA_URL,
        HA_TOKEN,
        session=nimax_async_session,
    ):
        pass


def test_websocket_client_ping(nimax_session: niquests.Session) -> None:
    with WebsocketClient(
        HA_WS_URL,
        HA_TOKEN,
        session=nimax_session,
    ) as client:
        assert client.ping_latency() > 0


async def test_async_websocket_client_ping(
    nimax_async_session: niquests.AsyncSession,
) -> None:
    async with AsyncWebsocketClient(
        HA_WS_URL,
        HA_TOKEN,
        session=nimax_async_session,
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
    start_time = datetime.fromisoformat(url.split("/")[-1])
    assert start_time.tzinfo is not None, "start_timestamp should have timezone offset"
    end_time_str = params["end_time"]
    assert end_time_str is not None
    end_time = datetime.fromisoformat(end_time_str)
    assert end_time.tzinfo is not None, "end_time should have timezone offset"


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
