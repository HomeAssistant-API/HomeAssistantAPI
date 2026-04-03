"""Module for interacting with Home Assistant asynchronously."""

from __future__ import annotations

import asyncio
import json
import logging
from http import HTTPMethod
from posixpath import join
from typing import TYPE_CHECKING
from typing import Any

from aiohttp import ClientSession
from aiohttp import TCPConnector
from aiohttp_client_cache import CacheBackend
from aiohttp_client_cache.session import CachedSession

from .baseclient import BaseClient
from .errors import BadTemplateError
from .errors import RequestError
from .errors import RequestTimeoutError
from .models import AsyncDomain
from .models import AsyncEntity
from .models import AsyncEvent
from .models import AsyncGroup
from .models import History
from .models import LogbookEntry
from .models import State
from .processing import AsyncResponseType
from .processing import async_process_response
from .utils import prepare_entity_id

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator
    from datetime import datetime
    from types import TracebackType

    from typing_extensions import Self

logger = logging.getLogger(__name__)


class AsyncClient(BaseClient):
    """
    The async client for interacting with Home Assistant via the REST API.

    :param api_url: The location of the api endpoint. e.g. :code:`http://localhost:8123/api` Required.
    :param token: The refresh or long lived access token to authenticate your requests. Required.
    :param session: A custom :py:class:`aiohttp_client_cache.session.CachedSession` or :py:class:`aiohttp.ClientSession` instance. Optional.
    :param use_cache: Enable the default in-memory request cache (300s expiry). Ignored if :code:`session` is provided. Default :code:`False`.
    :param verify_ssl: Whether to verify SSL certificates. Default :code:`True`.
    :param global_request_kwargs: Kwargs to pass to :meth:`aiohttp.ClientSession.request`. Optional.
    """  # pylint: disable=line-too-long

    _session: CachedSession | ClientSession

    def __init__(
        self,
        *args: Any,
        session: CachedSession | None = None,
        use_cache: bool = False,
        verify_ssl: bool = True,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        connector = TCPConnector(ssl=verify_ssl)
        if session is not None:
            self._session = session
        elif use_cache:
            self._session = CachedSession(
                cache=CacheBackend(cache_name="default_async_cache", expire_after=300),
                connector=connector,
            )
        else:
            self._session = ClientSession(connector=connector)

    async def __aenter__(self) -> Self:
        logger.debug("Entering cached async requests session %r", self._session)
        await self._session.__aenter__()
        await self.check_api_running()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        logger.debug("Exiting async requests session %r", self._session)
        await self._session.close()

    # Very important request function
    async def request(
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
            resp = await self._session.request(
                method,
                path,
                headers=self.prepare_headers(headers),
                **kwargs,
            )
        except asyncio.exceptions.TimeoutError as err:
            msg = f"Home Assistant did not respond in time (timeout: {kwargs.get('timeout', 300)} sec)"
            raise RequestTimeoutError(msg, path) from err
        return await self.response_logic(resp)

    async def _dict_request(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        data = await self.request(*args, **kwargs)
        if not isinstance(data, dict):
            msg = f"Expected dict response, got {type(data).__name__}"
            raise TypeError(msg)
        return data

    async def _list_request(self, *args: Any, **kwargs: Any) -> list:
        data = await self.request(*args, **kwargs)
        if not isinstance(data, list):
            msg = f"Expected list response, got {type(data).__name__}"
            raise TypeError(msg)
        return data

    async def _str_request(self, *args: Any, **kwargs: Any) -> str:
        data = await self.request(*args, **kwargs)
        if not isinstance(data, str):
            msg = f"Expected str response, got {type(data).__name__}"
            raise TypeError(msg)
        return data

    @staticmethod
    async def response_logic(response: AsyncResponseType) -> Any:
        """Processes custom mimetype content asynchronously."""
        return await async_process_response(response)

    # API information methods
    async def get_error_log(self) -> str:
        """
        Returns the server error log as a string.
        :code:`GET /api/error_log`
        """
        return await self._str_request("error_log")

    async def get_config(self) -> dict[str, Any]:
        """
        Returns the configuration of Home Assistant.
        :code:`GET /api/config`
        """
        return await self._dict_request("config")

    async def get_logbook_entries(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> AsyncGenerator[LogbookEntry, None]:
        """
        Returns a list of logbook entries from Home Assistant.
        :code:`GET /api/logbook/<timestamp>`
        """
        params, url = self.prepare_get_logbook_entry_params(*args, **kwargs)
        data = await self._list_request(url, params=params)
        for entry in data:
            yield LogbookEntry.model_validate(entry)

    async def get_entity_histories(
        self,
        entities: tuple[AsyncEntity, ...] | None = None,
        start_timestamp: datetime | None = None,
        # Defaults to 1 day before. https://developers.home-assistant.io/docs/api/rest/
        end_timestamp: datetime | None = None,
        *,
        significant_changes_only: bool = False,
    ) -> AsyncGenerator[History, None]:
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
        data = await self._list_request(url, params=params)
        for states in data:
            yield History.model_validate({"states": states})

    async def get_rendered_template(self, template: str) -> str:
        """
        Renders a given Jinja2 template string with Home Assistant context data.
        :code:`POST /api/template`
        """
        try:
            return await self._str_request(
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
    async def check_api_config(self) -> bool:
        """
        Asks Home Assistant to validate its configuration file.
        :code:`POST /api/config/core/check_config`
        """
        res = await self._dict_request(
            "config/core/check_config",
            method=HTTPMethod.POST,
        )
        return {"valid": True, "invalid": False}.get(res["result"], False)

    async def check_api_running(self) -> bool:
        """
        Asks Home Assistant if it is running.
        :code:`GET /api/`
        """
        res = await self._dict_request("")
        return res.get("message") == "API running."

    # Entity methods
    async def get_entities(self) -> dict[str, AsyncGroup]:
        """
        Fetches all entities from the api and returns them as a dictionary of :py:class:`AsyncGroup`'s.
        :code:`GET /api/states`
        """
        entities: dict[str, AsyncGroup] = {}
        for state in await self.get_states():
            group_id, entity_slug = state.entity_id.split(".")
            if group_id not in entities:
                entities[group_id] = AsyncGroup(group_id=group_id, client=self)
            entities[group_id]._add_entity(entity_slug, state)  # noqa: SLF001
        return entities

    async def get_entity(
        self,
        group_id: str | None = None,
        slug: str | None = None,
        entity_id: str | None = None,
    ) -> AsyncEntity | None:
        """
        Returns an :py:class:`AsyncEntity` model for an :code:`entity_id`.
        :code:`GET /api/states/<entity_id>`
        """
        if group_id is not None and slug is not None:
            state = await self.get_state(group_id=group_id, slug=slug)
        elif entity_id is not None:
            state = await self.get_state(entity_id=entity_id)
        else:
            help_msg = (
                "Use keyword arguments to pass entity_id. "
                "Or you can pass the group_id and slug instead."
            )
            msg = f"Neither group_id and slug or entity_id provided. {help_msg}"
            raise ValueError(msg)
        group_id, entity_slug = state.entity_id.split(".")
        group = AsyncGroup(group_id=group_id, client=self)
        group._add_entity(entity_slug, state)  # noqa: SLF001
        return group.get_entity(entity_slug)

    # Services and domain methods
    async def get_domains(self) -> dict[str, AsyncDomain]:
        """
        Fetches all service :py:class:`AsyncDomain`'s from the API.
        :code:`GET /api/services`
        """
        data = await self._list_request("services")
        domains = (
            AsyncDomain.from_json_with_client(json, client=self) for json in data
        )
        return {domain.domain_id: domain for domain in domains}

    async def get_domain(self, domain_id: str) -> AsyncDomain | None:
        """
        Fetches all :py:class:`AsyncService`'s under a particular service :py:class:`AsyncDomain`.
        Uses cached data from :py:meth:`get_domains` if available.
        """
        domains = await self.get_domains()
        return domains.get(domain_id)

    async def trigger_service(
        self,
        domain: str,
        service: str,
        **service_data: Any,
    ) -> tuple[State, ...]:
        """
        Tells Home Assistant to trigger a service, returns all states changed while in the process of being called.
        :code:`POST /api/services/<domain>/<service>`
        """
        data = await self._list_request(
            f"services/{domain}/{service}",
            method=HTTPMethod.POST,
            json=service_data,
        )
        return tuple(map(State.from_json, data))

    async def trigger_service_with_response(
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
        data = await self._dict_request(
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
    async def get_state(  # pylint: disable=duplicate-code
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
        target_entity_id = prepare_entity_id(
            group_id=group_id,
            slug=slug,
            entity_id=entity_id,
        )
        data = await self._dict_request(join("states", target_entity_id))
        return State.from_json(data)

    async def set_state(  # pylint: disable=duplicate-code
        self,
        state: State,
    ) -> State:
        """
        This method sets the representation of a device within Home Assistant and will not communicate with the actual device.
        To communicate with the device, use :py:meth:`AsyncService.trigger`.
        :code:`POST /api/states/<entity_id>`
        """
        data = await self._dict_request(
            join("states", state.entity_id),
            method=HTTPMethod.POST,
            json=json.loads(state.model_dump_json()),
        )
        return State.from_json(data)

    async def get_states(self) -> tuple[State, ...]:
        """
        Gets the states of all entities within Home Assistant.
        :code:`GET /api/states`
        """
        data = await self._list_request("states")
        return tuple(map(State.from_json, data))

    # Event methods
    async def get_events(self) -> tuple[AsyncEvent, ...]:
        """
        Gets the Events that happen within Home Assistant.
        :code:`GET /api/events`
        """
        data = await self._list_request("events")
        return tuple(
            AsyncEvent.from_json_with_client(json, client=self) for json in data
        )

    async def get_event(self, name: str) -> AsyncEvent | None:
        """
        Gets the :py:class:`AsyncEvent` with the specified name if it has at least one listener.
        Uses cached data from :py:meth:`get_events` if available.
        """
        for event in await self.get_events():
            if event.event == name.strip().lower():
                return event
        return None

    async def fire_event(self, event_type: str, **event_data: Any) -> str:
        """
        Fires a given event_type within Home Assistant.
        :code:`POST /api/events/<event_type>`
        """
        data = await self._dict_request(
            join("events", event_type),
            method=HTTPMethod.POST,
            json=event_data,
        )
        return data.get("message", "No message provided")

    async def get_components(self) -> tuple[str, ...]:
        """
        Returns a tuple of all registered components.
        :code:`GET /api/components`
        """
        data = await self._list_request("components")
        return tuple(data)
