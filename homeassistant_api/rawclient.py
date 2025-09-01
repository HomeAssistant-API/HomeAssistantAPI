"""Module for all interaction with homeassistant."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from posixpath import join
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Generator,
    List,
    Literal,
    Optional,
    Tuple,
    Union,
    cast,
)

import requests
import requests_cache

from homeassistant_api.errors import BadTemplateError, RequestError, RequestTimeoutError
from homeassistant_api.models import (
    Domain,
    Entity,
    Event,
    Group,
    History,
    LogbookEntry,
    State,
)
from homeassistant_api.processing import Processing, ResponseType
from homeassistant_api.rawbaseclient import RawBaseClient
from homeassistant_api.utils import JSONType, prepare_entity_id

if TYPE_CHECKING:
    from homeassistant_api import Client
else:
    Client = None  # pylint: disable=invalid-name


logger = logging.getLogger(__name__)


class RawClient(RawBaseClient):
    """
    The base object for interacting with Homeassistant via the REST API.

    :param api_url: The location of the api endpoint. e.g. :code:`http://localhost:8123/api` Required.
    :param token: The refresh or long lived access token to authenticate your requests. Required.
    :param global_request_kwargs: Kwargs to pass to :func:`requests.request` or :meth:`aiohttp.ClientSession.request`. Optional.
    """  # pylint: disable=line-too-long

    cache_session: Union[requests_cache.CachedSession, requests.Session]

    def __init__(
        self,
        *args,
        cache_session: Union[
            requests_cache.CachedSession,
            Literal[False],
            Literal[None],
        ] = None,  # Explicitly disable cache with cache_session=False
        verify_ssl: bool = True,
        **kwargs,
    ):
        RawBaseClient.__init__(self, *args, **kwargs)
        self.global_request_kwargs["verify"] = verify_ssl
        if cache_session is False:
            self.cache_session = requests.Session()
        elif cache_session is None:
            self.cache_session = requests_cache.CachedSession(
                cache_name="default_cache",
                backend="memory",
                expire_after=300,
            )
        else:
            self.cache_session = cache_session

    def __enter__(self) -> "RawClient":
        logger.debug("Entering cached requests session %r.", self.cache_session)
        self.cache_session.__enter__()
        self.check_api_running()
        return self

    def __exit__(self, _, __, ___) -> None:
        logger.debug("Exiting requests session %r", self.cache_session)
        self.cache_session.close()

    def request(
        self,
        path: str,
        *,
        params: str = "",  # should be a string of query parameters from construct_params()
        method="GET",
        headers: Optional[Dict[str, str]] = None,
        decode_bytes: bool = True,
        **kwargs,
    ) -> Any:
        """Base method for making requests to the api"""
        try:
            if self.global_request_kwargs is not None:
                kwargs.update(self.global_request_kwargs)
            logger.debug("%s request to %s", method, self.endpoint(path))
            resp = self.cache_session.request(
                method,
                self.endpoint(path) + f"?{params}" * bool(params),
                headers=self.prepare_headers(headers),
                **kwargs,
            )
        except requests.exceptions.Timeout as err:
            raise RequestTimeoutError(
                f'Home Assistant did not respond in time (timeout: {kwargs.get("timeout", 300)} sec)',
                url=self.endpoint(path) + f"?{params}" * bool(params),
            ) from err
        return self.response_logic(response=resp, decode_bytes=decode_bytes)

    @classmethod
    def response_logic(cls, response: ResponseType, decode_bytes: bool = True) -> Any:
        """Processes responses from the API and formats them"""
        return Processing(response=response, decode_bytes=decode_bytes).process()

    # API information methods
    def get_error_log(self) -> str:
        """
        Returns the server error log as a string.
        :code:`GET /api/error_log`
        """
        return cast(str, self.request("error_log"))

    def get_config(self) -> dict[str, JSONType]:
        """
        Returns the yaml configuration of homeassistant.
        :code:`GET /api/config`
        """
        return cast(dict[str, JSONType], self.request("config"))

    def get_logbook_entries(
        self,
        *args,
        **kwargs,
    ) -> Generator[LogbookEntry, None, None]:
        """
        Returns a list of logbook entries from homeassistant.
        :code:`GET /api/logbook/<timestamp>`
        """
        params, url = self.prepare_get_logbook_entry_params(*args, **kwargs)
        data = self.request(
            url, params=self.construct_params(cast(Dict[str, Optional[str]], params))
        )
        for entry in data:
            yield LogbookEntry.model_validate(entry)

    def get_entity_histories(
        self,
        entities: Optional[Tuple[Entity, ...]] = None,
        start_timestamp: Optional[datetime] = None,
        # Defaults to 1 day before. https://developers.home-assistant.io/docs/api/rest/
        end_timestamp: Optional[datetime] = None,
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
        data = self.request(
            url,
            params=self.construct_params(params),
        )
        for states in data:
            yield History.model_validate({"states": states})

    def get_rendered_template(self, template: str) -> str:
        """
        Renders a Jinja2 template with Home Assistant context data.
        See https://www.home-assistant.io/docs/configuration/templating.
        :code:`POST /api/template`
        """
        try:
            return cast(
                str,
                self.request(
                    "template",
                    json=dict(template=template),
                    method="POST",
                ),
            )
        except RequestError as err:
            raise BadTemplateError(
                "Your template is invalid. "
                "Try debugging it in the developer tools page of homeassistant."
            ) from err

    # API check methods
    def check_api_config(self) -> bool:
        """
        Asks Home Assistant to validate its configuration file.
        :code:`POST /api/config/core/check_config`
        """
        res = cast(
            dict[str, str], self.request("config/core/check_config", method="POST")
        )
        valid = {"valid": True, "invalid": False}.get(res["result"], False)
        return valid

    def check_api_running(self) -> bool:
        """
        Asks Home Assistant if it is running.
        :code:`GET /api/`
        """
        res = self.request("")
        return cast(dict[str, JSONType], res).get("message") == "API running."

    # Entity methods
    def get_entities(self) -> Dict[str, Group]:
        """
        Fetches all entities from the api and returns them as a dictionary of :py:class:`Group`'s.
        :code:`GET /api/states`
        """
        entities: Dict[str, Group] = {}
        for state in self.get_states():
            group_id, entity_slug = state.entity_id.split(".")
            if group_id not in entities:
                entities[group_id] = Group(
                    group_id=group_id,
                    _client=self,  # type: ignore[arg-type]
                )
            entities[group_id]._add_entity(entity_slug, state)
        return entities

    def get_entity(
        self,
        group_id: Optional[str] = None,
        slug: Optional[str] = None,
        entity_id: Optional[str] = None,
    ) -> Optional[Entity]:
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
            raise ValueError(
                f"Neither group_id and slug or entity_id provided. {help_msg}"
            )
        split_group_id, split_slug = state.entity_id.split(".")
        group = Group(
            group_id=split_group_id,
            _client=self,  # type: ignore[arg-type]
        )
        group._add_entity(split_slug, state)
        return group.get_entity(split_slug)

    # Services and domain methods
    def get_domains(self) -> Dict[str, Domain]:
        """
        Fetches all :py:class:`Service` 's from the API.
        :code:`GET /api/services`
        """
        data = self.request("services")
        domains = map(
            lambda json: Domain.from_json(json, client=cast(Client, self)),
            cast(Tuple[dict[str, JSONType], ...], data),
        )
        return {domain.domain_id: domain for domain in domains}

    def get_domain(self, domain_id: str) -> Optional[Domain]:
        """
        Fetches all :py:class:`Service`'s under a particular service :py:class:`Domain`.
        Uses cached data from :py:meth:`get_domains` if available.
        """
        return self.get_domains().get(domain_id)

    def trigger_service(
        self,
        domain: str,
        service: str,
        **service_data,
    ) -> Tuple[State, ...]:
        """
        Tells Home Assistant to trigger a service, returns all states changed while in the process of being called.
        :code:`POST /api/services/<domain>/<service>`
        """
        data = self.request(
            join("services", domain, service),
            method="POST",
            json=service_data,
        )
        return tuple(map(State.from_json, cast(List[dict[str, JSONType]], data)))

    def trigger_service_with_response(
        self,
        domain: str,
        service: str,
        **service_data,
    ) -> tuple[tuple[State, ...], dict[str, JSONType]]:
        """
        Tells Home Assistant to trigger a service, returns the response from the service call.
        :code:`POST /api/services/<domain>/<service>`

        Returns a list of the states changed and the response from the service call.
        """
        data = cast(
            dict[str, dict[str, JSONType]],
            self.request(
                join("services", domain, service) + "?return_response",
                method="POST",
                json=service_data,
            ),
        )
        states = tuple(
            map(
                State.from_json,
                cast(List[Dict[Any, Any]], data.get("changed_states", [])),
            )
        )
        return states, data.get("service_response", {})

    # EntityState methods
    def get_state(  # pylint: disable=duplicate-code
        self,
        *,
        entity_id: Optional[str] = None,
        group_id: Optional[str] = None,
        slug: Optional[str] = None,
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
        data = self.request(join("states", entity_id))
        return State.from_json(cast(dict[str, JSONType], data))

    def set_state(  # pylint: disable=duplicate-code
        self,
        state: State,
    ) -> State:
        """
        This method sets the representation of a device within Home Assistant and will not communicate with the actual device.
        To communicate with the device, use :py:meth:`Service.trigger` or :py:meth:`Service.async_trigger`.
        :code:`POST /api/states/<entity_id>`
        """
        data = self.request(
            join("states", state.entity_id),
            method="POST",
            json=json.loads(state.model_dump_json()),
        )
        return State.from_json(cast(dict[str, JSONType], data))

    def get_states(self) -> Tuple[State, ...]:
        """
        Gets the states of all entities within homeassistant.
        :code:`GET /api/states`
        """
        data = self.request("states")
        states = map(State.from_json, cast(List[dict[str, JSONType]], data))
        return tuple(states)

    # Event methods
    def get_events(self) -> Tuple[Event, ...]:
        """
        Gets the Events that happen within homeassistant
        :code:`GET /api/events`
        """
        data = self.request("events")
        return tuple(
            map(
                lambda json: Event.from_json(json, client=cast(Client, self)),
                cast(List[dict[str, JSONType]], data),
            )
        )

    def get_event(self, name: str) -> Optional[Event]:
        """
        Gets the :py:class:`Event` with the specified name if it has at least one listener.
        Uses cached data from :py:meth:`get_events` if available.
        """
        for event in self.get_events():
            if event.event == name.strip().lower():
                return event
        return None

    def fire_event(self, event_type: str, **event_data) -> Optional[str]:
        """
        Fires a given event_type within homeassistant. Must be an existing event_type.
        `POST /api/events/<event_type>`
        """
        data = self.request(
            join("events", event_type),
            method="POST",
            json=event_data,
        )
        return cast(dict[str, str], data).get("message")

    def get_components(self) -> Tuple[str, ...]:
        """
        Returns a tuple of all registered components.
        :code:`GET /api/components`
        """
        return tuple(self.request("components"))
