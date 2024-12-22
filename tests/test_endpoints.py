"""Module for making sure endpoints that should succeed, do indeed succeed."""

from datetime import datetime

from homeassistant_api import Client
from homeassistant_api.models.events import Event
from homeassistant_api.models.states import State


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
        filter_entities="sun.sun",
        start_timestamp=datetime(2020, 1, 1),
        end_timestamp=datetime.now(),
    ):
        assert entry


async def test_async_get_logbook_entries(async_cached_client: Client) -> None:
    """Tests the `GET /api/logbook/<timestamp>` endpoint."""
    async for entry in async_cached_client.async_get_logbook_entries():
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
    for history in cached_client.get_entity_histories(
        (sun,),
        end_timestamp=datetime(2023, 1, 1),
        start_timestamp=datetime(2020, 1, 1),
        significant_changes_only=True,
    ):
        for state in history.states:
            assert isinstance(state, State)


async def test_async_get_entity_histories(async_cached_client: Client) -> None:
    """Tests the `GET /api/history/period/<timestamp>` endpoint."""
    sun = await async_cached_client.async_get_entity(entity_id="sun.sun")
    assert sun is not None
    async for history in async_cached_client.async_get_entity_histories((sun,)):
        for state in history.states:
            assert isinstance(state, State)


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


def test_get_domains(cached_client: Client) -> None:
    """Tests the `GET /api/services` endpoint."""
    domains = cached_client.get_domains()
    assert "homeassistant" in domains


async def test_async_get_domains(async_cached_client: Client) -> None:
    """Tests the `GET /api/services` endpoint."""
    domains = await async_cached_client.async_get_domains()
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


def test_trigger_service(cached_client: Client) -> None:
    """Tests the `POST /api/services/<domain>/<service>` endpoint."""
    notify = cached_client.get_domain("notify")
    assert notify is not None
    resp = notify.persistent_notification(
        message="Your API Test Suite just said hello!",
        title="Test Suite Notifcation",
    )
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
        return_response=True,
    )
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
