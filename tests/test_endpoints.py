"""Module for making sure endpoints that should succeed, do indeed succeed."""

import logging
from datetime import datetime

import pytest

from homeassistant_api import Client
from homeassistant_api.errors import RequestError
from homeassistant_api.models import ConfigEntryDisabler
from homeassistant_api.models.events import Event
from homeassistant_api.models.states import State
from homeassistant_api.websocket import WebsocketClient


def test_get_error_log(cached_client: Client) -> None:
    """Tests the `GET /api/error_log` endpoint."""
    assert cached_client.get_error_log()


async def test_async_get_error_log(async_cached_client: Client) -> None:
    """Tests the `GET /api/error_log` endpoint."""
    assert await async_cached_client.async_get_error_log()


def test_get_config(cached_client: Client) -> None:
    """Tests the `GET /api/config` endpoint."""
    assert cached_client.get_config().get("state") in {"RUNNING", "NOT_RUNNING"}


async def test_async_get_config(async_cached_client: Client) -> None:
    """Tests the `GET /api/config` endpoint."""
    assert (await async_cached_client.async_get_config()).get("state") in {
        "RUNNING",
        "NOT_RUNNING",
    }


def test_get_logbook_entries(cached_client: Client) -> None:
    """Tests the `GET /api/logbook/<timestamp>` endpoint."""
    for entry in cached_client.get_logbook_entries(
        filter_entities="sun.red_sun",
        start_timestamp=datetime(2020, 1, 1),
        end_timestamp=datetime.now(),
    ):
        assert entry


async def test_async_get_logbook_entries(async_cached_client: Client) -> None:
    """Tests the `GET /api/logbook/<timestamp>` endpoint."""
    async for entry in async_cached_client.async_get_logbook_entries(
        filter_entities="sun.red_sun",
        start_timestamp=datetime(2020, 1, 1),
        end_timestamp=datetime.now(),
    ):
        assert entry


def test_get_entity(cached_client: Client) -> None:
    """Tests the `GET /api/states/<entity_id>` endpoint."""
    assert cached_client.get_entity(entity_id="sun.sun")


async def test_async_get_entity(async_cached_client: Client) -> None:
    """Tests the `GET /api/states/<entity_id>` endpoint."""
    assert await async_cached_client.async_get_entity(entity_id="sun.sun")


def test_get_entity_histories(cached_client: Client) -> None:
    """Tests the `GET /api/history/period/<timestamp>` endpoint."""
    sun = cached_client.get_entity(entity_id="sun.sun")
    assert sun is not None
    histories = list(
        cached_client.get_entity_histories(
            (sun,),
            end_timestamp=datetime.now(),
            start_timestamp=datetime(2020, 1, 1),
            significant_changes_only=True,
        )
    )
    assert histories, "No history found."
    assert histories[0].states, "No states in entity history found."
    assert isinstance(histories[0].states[0], State)


async def test_async_get_entity_histories(async_cached_client: Client) -> None:
    """Tests the `GET /api/history/period/<timestamp>` endpoint."""
    sun = await async_cached_client.async_get_entity(entity_id="sun.sun")
    assert sun is not None
    histories = [
        history
        async for history in async_cached_client.async_get_entity_histories((sun,))
    ]
    assert histories, "No history found."
    assert histories[0].states, "No states in entity history found."
    assert isinstance(histories[0].states[0], State)


def test_get_rendered_template(cached_client: Client) -> None:
    """Tests the `POST /api/template` endpoint."""
    rendered_template = cached_client.get_rendered_template(
        'The sun is {{ states("sun.sun").replace("_", " the ") }}.'
    )
    assert rendered_template in {
        "The sun is above the horizon.",
        "The sun is below the horizon.",
    }


async def test_async_get_rendered_template(async_cached_client: Client) -> None:
    """Tests the `POST /api/template` endpoint."""
    rendered_template = await async_cached_client.async_get_rendered_template(
        'The sun is {{ states("sun.sun").replace("_", " the ") }}.'
    )
    assert rendered_template in {
        "The sun is above the horizon.",
        "The sun is below the horizon.",
    }


