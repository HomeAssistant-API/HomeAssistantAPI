from datetime import datetime

import pytest

from homeassistant_api.models import (
    ConfigEntryChange,
    ConfigEntryDisabler,
    ConfigEntryState,
)
from homeassistant_api.websocket import WebsocketClient


def test_listen_events(websocket_client: WebsocketClient) -> None:
    with websocket_client.listen_events("test_event") as events:
        websocket_client.fire_event(
            "test_event", message="Triggered by websocket client"
        )
        for _, event in zip(range(1), events):
            assert event.origin == "LOCAL"
            assert event.event_type == "test_event"
            assert event.data["message"] == "Triggered by websocket client"


async def test_async_listen_events(async_websocket_client: WebsocketClient) -> None:
    async with async_websocket_client.async_listen_events("async_test_event") as events:
        await async_websocket_client.async_fire_event(
            "async_test_event", message="Triggered by async websocket client"
        )
        async for _, event in zip(range(1), events):
            assert event.origin == "LOCAL"
            assert event.event_type == "async_test_event"
            assert event.data["message"] == "Triggered by async websocket client"


def test_listen_trigger(websocket_client: WebsocketClient) -> None:
    future = datetime.fromisoformat(
        websocket_client.get_rendered_template("{{ (now() + timedelta(seconds=1)) }}")
    )
    with websocket_client.listen_trigger(
        "time", at=future.strftime("%H:%M:%S")
    ) as triggers:
        for _, trigger in zip(range(1), triggers):
            assert trigger["trigger"]["platform"] == "time"
            assert datetime.fromisoformat(
                trigger["trigger"]["now"]
            ).timestamp() == pytest.approx(future.timestamp(), abs=1)


def test_listen_config_entries(websocket_client: WebsocketClient) -> None:
    with websocket_client.listen_config_entries() as flows:
        for i, flow in zip(range(5), flows):
            # The first "events" are currently available entries
            if i == 0:
                # Assumes that the first entry (sun.sun?) is enabled
                assert flow[0].type is None
                assert flow[0].entry.disabled_by is None
                assert flow[0].entry.state == ConfigEntryState.LOADED

                # Trigger an "updated" event
                websocket_client.disable_config_entry(flow[0].entry.entry_id)

            if i == 1:
                assert flow[0].type == ConfigEntryChange.UPDATED
                assert flow[0].entry.disabled_by == ConfigEntryDisabler.USER
                assert flow[0].entry.state == ConfigEntryState.UNLOAD_IN_PROGRESS

            if i == 2:
                assert flow[0].type == ConfigEntryChange.UPDATED
                assert flow[0].entry.disabled_by == ConfigEntryDisabler.USER
                assert flow[0].entry.state == ConfigEntryState.NOT_LOADED

                # Restore original state
                websocket_client.enable_config_entry(flow[0].entry.entry_id)

            if i == 3:
                assert flow[0].type == ConfigEntryChange.UPDATED
                assert flow[0].entry.disabled_by is None
                assert flow[0].entry.state == ConfigEntryState.SETUP_IN_PROGRESS

            if i == 4:
                assert flow[0].type == ConfigEntryChange.UPDATED
                assert flow[0].entry.disabled_by is None
                assert flow[0].entry.state == ConfigEntryState.LOADED


async def test_async_listen_trigger(async_websocket_client: WebsocketClient) -> None:
    future = datetime.fromisoformat(
        await async_websocket_client.async_get_rendered_template(
            "{{ (now() + timedelta(seconds=1)) }}"
        )
    )
    async with async_websocket_client.async_listen_trigger(
        "time", at=future.strftime("%H:%M:%S")
    ) as triggers:
        async for _, trigger in zip(range(1), triggers):
            assert trigger["trigger"]["platform"] == "time"
            assert datetime.fromisoformat(
                trigger["trigger"]["now"]
            ).timestamp() == pytest.approx(future.timestamp(), abs=1)
