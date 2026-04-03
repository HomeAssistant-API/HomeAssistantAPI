"""Module for all interaction with Home Assistant."""

from __future__ import annotations

import json
import logging
from http import HTTPMethod
from posixpath import join
from typing import TYPE_CHECKING
from typing import Any

from requests import Session
from requests import Timeout
from requests_cache import CachedSession
from typing_extensions import Self

from homeassistant_api.baseclient import BaseClient
from homeassistant_api.errors import BadTemplateError
from homeassistant_api.errors import RequestError
from homeassistant_api.errors import RequestTimeoutError
from homeassistant_api.models import Domain
from homeassistant_api.models import Entity
from homeassistant_api.models import Event
from homeassistant_api.models import Group
from homeassistant_api.models import History
from homeassistant_api.models import LogbookEntry
from homeassistant_api.models import State
from homeassistant_api.processing import ResponseType
from homeassistant_api.processing import process_response
from homeassistant_api.utils import prepare_entity_id

if TYPE_CHECKING:
    from collections.abc import Generator
    from datetime import datetime
    from types import TracebackType

logger = logging.getLogger(__name__)


class Client(BaseClient):
    """
    The sync client for interacting with Home Assistant via the REST API.

    :param api_url: The location of the api endpoint. e.g. :code:`http://localhost:8123/api` Required.
    :param token: The refresh or long lived access token to authenticate your requests. Required.
    :param session: A custom :py:class:`requests_cache.CachedSession` or :py:class:`requests.Session` instance. Optional.
    :param use_cache: Enable the default in-memory request cache (300s expiry). Ignored if :code:`session` is provided. Default :code:`False`.
    :param verify_ssl: Whether to verify SSL certificates. Default :code:`True`.
    :param global_request_kwargs: Kwargs to pass to :func:`requests.request`. Optional.
    """  # pylint: disable=line-too-long

    _session: CachedSession | Session

    def __init__(
        self,
        *args: Any,
        session: CachedSession | None = None,
        use_cache: bool = False,
        verify_ssl: bool = True,
        **kwargs: Any,
    ) -> None:
        BaseClient.__init__(self, *args, **kwargs)
        self.global_request_kwargs["verify"] = verify_ssl
        if session:
            self._session = session
        elif use_cache:
            self._session = CachedSession(
                cache_name="default_cache",
                backend="memory",
                expire_after=300,
            )
        else:
            self._session = Session()

    def __enter__(self) -> Self:
        logger.debug("Entering cached requests session %r.", self._session)
        self._session.__enter__()
        self.check_api_running()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        logger.debug("Exiting requests session %r", self._session)
        self._session.close()

    def request(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        method: HTTPMethod = HTTPMethod.GET,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> Any:
        """Base method for making requests to the api"""
        path = self.endpoint(path)
        if params:
            path = f"{path}?{self.construct_params(params)}"
        if self.global_request_kwargs is not None:
            kwargs.update(self.global_request_kwargs)
        try:
            logger.debug(f"{method} request to {path}")
            resp = self._session.request(
                method,
                path,
                headers=self.prepare_headers(headers),
                **kwargs,
            )
        except Timeout as err:
            msg = f"Home Assistant did not respond in time (timeout: {kwargs.get('timeout', 300)} sec)"
            raise RequestTimeoutError(msg, url=path) from err
        return self.response_logic(response=resp)

    def _dict_request(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        data = self.request(*args, **kwargs)
        if not isinstance(data, dict):
            msg = f"Expected dict response, got {type(data).__name__}"
            raise TypeError(msg)
        return data

    def _list_request(self, *args: Any, **kwargs: Any) -> list:
        data = self.request(*args, **kwargs)
        if not isinstance(data, list):
            msg = f"Expected list response, got {type(data).__name__}"
            raise TypeError(msg)
        return data

    def _str_request(self, *args: Any, **kwargs: Any) -> str:
        data = self.request(*args, **kwargs)
        if not isinstance(data, str):
            msg = f"Expected str response, got {type(data).__name__}"
            raise TypeError(msg)
        return data

    @staticmethod
    def response_logic(response: ResponseType) -> Any:
        """Processes responses from the API and formats them"""
        return process_response(response)

    # API information methods
    def get_error_log(self) -> str:
        """
        Returns the server error log as a string.
        :code:`GET /api/error_log`
        """
        return self._str_request("error_log")

    def get_config(self) -> dict[str, Any]:
        """
        Returns the configuration of Home Assistant.
        :code:`GET /api/config`
        """
        return self._dict_request("config")

    def get_logbook_entries(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> Generator[LogbookEntry, None, None]:
        """
        Returns a list of logbook entries from Home Assistant.
        :code:`GET /api/logbook/<timestamp>`
        """
        params, url = self.prepare_get_logbook_entry_params(*args, **kwargs)
        data = self._list_request(url, params=params)
        for entry in data:
            yield LogbookEntry.model_validate(entry)

    def get_entity_histories(
        self,
        entities: tuple[Entity, ...] | None = None,
        start_timestamp: datetime | None = None,
        # Defaults to 1 day before. https://developers.home-assistant.io/docs/api/rest/
        end_timestamp: datetime | None = None,
        *,
        significant_changes_only: bool = False,
    ) -> Generator[History, None, None]:
        """
        Yields entity state histories. See docs on the :py:class:`History` model.
        :code:`GET /api/history/period/<timestamp>`
        """
        params, url = self.prepare_get_entity_histories_params(
            entities=entities,
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
            significant_changes_only=significant_changes_only,
        )
        data = self._list_request(url, params=params)
        for states in data:
            yield History.model_validate({"states": states})

    def get_rendered_template(self, template: str) -> str:
        """
        Renders a Jinja2 template with Home Assistant context data.
        See https://www.home-assistant.io/docs/configuration/templating.
        :code:`POST /api/template`
        """
        try:
            return self._str_request(
                "template",
                json={"template": template},
                method=HTTPMethod.POST,
            )
        except RequestError as err:
            msg = (
                "Your template is invalid. "
                "Try debugging it in the developer tools page of Home Assistant."
            )
            raise BadTemplateError(msg) from err

    # API check methods
    def check_api_config(self) -> bool:
        """
        Asks Home Assistant to validate its configuration file.
        :code:`POST /api/config/core/check_config`
        """
        res = self._dict_request("config/core/check_config", method=HTTPMethod.POST)
        return {"valid": True, "invalid": False}.get(res["result"], False)

    def check_api_running(self) -> bool:
        """
        Asks Home Assistant if it is running.
        :code:`GET /api/`
        """
        res = self._dict_request("")
        return res.get("message") == "API running."

    # Entity methods
    def get_entities(self) -> dict[str, Group]:
        """
        Fetches all entities from the api and returns them as a dictionary of :py:class:`Group`'s.
        :code:`GET /api/states`
        """
        entities: dict[str, Group] = {}
        for state in self.get_states():
            group_id, entity_slug = state.entity_id.split(".")
            if group_id not in entities:
                entities[group_id] = Group(
                    group_id=group_id,
                    client=self,
                )
            entities[group_id]._add_entity(entity_slug, state)  # noqa: SLF001
        return entities

    def get_entity(
        self,
        group_id: str | None = None,
        slug: str | None = None,
        entity_id: str | None = None,
    ) -> Entity | None:
        """
        Returns an :py:class:`Entity` model for an :code:`entity_id`.
        :code:`GET /api/states/<entity_id>`
        """
        if group_id is not None and slug is not None:
            state = self.get_state(group_id=group_id, slug=slug)
        elif entity_id is not None:
            state = self.get_state(entity_id=entity_id)
        else:
            help_msg = (
                "Use keyword arguments to pass entity_id. "
                "Or you can pass the group_id and slug instead"
            )
            msg = f"Neither group_id and slug or entity_id provided. {help_msg}"
            raise ValueError(msg)
        split_group_id, split_slug = state.entity_id.split(".")
        group = Group(
            group_id=split_group_id,
            client=self,
        )
        group._add_entity(split_slug, state)  # noqa: SLF001
        return group.get_entity(split_slug)

    # Services and domain methods
    def get_domains(self) -> dict[str, Domain]:
        """
        Fetches all service :py:class:`Domain`'s from the API.
        :code:`GET /api/services`
        """
        data = self._list_request("services")
        domains = (Domain.from_json_with_client(json, client=self) for json in data)
        return {domain.domain_id: domain for domain in domains}

    def get_domain(self, domain_id: str) -> Domain | None:
        """
        Fetches all :py:class:`Service`'s under a particular service :py:class:`Domain`.
        Uses cached data from :py:meth:`get_domains` if available.
        """
        return self.get_domains().get(domain_id)

    def trigger_service(
        self,
        domain: str,
        service: str,
        **service_data: Any,
    ) -> tuple[State, ...]:
        """
        Tells Home Assistant to trigger a service, returns all states changed while in the process of being called.
        :code:`POST /api/services/<domain>/<service>`
        """
        data = self._list_request(
            join("services", domain, service),
            method=HTTPMethod.POST,
            json=service_data,
        )
        return tuple(map(State.from_json, data))

    def trigger_service_with_response(
        self,
        domain: str,
        service: str,
        **service_data: Any,
    ) -> tuple[tuple[State, ...], dict[str, Any]]:
        """
        Tells Home Assistant to trigger a service, returns the response from the service call.
        :code:`POST /api/services/<domain>/<service>`

        Returns a list of the states changed and the response from the service call.
        """
        data = self._dict_request(
            join("services", domain, service) + "?return_response",
            method=HTTPMethod.POST,
            json=service_data,
        )
        states = tuple(
            map(
                State.from_json,
                data.get("changed_states", []),
            ),
        )
        return states, data.get("service_response", {})

    # EntityState methods
    def get_state(  # pylint: disable=duplicate-code
        self,
        *,
        entity_id: str | None = None,
        group_id: str | None = None,
        slug: str | None = None,
    ) -> State:
        """
        Fetches the state of the entity specified.
        :code:`GET /api/states/<entity_id>`
        """
        entity_id = prepare_entity_id(
            group_id=group_id,
            slug=slug,
            entity_id=entity_id,
        )
        data = self._dict_request(join("states", entity_id))
        return State.from_json(data)

    def set_state(  # pylint: disable=duplicate-code
        self,
        state: State,
    ) -> State:
        """
        This method sets the representation of a device within Home Assistant and will not communicate with the actual device.
        To communicate with the device, use :py:meth:`Service.trigger`.
        :code:`POST /api/states/<entity_id>`
        """
        data = self._dict_request(
            join("states", state.entity_id),
            method=HTTPMethod.POST,
            json=json.loads(state.model_dump_json()),
        )
        return State.from_json(data)

    def get_states(self) -> tuple[State, ...]:
        """
        Gets the states of all entities within Home Assistant.
        :code:`GET /api/states`
        """
        data = self._list_request("states")
        states = map(State.from_json, data)
        return tuple(states)

    # Event methods
    def get_events(self) -> tuple[Event, ...]:
        """
        Gets the Events that happen within Home Assistant.
        :code:`GET /api/events`
        """
        data = self._list_request("events")
        return tuple(Event.from_json_with_client(json, client=self) for json in data)

    def get_event(self, name: str) -> Event | None:
        """
        Gets the :py:class:`Event` with the specified name if it has at least one listener.
        Uses cached data from :py:meth:`get_events` if available.
        """
        for event in self.get_events():
            if event.event == name.strip().lower():
                return event
        return None

    def fire_event(self, event_type: str, **event_data: Any) -> str:
        """
        Fires a given event_type within Home Assistant.
        `POST /api/events/<event_type>`
        """
        data = self._dict_request(
            join("events", event_type),
            method=HTTPMethod.POST,
            json=event_data,
        )
        return data.get("message", "No message provided")

    def get_components(self) -> tuple[str, ...]:
        """
        Returns a tuple of all registered components.
        :code:`GET /api/components`
        """
        return tuple(self._list_request("components"))