def test_websocket_get_rendered_template(websocket_client: WebsocketClient) -> None:
    """Tests the `"type": "render_template"` websocket command."""
    rendered_template = websocket_client.get_rendered_template(
        'The sun is {{ states("sun.sun").replace("_", " the ") }}.'
    )
    assert rendered_template in {
        "The sun is above the horizon.",
        "The sun is below the horizon.",
    }


async def test_async_websocket_get_rendered_template(
    async_websocket_client: WebsocketClient,
) -> None:
    """Tests the `"type": "render_template"` websocket command."""
    rendered_template = await async_websocket_client.async_get_rendered_template(
        'The sun is {{ states("sun.sun").replace("_", " the ") }}.'
    )
    assert rendered_template in {
        "The sun is above the horizon.",
        "The sun is below the horizon.",
    }


def test_check_api_config(cached_client: Client) -> None:
    """Tests the `POST /api/config/core/check_config` endpoint."""
    assert cached_client.check_api_config()


async def test_async_check_api_config(async_cached_client: Client) -> None:
    """Tests the `POST /api/config/core/check_config` endpoint."""
    assert await async_cached_client.async_check_api_config()


def test_get_entities(cached_client: Client) -> None:
    """Tests the `GET /api/states` endpoint."""
    entities = cached_client.get_entities()
    assert "sun" in entities


async def test_async_get_entities(async_cached_client: Client) -> None:
    """Tests the `GET /api/states` endpoint."""
    entities = await async_cached_client.async_get_entities()
    assert "sun" in entities


def test_websocket_get_config(websocket_client: WebsocketClient) -> None:
    """Tests the `"type": "get_config"` websocket command."""
    config = websocket_client.get_config()
    assert isinstance(config, dict)
    assert config.get("state") in {"RUNNING", "NOT_RUNNING"}


def test_websocket_get_state(websocket_client: WebsocketClient) -> None:
    """Tests WebsocketClient.get_state with entity_id."""
    state = websocket_client.get_state(entity_id="sun.sun")
    assert state.entity_id == "sun.sun"
    assert state.state in {"above_horizon", "below_horizon"}


def test_websocket_get_entity_by_group_slug(websocket_client: WebsocketClient) -> None:
    """Tests WebsocketClient.get_entity with group_id and slug."""
    entity = websocket_client.get_entity(group_id="sun", slug="sun")
    assert entity is not None
    assert entity.entity_id == "sun.sun"


def test_websocket_get_entity_by_entity_id(websocket_client: WebsocketClient) -> None:
    """Tests WebsocketClient.get_entity with entity_id."""
    entity = websocket_client.get_entity(entity_id="sun.sun")
    assert entity is not None
    assert entity.entity_id == "sun.sun"


def test_websocket_get_entity_no_args(websocket_client: WebsocketClient) -> None:
    """Tests WebsocketClient.get_entity raises ValueError with no arguments."""
    with pytest.raises(
        ValueError, match="Neither group_id and slug or entity_id provided"
    ):
        websocket_client.get_entity()


def test_websocket_get_state_not_found(websocket_client: WebsocketClient) -> None:
    """Tests WebsocketClient.get_state raises ValueError for nonexistent entity."""
    with pytest.raises(ValueError, match="not found"):
        websocket_client.get_state(entity_id="fake.nonexistent_entity_12345")


def test_websocket_get_entities(websocket_client: WebsocketClient) -> None:
    """Tests the `"type": "get_entities"` websocket command."""
    entities = websocket_client.get_entities()
    assert "sun" in entities


async def test_async_websocket_get_entities(
    async_websocket_client: WebsocketClient,
) -> None:
    """Tests the `"type": "get_entities"` websocket command."""
    entities = await async_websocket_client.async_get_entities()
    assert "sun" in entities


def test_get_domains(cached_client: Client) -> None:
    """Tests the `GET /api/services` endpoint."""
    domains = cached_client.get_domains()
    assert "homeassistant" in domains


