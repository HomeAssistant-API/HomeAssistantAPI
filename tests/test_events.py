from datetime import datetime

import pytest

from homeassistant_api import AsyncWebsocketClient
from homeassistant_api import WebsocketClient
from homeassistant_api.models import ConfigEntryChange
from homeassistant_api.models import ConfigEntryDisabler
from homeassistant_api.models import ConfigEntryState
from homeassistant_api.models.websocket import FiredEvent


def test_listen_events(websocket_client: WebsocketClient) -> None:
    with websocket_client.listen_events("test_event") as events:
        websocket_client.fire_event(
            "test_event",
            message="Triggered by websocket client",
        )
        for event in events:
            assert isinstance(event, FiredEvent)
            assert event.origin == "LOCAL"
            assert event.event_type == "test_event"
            assert event.data["message"] == "Triggered by websocket client"
            break


async def test_async_listen_events(
    async_websocket_client: AsyncWebsocketClient,
) -> None:
    async with async_websocket_client.listen_events("async_test_event") as events:
        await async_websocket_client.fire_event(
            "async_test_event",
            message="Triggered by async websocket client",
        )
        # Typing breaks when using zip in an async context, so break instead
        async for event in events:
            assert isinstance(event, FiredEvent)
            assert event.origin == "LOCAL"
            assert event.event_type == "async_test_event"
            assert event.data["message"] == "Triggered by async websocket client"
            break


def test_listen_trigger(websocket_client: WebsocketClient) -> None:
    future = datetime.fromisoformat(
        websocket_client.get_rendered_template("{{ (now() + timedelta(seconds=1)) }}"),
    )
    with websocket_client.listen_trigger(
        "time",
        at=future.strftime("%H:%M:%S"),
    ) as triggers:
        for trigger in triggers:
            assert trigger["trigger"]["platform"] == "time"
            assert datetime.fromisoformat(
                trigger["trigger"]["now"],
            ).timestamp() == pytest.approx(future.timestamp(), abs=1)
            break


def test_listen_config_entries(websocket_client: WebsocketClient) -> None:
    with websocket_client.listen_config_entries() as flows:
        for i, flow in zip(range(5), flows, strict=False):
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


async def test_async_listen_config_entries(
    async_websocket_client: AsyncWebsocketClient,
) -> None:
    async with async_websocket_client.listen_config_entries() as flows:
        i = 0
        async for flow in flows:
            if i == 0:
                # The first "events" are currently available entries
                assert flow[0].type is None
                assert flow[0].entry.disabled_by is None
                assert flow[0].entry.state == ConfigEntryState.LOADED

                # Trigger an "updated" event
                await async_websocket_client.disable_config_entry(
                    flow[0].entry.entry_id,
                )

            if i == 1:
                assert flow[0].type == ConfigEntryChange.UPDATED
                assert flow[0].entry.disabled_by == ConfigEntryDisabler.USER
                assert flow[0].entry.state == ConfigEntryState.UNLOAD_IN_PROGRESS

            if i == 2:
                assert flow[0].type == ConfigEntryChange.UPDATED
                assert flow[0].entry.disabled_by == ConfigEntryDisabler.USER
                assert flow[0].entry.state == ConfigEntryState.NOT_LOADED

                # Restore original state
                await async_websocket_client.enable_config_entry(flow[0].entry.entry_id)

            if i == 3:
                assert flow[0].type == ConfigEntryChange.UPDATED
                assert flow[0].entry.disabled_by is None
                assert flow[0].entry.state == ConfigEntryState.SETUP_IN_PROGRESS

            if i == 4:
                assert flow[0].type == ConfigEntryChange.UPDATED
                assert flow[0].entry.disabled_by is None
                assert flow[0].entry.state == ConfigEntryState.LOADED
                break

            i += 1


async def test_async_listen_trigger(
    async_websocket_client: AsyncWebsocketClient,
) -> None:
    future = datetime.fromisoformat(
        await async_websocket_client.get_rendered_template(
            "{{ (now() + timedelta(seconds=1)) }}",
        ),
    )
    async with async_websocket_client.listen_trigger(
        "time",
        at=future.strftime("%H:%M:%S"),
    ) as triggers:
        # Typing breaks when using zip in an async context, so break instead
        async for trigger in triggers:
            assert trigger["trigger"]["platform"] == "time"
            assert datetime.fromisoformat(
                trigger["trigger"]["now"],
            ).timestamp() == pytest.approx(future.timestamp(), abs=1)
            break
