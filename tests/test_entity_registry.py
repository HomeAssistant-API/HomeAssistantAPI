"""Integration tests for entity registry WebSocket methods."""

from homeassistant_api import AsyncWebsocketClient
from homeassistant_api import WebsocketClient
from homeassistant_api.models.entity_registry import EntityRegistryEntry
from homeassistant_api.models.entity_registry import EntityRegistryEntryExtended
from homeassistant_api.models.entity_registry import EntityRegistryUpdateParams
from homeassistant_api.models.entity_registry import EntityRegistryUpdateResult

# A stable, always-present entity for read/update tests
_TEST_ENTITY_ID = "sensor.sun_next_dawn"

# Dedicated input_booleans for remove tests — HA re-adds them on restart
_REMOVE_ENTITY_ID = "input_boolean.smoke_registry_remove_test"
_ASYNC_REMOVE_ENTITY_ID = "input_boolean.smoke_registry_remove_test_async"


def test_list_entity_registry(websocket_client: WebsocketClient) -> None:
    entries = websocket_client.list_entity_registry()
    assert isinstance(entries, tuple)
    assert len(entries) > 0
    assert all(isinstance(e, EntityRegistryEntry) for e in entries)


def test_get_entity_registry_entry(websocket_client: WebsocketClient) -> None:
    entry = websocket_client.get_entity_registry_entry(_TEST_ENTITY_ID)
    assert isinstance(entry, EntityRegistryEntryExtended)
    assert entry.entity_id == _TEST_ENTITY_ID


def test_update_entity_registry_entry(websocket_client: WebsocketClient) -> None:
    result = websocket_client.update_entity_registry_entry(
        EntityRegistryUpdateParams(
            entity_id=_TEST_ENTITY_ID,
            name="Test Name",
        ),
    )
    assert isinstance(result, EntityRegistryUpdateResult)
    assert result.entity_entry.entity_id == _TEST_ENTITY_ID
    assert result.entity_entry.name == "Test Name"
    # Restore original state
    websocket_client.update_entity_registry_entry(
        EntityRegistryUpdateParams(
            entity_id=_TEST_ENTITY_ID,
            name=None,
        ),
    )


def test_remove_entity_registry_entry(websocket_client: WebsocketClient) -> None:
    websocket_client.recv(
        websocket_client.send(
            "input_boolean/create",
            name="smoke_registry_remove_test",
        ),
    )
    websocket_client.remove_entity_registry_entry(_REMOVE_ENTITY_ID)
    entity_ids = {e.entity_id for e in websocket_client.list_entity_registry()}
    assert _REMOVE_ENTITY_ID not in entity_ids


async def test_async_list_entity_registry(
    async_websocket_client: AsyncWebsocketClient,
) -> None:
    entries = await async_websocket_client.list_entity_registry()
    assert isinstance(entries, tuple)
    assert len(entries) > 0
    assert all(isinstance(e, EntityRegistryEntry) for e in entries)


async def test_async_get_entity_registry_entry(
    async_websocket_client: AsyncWebsocketClient,
) -> None:
    entry = await async_websocket_client.get_entity_registry_entry(_TEST_ENTITY_ID)
    assert isinstance(entry, EntityRegistryEntryExtended)
    assert entry.entity_id == _TEST_ENTITY_ID


async def test_async_update_entity_registry_entry(
    async_websocket_client: AsyncWebsocketClient,
) -> None:
    result = await async_websocket_client.update_entity_registry_entry(
        EntityRegistryUpdateParams(
            entity_id=_TEST_ENTITY_ID,
            name="Async Test Name",
        ),
    )
    assert isinstance(result, EntityRegistryUpdateResult)
    assert result.entity_entry.entity_id == _TEST_ENTITY_ID
    assert result.entity_entry.name == "Async Test Name"
    # Restore original state
    await async_websocket_client.update_entity_registry_entry(
        EntityRegistryUpdateParams(
            entity_id=_TEST_ENTITY_ID,
            name=None,
        ),
    )


async def test_async_remove_entity_registry_entry(
    async_websocket_client: AsyncWebsocketClient,
) -> None:
    await async_websocket_client.recv(
        await async_websocket_client.send(
            "input_boolean/create",
            name="smoke_registry_remove_test_async",
        ),
    )
    await async_websocket_client.remove_entity_registry_entry(_ASYNC_REMOVE_ENTITY_ID)
    entity_ids = {
        e.entity_id for e in await async_websocket_client.list_entity_registry()
    }
    assert _ASYNC_REMOVE_ENTITY_ID not in entity_ids