async def test_async_get_domains(async_cached_client: Client) -> None:
    """Tests the `GET /api/services` endpoint."""
    domains = await async_cached_client.async_get_domains()
    assert "homeassistant" in domains


def test_websocket_get_domains(websocket_client: WebsocketClient) -> None:
    """Tests the `"type": "get_domains"` websocket command."""
    domains = websocket_client.get_domains()
    assert "homeassistant" in domains


async def test_async_websocket_get_domains(
    async_websocket_client: WebsocketClient,
) -> None:
    """Tests the `"type": "get_domains"` websocket command."""
    domains = await async_websocket_client.async_get_domains()
    assert "homeassistant" in domains


def test_get_domain(cached_client: Client) -> None:
    """Tests the `GET /api/services` endpoint."""
    domain = cached_client.get_domain("homeassistant")
    assert domain is not None
    assert domain.services


async def test_async_get_domain(async_cached_client: Client) -> None:
    """Tests the `GET /api/services` endpoint."""
    domain = await async_cached_client.async_get_domain("homeassistant")
    assert domain is not None
    assert domain.services


def test_websocket_get_domain(websocket_client: WebsocketClient) -> None:
    """Tests the `"type": "get_domain"` websocket command."""
    domain = websocket_client.get_domain("homeassistant")
    assert domain is not None
    assert domain.services


async def test_async_websocket_get_domain(
    async_websocket_client: WebsocketClient,
) -> None:
    """Tests the `"type": "get_domain"` websocket command."""
    domain = await async_websocket_client.async_get_domain("homeassistant")
    assert domain is not None
    assert domain.services


def test_get_nonuser_flows_in_progress(websocket_client: WebsocketClient) -> None:
    """Tests the `"type": "config_entries/flow/progress"` websocket command."""
    # No flows in progress
    flows = websocket_client.get_nonuser_flows_in_progress()
    assert not flows


def test_disable_enable_config_entry(websocket_client: WebsocketClient) -> None:
    """Tests the `"type": "config_entries/disable"` websocket command."""
    # Get sun entry
    entry = websocket_client.get_config_entries()[0]
    assert entry.disabled_by is None

    # Disable entry
    websocket_client.disable_config_entry(entry.entry_id)

    # Check that it was disabled
    disabled_entry = websocket_client.get_config_entries()[0]
    assert disabled_entry.disabled_by is ConfigEntryDisabler.USER

    # Re-enable
    websocket_client.enable_config_entry(entry.entry_id)

    # Check that it was enable
    enabled_entry = websocket_client.get_config_entries()[0]
    assert enabled_entry.disabled_by is None


def test_ignore_config_flow(websocket_client: WebsocketClient) -> None:
    """Tests the `"type": "config_entries/ignore_flow"` websocket command."""
    # Currently not able to test as no flows are in progress. Send invalid parameters and handle that error
    try:
        websocket_client.ignore_config_flow("", "")
    except RequestError as error:
        assert (
            error.__str__()
            == "An error occurred while making the request to 'Config entry not found' with data: 'not_found'"
        )


def test_get_config_entries(websocket_client: WebsocketClient) -> None:
    """Tests the `"type": "config_entries/get"` websocket command."""
    # Check number of entries
    entries = websocket_client.get_config_entries()
    assert len(entries) == 4

    # Check that entries have expected values
    sun = entries[0]
    # Usually some kind of float. Is 0.0 in testing environment
    assert sun.created_at == 0.0
    assert sun.entry_id == "5f8426fa502435857743f302651753c9"
    assert sun.domain == "sun"
    assert sun.modified_at == 0.0
    assert sun.title == "Sun"
    assert sun.source == "import"
    assert sun.supports_options is False
    assert sun.supports_remove_device is False
    assert sun.supports_unload is True
    assert sun.supports_reconfigure is False
    assert sun.supported_subentry_types == {}
    assert sun.pref_disable_new_entities is False
    assert sun.pref_disable_polling is False
    assert sun.disabled_by is None
    assert sun.reason is None
    assert sun.error_reason_translation_key is None
    assert sun.error_reason_translation_placeholders is None
    assert sun.num_subentries == 0


