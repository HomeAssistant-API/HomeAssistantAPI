"""Module that tests model methods."""

import copy
from datetime import UTC
from datetime import datetime

import pytest

from homeassistant_api import AsyncClient
from homeassistant_api import Client
from homeassistant_api import Domain
from homeassistant_api.models.domains import BaseDomain
from homeassistant_api.models.entity import BaseGroup
from homeassistant_api.models.events import Event
from homeassistant_api.models.history import History
from homeassistant_api.models.states import State


def test_entity_get_entity(cached_client: Client) -> None:
    person_test_suite = cached_client.get_entity(group_id="person", slug="test_user")
    assert person_test_suite is not None
    state = copy.copy(person_test_suite.state)
    person = person_test_suite.group
    assert state.state == person_test_suite.get_state().state
    assert getattr(person, person_test_suite.slug) == person_test_suite
    with pytest.raises(AttributeError):
        assert person.thispersondoesnotexistplease


async def test_async_entity_get_entity(async_cached_client: AsyncClient) -> None:
    person_test_suite = await async_cached_client.get_entity(
        group_id="person",
        slug="test_user",
    )
    assert person_test_suite is not None
    state = copy.copy(person_test_suite.state)
    person = person_test_suite.group
    assert state.state == (await person_test_suite.get_state()).state
    assert getattr(person, person_test_suite.slug) == person_test_suite
    with pytest.raises(AttributeError):
        assert person.thispersondoesnotexistplease


def test_entity_update_state(cached_client: Client) -> None:
    entity = cached_client.get_entity(group_id="sun", slug="red_sun")
    assert entity is not None
    entity.state.state = "In the palm of your hand."
    new_state = entity.update_state()
    assert new_state is not None
    assert new_state.state == "In the palm of your hand."


async def test_async_entity_update_state(async_cached_client: AsyncClient) -> None:
    entity = await async_cached_client.get_entity(group_id="sun", slug="red_sun")
    assert entity is not None
    entity.state.state = "In the palm of my hand."
    new_state = await entity.update_state()
    assert new_state is not None
    assert new_state.state == "In the palm of my hand."


def test_get_event(cached_client: Client) -> None:
    event = cached_client.get_event("my_favorite_candy_is_mike_and_ikes")
    assert event is None


async def test_async_get_event(async_cached_client: AsyncClient) -> None:
    event = await async_cached_client.get_event("my_favorite_candy_is_mike_and_ikes")
    assert event is None


def test_fire_event(cached_client: Client) -> None:
    event = cached_client.get_event("core_config_updated")
    assert event is not None
    assert event.fire() == "Event core_config_updated fired."


async def test_async_fire_event(async_cached_client: AsyncClient) -> None:
    event = await async_cached_client.get_event("core_config_updated")
    assert event is not None
    assert await event.fire() == "Event core_config_updated fired."


def test_get_domain(cached_client: Client) -> None:
    notify = cached_client.get_domain("notify")
    assert notify is not None
    assert notify.domain_id == "notify"
    with pytest.raises(AttributeError):
        assert notify.thisservicedoesnotexistplease


async def test_async_get_domains(async_cached_client: AsyncClient) -> None:
    notify = await async_cached_client.get_domain("notify")
    assert notify is not None
    assert notify.domain_id == "notify"
    with pytest.raises(AttributeError):
        assert notify.thisservicedoesnotexistplease


def test_entity_get_history(cached_client: Client) -> None:
    entity = cached_client.get_entity(group_id="sun", slug="sun")
    assert entity is not None
    history = entity.get_history()
    assert history is not None
    for state in history.states:
        assert isinstance(state, State)


async def test_async_entity_get_history(async_cached_client: AsyncClient) -> None:
    entity = await async_cached_client.get_entity(group_id="sun", slug="sun")
    assert entity is not None
    history = await entity.get_history()
    assert history is not None
    for state in history.states:
        assert isinstance(state, State)


def test_entity_get_history_none(cached_client: Client) -> None:
    entity = cached_client.get_entity(group_id="sun", slug="red_sun")
    assert entity is not None
    history = entity.get_history(
        start_timestamp=datetime(2015, 1, 1, tzinfo=UTC),
        end_timestamp=datetime(2020, 1, 1, tzinfo=UTC),
    )
    assert history is None


def test_event_from_json_raises() -> None:
    """Tests that Event.from_json raises NotImplementedError directing to from_json_with_client."""
    with pytest.raises(NotImplementedError, match="does not support `from_json\\(\\)`"):
        Event.from_json({})


def test_domain_from_json_with_client_missing_keys(cached_client: Client) -> None:
    """Tests that Domain.from_json_with_client raises ValueError when keys are missing."""
    with pytest.raises(ValueError, match="Missing services or domain"):
        Domain.from_json_with_client({"foo": "bar"}, cached_client)


async def test_async_entity_get_history_none(async_cached_client: AsyncClient) -> None:
    entity = await async_cached_client.get_entity(group_id="sun", slug="red_sun")
    assert entity is not None
    history = await entity.get_history(
        start_timestamp=datetime(2015, 1, 1, tzinfo=UTC),
        end_timestamp=datetime(2020, 1, 1, tzinfo=UTC),
    )
    assert history is None


# --- BaseGroup: __getattr__ for nonexistent key ---


def test_base_group_getattr_nonexistent() -> None:
    """Tests that BaseGroup.__getattr__ raises AttributeError for unknown attributes."""
    group = BaseGroup(group_id="test")
    assert group.get_entity("nonexistent") is None
    with pytest.raises(AttributeError):
        _ = group.nonexistent_entity


def test_base_group_add_entity_not_implemented() -> None:
    """Tests that BaseGroup._add_entity raises NotImplementedError."""
    group = BaseGroup(group_id="test")
    with pytest.raises(NotImplementedError):
        group._add_entity("slug", State(state="on", entity_id="test.slug"))


# --- BaseDomain: _add_service not implemented ---


def test_base_domain_add_service_not_implemented() -> None:
    """Tests that BaseDomain._add_service raises NotImplementedError."""
    domain = BaseDomain(domain_id="test")
    with pytest.raises(NotImplementedError):
        domain._add_service("svc")


def test_base_domain_from_json_invalid_services_type(cached_client: Client) -> None:
    """Tests that Domain.from_json_with_client raises TypeError when services is not a dict."""
    with pytest.raises(TypeError, match="Expected dict for services"):
        Domain.from_json_with_client(
            {"domain": "test", "services": "not_a_dict"},
            cached_client,
        )


# --- History: repr and entity_id ---


def test_history_repr() -> None:
    """Tests that History has a meaningful repr with entity_id."""
    states = (
        State(state="on", entity_id="light.kitchen"),
        State(state="off", entity_id="light.kitchen"),
    )
    history = History(states=states)
    assert history.entity_id == "light.kitchen"
    assert "light.kitchen" in repr(history)


def test_history_entity_id_from_states() -> None:
    """Tests that History.entity_id is derived from the states' entity_ids."""
    states = (
        State(state="on", entity_id="light.kitchen"),
        State(state="off", entity_id="light.kitchen"),
    )
    history = History(states=states)
    assert history.entity_id == "light.kitchen"


# --- Domain: service access via attribute ---


def test_domain_service_attribute_access(cached_client: Client) -> None:
    """Tests that Domain services are accessible as attributes."""
    notify = cached_client.get_domain("notify")
    assert notify is not None
    svc = notify.get_service("persistent_notification")
    assert svc is not None
    assert notify.persistent_notification == svc