def test_get_entry_subentries(websocket_client: WebsocketClient) -> None:
    """Tests the `"type": "config_entries/subentries/list"` websocket command."""
    # Currently not able to test as no entries with subentries available
    # Get the sun entry
    sun = websocket_client.get_config_entries()[0]
    assert sun

    # Get subentries for sun (empty tuple)
    assert not websocket_client.get_entry_subentries(sun.entry_id)


def test_delete_entry_subentry(websocket_client: WebsocketClient) -> None:
    """Tests the `"type": "config_entries/subentries/delete"` websocket command."""
    # Currently not able to test as no entries with subentries available. Send invalid parameters and handle that error
    try:
        websocket_client.delete_entry_subentry("", "")
    except RequestError as error:
        assert (
            error.__str__()
            == "An error occurred while making the request to 'Config entry not found' with data: 'not_found'"
        )


def test_trigger_service(cached_client: Client) -> None:
    """Tests the `POST /api/services/<domain>/<service>` endpoint."""
    notify = cached_client.get_domain("notify")
    assert notify is not None
    resp = notify.persistent_notification(
        message="Your API Test Suite just said hello!",
        title="Test Suite Notifcation",
    )
    logging.info(resp)
    assert isinstance(resp, tuple)


async def test_async_trigger_service(async_cached_client: Client) -> None:
    """Tests the `POST /api/services/<domain>/<service>` endpoint."""
    notify = await async_cached_client.async_get_domain("notify")
    assert notify is not None
    resp = await notify.persistent_notification(
        message="Your API Test Suite just said hello!",
        title="Test Suite Notifcation (Async)",
    )
    assert isinstance(resp, tuple)


def test_websocket_trigger_service(websocket_client: WebsocketClient) -> None:
    """Tests the `"type": "trigger_service"` websocket command."""
    notify = websocket_client.get_domain("notify")
    assert notify is not None
    resp = notify.persistent_notification(
        message="Your API Test Suite just said hello!", title="Test Suite Notifcation"
    )
    # Websocket API doesnt return changed states so we check for None
    assert resp is None


async def test_async_websocket_trigger_service(
    async_websocket_client: WebsocketClient,
) -> None:
    """Tests the `"type": "trigger_service"` websocket command."""
    notify = await async_websocket_client.async_get_domain("notify")
    assert notify is not None
    resp = await notify.persistent_notification(
        message="Your API Test Suite just said hello!", title="Test Suite Notifcation"
    )
    # Websocket API doesnt return changed states so we check for None
    assert resp is None


def test_websocket_trigger_service_with_entity_id(
    websocket_client: WebsocketClient,
) -> None:
    """Tests websocket trigger_service with an entity_id target."""
    state_before = websocket_client.get_state(entity_id="sun.sun")
    websocket_client.trigger_service(
        "homeassistant",
        "update_entity",
        entity_id="sun.sun",
    )
    state_after = websocket_client.get_state(entity_id="sun.sun")
    # update_entity refreshes the entity; state should remain valid
    assert state_after.entity_id == state_before.entity_id
    assert state_after.state in {"above_horizon", "below_horizon"}


def test_trigger_service_with_response(cached_client: Client) -> None:
    """Tests the `POST /api/services/<domain>/<service>?return_response` endpoint."""
    weather = cached_client.get_domain("weather")
    assert weather is not None
    changed_states, data = weather.get_forecasts(
        entity_id="weather.forecast_home",
        type="hourly",
    )
    assert data is not None


async def test_async_trigger_service_with_response(async_cached_client: Client) -> None:
    """Tests the `POST /api/services/<domain>/<service>?return_response` endpoint."""
    weather = await async_cached_client.async_get_domain("weather")
    assert weather is not None
    changed_states, data = await weather.get_forecasts(
        entity_id="weather.forecast_home",
        type="hourly",
    )
    assert data is not None


def test_websocket_trigger_service_with_response(
    websocket_client: WebsocketClient,
) -> None:
    """Tests the `"type": "trigger_service_with_response"` websocket command."""
    weather = websocket_client.get_domain("weather")
    assert weather is not None
    data = weather.get_forecasts(
        entity_id="weather.forecast_home",
        type="hourly",
    )
    # Websocket API doesnt return changed states so we check data is not None because we expect a response
    assert data is not None


async def test_async_websocket_trigger_service_with_response(
    async_websocket_client: WebsocketClient,
) -> None:
    """Tests the `"type": "trigger_service_with_response"` websocket command."""
    weather = await async_websocket_client.async_get_domain("weather")
    assert weather is not None
    data = weather.get_forecasts(
        entity_id="weather.forecast_home",
        type="hourly",
    )
    # Websocket API doesnt return changed states so we check data is not None because we expect a response
    assert data is not None


def test_get_states(cached_client: Client) -> None:
    """Tests the `GET /api/states` endpoint."""
    states = cached_client.get_states()
    for state in states:
        assert isinstance(state, State)


async def test_async_get_states(async_cached_client: Client) -> None:
    """Tests the `GET /api/states` endpoint."""
    states = await async_cached_client.async_get_states()
    for state in states:
        assert isinstance(state, State)


def test_websocket_get_states(websocket_client: WebsocketClient) -> None:
    """Tests the `"type": "get_states"` websocket command."""
    states = websocket_client.get_states()
    for state in states:
        assert isinstance(state, State)


async def test_async_websocket_get_states(
    async_websocket_client: WebsocketClient,
) -> None:
    """Tests the `"type": "get_states"` websocket command."""
    states = await async_websocket_client.async_get_states()
    for state in states:
        assert isinstance(state, State)


def test_get_state(cached_client: Client) -> None:
    """Tests the `GET /api/states/<entity_id>` endpoint."""
    state = cached_client.get_state(entity_id="sun.sun")
    assert state.state in {"above_horizon", "below_horizon"}


async def test_async_get_state(async_cached_client: Client) -> None:
    """Tests the `GET /api/states/<entity_id>` endpoint."""
    state = await async_cached_client.async_get_state(entity_id="sun.sun")
    assert state.state in {"above_horizon", "below_horizon"}


def test_set_state(cached_client: Client) -> None:
    """Tests the `POST /api/states/<entity_id>` endpoint."""
    state = cached_client.set_state(
        State(state="beyond_our_solar_system", entity_id="sun.red_sun")
    )
    assert state.state == "beyond_our_solar_system"


async def test_async_set_state(async_cached_client: Client) -> None:
    """Tests the `POST /api/states/<entity_id>` endpoint."""
    state = await async_cached_client.async_set_state(
        State(state="beyond_our_solar_system", entity_id="sun.red_sun")
    )
    assert state.state == "beyond_our_solar_system"


def test_get_events(cached_client: Client) -> None:
    """Tests the `GET /api/events` endpoint."""
    events = cached_client.get_events()
    for event in events:
        assert isinstance(event, Event)


async def test_async_get_events(async_cached_client: Client) -> None:
    """Tests the `GET /api/events` endpoint."""
    events = await async_cached_client.async_get_events()
    for event in events:
        assert isinstance(event, Event)


def test_fire_event(cached_client: Client) -> None:
    """Tests the `POST /api/events/<event_type>` endpoint."""
    data = cached_client.fire_event("my_new_event", parameter="123")
    assert data == "Event my_new_event fired."


async def test_async_fire_event(async_cached_client: Client) -> None:
    """Tests the `POST /api/events/<event_type>` endpoint."""
    data = await async_cached_client.async_fire_event("my_new_event", parameter="123")
    assert data == "Event my_new_event fired."


def test_get_components(cached_client: Client) -> None:
    """Tests the `GET /api/components` endpoint."""
    components = cached_client.get_components()
    assert "person" in components


async def test_async_get_components(async_cached_client: Client) -> None:
    """Tests the `GET /api/components` endpoint."""
    components = await async_cached_client.async_get_components()
    assert "person" in components
