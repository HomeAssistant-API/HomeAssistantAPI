from __future__ import annotations

import contextlib
import json
import logging
import time
from typing import TYPE_CHECKING
from typing import Any

import websockets.asyncio.client as ws
from pydantic import ValidationError
from typing_extensions import Self

from homeassistant_api.basewebsocket import BaseWebsocketClient
from homeassistant_api.errors import ReceivingError
from homeassistant_api.errors import ResponseError
from homeassistant_api.errors import UnauthorizedError
from homeassistant_api.models import AsyncDomain
from homeassistant_api.models import AsyncEntity
from homeassistant_api.models import AsyncGroup
from homeassistant_api.models import ConfigEntry
from homeassistant_api.models import ConfigEntryEvent
from homeassistant_api.models import ConfigSubEntry
from homeassistant_api.models import History
from homeassistant_api.models import State
from homeassistant_api.models.config_entries import DisableEnableResult
from homeassistant_api.models.config_entries import FlowResult
from homeassistant_api.models.entity_registry import EntityRegistryEntry
from homeassistant_api.models.entity_registry import EntityRegistryEntryExtended
from homeassistant_api.models.entity_registry import EntityRegistryUpdateResult
from homeassistant_api.models.states import Context
from homeassistant_api.models.websocket import AuthInvalid
from homeassistant_api.models.websocket import AuthOk
from homeassistant_api.models.websocket import AuthRequired
from homeassistant_api.models.websocket import EventResponse
from homeassistant_api.models.websocket import FiredEvent
from homeassistant_api.models.websocket import FiredTrigger
from homeassistant_api.models.websocket import PingResponse
from homeassistant_api.models.websocket import ResultResponse
from homeassistant_api.models.websocket import TemplateEvent
from homeassistant_api.utils import prepare_entity_id

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator
    from datetime import datetime
    from types import TracebackType

logger = logging.getLogger(__name__)


class AsyncWebsocketClient(BaseWebsocketClient):
    _async_conn: ws.ClientConnection | None

    def __init__(self, api_url: str, token: str, *, max_size: int = 2**24) -> None:
        super().__init__(api_url, token, max_size=max_size)
        self._async_conn = None

    async def __aenter__(self) -> Self:
        self._async_conn = await ws.connect(self.api_url, max_size=self.max_size)
        await self._async_conn.__aenter__()
        okay = await self.authentication_phase()
        logger.info("Authenticated with Home Assistant (%s)", okay.ha_version)
        await self.supported_features_phase()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if not self._async_conn:
            msg = "Connection is not open!"
            raise ReceivingError(msg)
        await self._async_conn.__aexit__(exc_type, exc_value, traceback)
        self._async_conn = None

    async def _async_send(self, data: dict[str, Any]) -> None:
        """Send a message to the websocket server."""
        logger.debug(f"Sending message: {data}")
        if self._async_conn is None:
            msg = "Connection is not open!"
            raise ReceivingError(msg)
        await self._async_conn.send(json.dumps(data))

    async def _async_recv(self) -> dict[str, Any]:
        """Receive a message from the websocket server."""
        if self._async_conn is None:
            msg = "Connection is not open!"
            raise ReceivingError(msg)
        _bytes = await self._async_conn.recv()
        logger.debug("Received message: %s", _bytes)
        r = json.loads(_bytes)
        if not isinstance(r, dict):
            msg = f"Expected dict, got {type(r).__name__}"
            raise TypeError(msg)
        return r

    async def send(self, msg_type: str, include_id: bool = True, **data: Any) -> int:
        """
        Send a command message to the websocket server and wait for a "result" response.

        Returns the id of the message sent.
        """
        if include_id:  # auth messages don't have an id
            data["id"] = self._request_id()

        data["type"] = msg_type
        await self._async_send(data)

        if "id" in data:
            if not isinstance(data["id"], int):
                msg = f"Expected int for message id, got {type(data['id'])}"
                raise TypeError(msg)
            if data["type"] == "ping":
                self._ping_responses[data["id"]] = PingResponse(
                    start=time.perf_counter_ns(),
                    id=data["id"],
                    type="pong",
                )
            else:
                self._event_responses[data["id"]] = []
                self._result_responses[data["id"]] = None
            return data["id"]
        return -1  # non-command messages don't have an id

    async def recv(
        self,
        msg_id: int,
    ) -> EventResponse | ResultResponse | PingResponse | None:
        """Receive a response to a message from the websocket server."""
        while True:
            ## have we received a message with the id we're looking for?
            if self._result_responses.get(msg_id) is not None:
                return self._result_responses.pop(msg_id)
            if self._event_responses.get(msg_id, []):
                return self._event_responses[msg_id].pop(0)
            if (
                self._ping_responses.get(msg_id) is not None
                and self._ping_responses[msg_id].end is not None
            ):
                return self._ping_responses.pop(msg_id)

            ## if not, keep receiving messages until we do
            self.handle_recv(await self._async_recv())

    async def recv_result(self, msg_id: int) -> ResultResponse:
        """Receive a ResultResponse, raising TypeError if the response is not a ResultResponse."""
        resp = await self.recv(msg_id)
        if not isinstance(resp, ResultResponse):
            msg = f"Expected ResultResponse, got {type(resp).__name__}"
            raise TypeError(msg)
        return resp

    async def recv_result_dict(self, msg_id: int) -> dict[str, Any]:
        """Receive a ResultResponse and return its result as a dict."""
        resp = await self.recv_result(msg_id)
        if not isinstance(resp.result, dict):
            msg = f"Expected dict result, got {type(resp.result).__name__}"
            raise TypeError(msg)
        return resp.result

    async def recv_result_list(self, msg_id: int) -> list[dict[str, Any]]:
        """Receive a ResultResponse and return its result as a list."""
        resp = await self.recv_result(msg_id)
        if not isinstance(resp.result, list):
            msg = f"Expected list result, got {type(resp.result).__name__}"
            raise TypeError(msg)
        return resp.result

    async def recv_event(self, msg_id: int) -> EventResponse:
        """Receive an EventResponse, raising TypeError if the response is not an EventResponse."""
        resp = await self.recv(msg_id)
        if not isinstance(resp, EventResponse):
            msg = f"Expected EventResponse, got {type(resp).__name__}"
            raise TypeError(msg)
        return resp

    async def recv_ping(self, msg_id: int) -> PingResponse:
        """Receive a PingResponse, raising TypeError if the response is not a PingResponse."""
        resp = await self.recv(msg_id)
        if not isinstance(resp, PingResponse):
            msg = f"Expected PingResponse, got {type(resp).__name__}"
            raise TypeError(msg)
        return resp

    async def authentication_phase(self) -> AuthOk:
        """Authenticate with the websocket server."""
        # Capture the first message from the server saying we need to authenticate
        try:
            welcome = AuthRequired.model_validate(await self._async_recv())
            logger.debug(f"Received welcome message: {welcome}")
        except ValidationError as e:
            msg = "Unexpected response during authentication"
            raise ResponseError(msg) from e

        # Send our authentication token
        await self.send("auth", access_token=self.token, include_id=False)
        logger.debug("Sent auth message")

        # Check the response
        resp = await self._async_recv()
        try:
            return AuthOk.model_validate(resp)
        except ValidationError as e:
            error_resp = AuthInvalid.model_validate(resp)
            raise UnauthorizedError(error_resp.message) from e
        except Exception as e:
            msg = "Unexpected response during authentication"
            raise ResponseError(msg, resp["message"]) from e

    async def supported_features_phase(self) -> None:
        """Get the supported features from the websocket server."""
        resp = await self.recv_result(
            await self.send(
                "supported_features",
                features={
                    # "coalesce_messages": 42, # including this key sets it to True  # noqa: ERA001
                },
            ),
        )
        if resp.result is not None:
            msg = "Expected None result for unsubscribe"
            raise ValueError(msg)

    async def ping_latency(self) -> float:
        """Get the latency (in milliseconds) of the connection by sending a ping message."""
        pong = await self.recv_ping(await self.send("ping"))
        if pong.end is None:
            msg = "Pong response missing end timestamp"
            raise ValueError(msg)
        return (pong.end - pong.start) / 1_000_000

    async def get_rendered_template(self, template: str) -> str:
        """
        Renders a Jinja2 template with Home Assistant context data.
        See https://www.home-assistant.io/docs/configuration/templating.

        Sends command :code:`{"type": "render_template", ...}`.
        """
        msg_id = await self.send(
            "render_template",
            template=template,
            report_errors=True,
        )
        await self.recv_result(msg_id)
        second = await self.recv_event(msg_id)
        await self._async_unsubscribe(msg_id)
        if not isinstance(second.event, TemplateEvent):
            msg = f"Expected TemplateEvent, got {type(second.event).__name__}"
            raise TypeError(msg)
        return str(second.event.result)

    async def get_config(self) -> dict[str, Any]:
        """
        Returns the configuration of Home Assistant.

        Sends command :code:`{"type": "get_config", ...}`.
        """
        return await self.recv_result_dict(await self.send("get_config"))

    async def get_states(self) -> tuple[State, ...]:
        """
        Gets the states of all entities within Home Assistant.

        Sends command :code:`{"type": "get_states", ...}`.
        """
        return tuple(
            State.from_json(state)
            for state in await self.recv_result_list(await self.send("get_states"))
        )

    async def get_state(  # pylint: disable=duplicate-code
        self,
        *,
        entity_id: str | None = None,
        group_id: str | None = None,
        slug: str | None = None,
    ) -> State:
        """
        Fetches the state of the entity specified.

        Note: The WebSocket API has no single-entity state command, so this fetches all states and filters.

        Sends command :code:`{"type": "get_states", ...}`.
        """
        entity_id = prepare_entity_id(
            group_id=group_id,
            slug=slug,
            entity_id=entity_id,
        )

        for state in await self.get_states():
            if state.entity_id == entity_id:
                return state
        msg = f"Entity {entity_id} not found!"
        raise ValueError(msg)

    async def get_entities(self) -> dict[str, AsyncGroup]:
        """
        Fetches all entities from the Websocket API and returns them as a dictionary of :py:class:`AsyncGroup`'s.
        For example :code:`light.living_room` would be in the group :code:`light` (i.e. :code:`get_entities()["light"].living_room`).
        """
        entities: dict[str, AsyncGroup] = {}
        for state in await self.get_states():
            group_id, entity_slug = state.entity_id.split(".")
            if group_id not in entities:
                entities[group_id] = AsyncGroup(
                    group_id=group_id,
                    client=self,
                )
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

        Note: The WebSocket API has no single-entity state command, so this fetches all states and filters.
        """
        if group_id is not None and slug is not None:
            state = await self.get_state(group_id=group_id, slug=slug)
        elif entity_id is not None:
            state = await self.get_state(entity_id=entity_id)
        else:
            help_msg = (
                "Use keyword arguments to pass entity_id. "
                "Or you can pass the group_id and slug instead"
            )
            msg = f"Neither group_id and slug or entity_id provided. {help_msg}"
            raise ValueError(msg)
        split_group_id, split_slug = state.entity_id.split(".")
        group = AsyncGroup(
            group_id=split_group_id,
            client=self,
        )
        group._add_entity(split_slug, state)  # noqa: SLF001
        return group.get_entity(split_slug)

    async def set_state(self, state: State) -> State:
        """Not supported over WebSocket. Use the REST :py:class:`AsyncClient` instead."""
        msg = "set_state is not supported over the WebSocket API. Use the REST AsyncClient."
        raise NotImplementedError(msg)

    async def get_entity_histories(
        self,
        entities: tuple[AsyncEntity, ...] | None = None,  # noqa: ARG002
        start_timestamp: datetime | None = None,  # noqa: ARG002
        end_timestamp: datetime | None = None,  # noqa: ARG002
        significant_changes_only: bool = False,  # noqa: ARG002
    ) -> AsyncGenerator[History, None]:
        """Not supported over WebSocket. Use the REST :py:class:`AsyncClient` instead."""
        msg = "get_entity_histories is not supported over the WebSocket API. Use the REST AsyncClient."
        raise NotImplementedError(msg)
        yield  # unreachable: makes this a true AsyncGenerator for type checkers

    async def get_domains(self) -> dict[str, AsyncDomain]:
        """
        Fetches all service :py:class:`AsyncDomain`'s from the API.

        Sends command :code:`{"type": "get_services", ...}`.
        """
        result = await self.recv_result_dict(await self.send("get_services"))
        domains = (
            AsyncDomain.from_json_with_client(
                {"domain": item[0], "services": item[1]},
                client=self,
            )
            for item in result.items()
        )
        return {domain.domain_id: domain for domain in domains}

    async def get_domain(self, domain_id: str) -> AsyncDomain | None:
        """
        Fetches all :py:class:`AsyncService`'s under a particular service :py:class:`AsyncDomain`.

        Note: The WebSocket API has no single-domain command, so this fetches all domains and filters.
        """
        return (await self.get_domains()).get(domain_id)

    async def trigger_service(
        self,
        domain: str,
        service: str,
        **service_data: Any,
    ) -> None:
        """
        Trigger a service (that doesn't return a response).

        Sends command :code:`{"type": "call_service", ...}`.

        Note: Unlike the REST API, the WebSocket API does not return changed states.
        Subscribe to ``state_changed`` events via :py:meth:`listen_events` to track changes.
        """
        params = {
            "domain": domain,
            "service": service,
            "service_data": service_data,
            "return_response": False,
        }

        result = await self.recv_result_dict(
            await self.send("call_service", include_id=True, **params),
        )

        # TODO: handle result["context"] ?

        if result.get("response") is not None:
            msg = "Unexpected response from service without response support"
            raise ValueError(
                msg,
            )

    async def trigger_service_with_response(
        self,
        domain: str,
        service: str,
        **service_data: Any,
    ) -> dict[str, Any]:
        """
        Trigger a service (that returns a response) and return the response.

        Sends command :code:`{"type": "call_service", ...}`.

        Note: Unlike the REST API, the WebSocket API does not return changed states,
        only the service response data. Subscribe to ``state_changed`` events via
        :py:meth:`listen_events` to track changes.
        """
        params = {
            "domain": domain,
            "service": service,
            "service_data": service_data,
            "return_response": True,
        }

        result = await self.recv_result_dict(
            await self.send("call_service", include_id=True, **params),
        )

        return result["response"]

    @contextlib.asynccontextmanager
    async def listen_events(
        self,
        event_type: str | None = None,
    ) -> AsyncGenerator[AsyncGenerator[FiredEvent | FiredTrigger, None], None]:
        """
        Listen for all events of a certain type.

        For example, to listen for all events of type `test_event`:

        .. code-block:: python

            async with ws_client.listen_events("test_event") as events:
                async for i, event in zip(range(2), events):  # to only wait for two events to be received
                    print(event)
        """
        subscription = await self._async_subscribe_events(event_type)
        yield self._async_wait_for(subscription)
        await self._async_unsubscribe(subscription)

    async def _async_subscribe_events(self, event_type: str | None) -> int:
        """
        Subscribe to all events of a certain type.


        Sends command :code:`{"type": "subscribe_events", ...}`.
        """
        params = {"event_type": event_type} if event_type else {}
        return (
            await self.recv_result(
                await self.send("subscribe_events", include_id=True, **params),
            )
        ).id

    @contextlib.asynccontextmanager
    async def listen_trigger(
        self,
        trigger: str,
        **trigger_fields: Any,
    ) -> AsyncGenerator[AsyncGenerator[dict[str, Any], None], None]:
        """
        Listen to a Home Assistant trigger.
        Allows additional trigger keyword parameters with :code:`**kwargs` (i.e. passing :code:`tag_id=...` for NFC tag triggers).

        For example, in Home Assistant Automations we can subscribe to a state trigger for a light entity with YAML:

        .. code-block:: yaml

            triggers:
            # ...
            - trigger: state
              entity_id: light.kitchen

        To subscribe to that same state trigger with :py:class:`AsyncWebsocketClient` instead

        .. code-block:: python

            async with ws_client.listen_trigger("state", entity_id="light.kitchen") as trigger:
                async for event in trigger:  # will iterate until we manually break out of the loop
                    print(event)
                    if <some_condition>:
                        break
                # exiting the context manager unsubscribes from the trigger

        Woohoo! We can now listen to triggers in Python code!
        """
        subscription = await self._async_subscribe_trigger(trigger, **trigger_fields)
        yield (
            fired_trigger.variables
            async for fired_trigger in self._async_wait_for(subscription)
            if isinstance(fired_trigger, FiredTrigger)
        )
        await self._async_unsubscribe(subscription)

    async def _async_subscribe_trigger(
        self,
        trigger: str,
        **trigger_fields: Any,
    ) -> int:
        """
        Return the subscription id of the trigger we subscribe to.

        Sends command :code:`{"type": "subscribe_trigger", ...}`.
        """
        return (
            await self.recv_result(
                await self.send(
                    "subscribe_trigger",
                    trigger={"platform": trigger, **trigger_fields},
                ),
            )
        ).id

    async def _async_wait_for(
        self,
        subscription_id: int,
    ) -> AsyncGenerator[FiredEvent | FiredTrigger, None]:
        """
        An iterator that waits for events of a certain type.
        """
        while True:
            event_resp = await self.recv_event(subscription_id)
            # TODO: DISCUSS Change of behavior here. before anything received would get yielded
            if isinstance(event_resp.event, FiredEvent | FiredTrigger):
                yield event_resp.event

    async def _async_unsubscribe(self, subcription_id: int) -> None:
        """
        Unsubscribe from all events of a certain type.

        Sends command :code:`{"type": "unsubscribe_events", ...}`.
        """
        resp = await self.recv_result(
            await self.send("unsubscribe_events", subscription=subcription_id),
        )
        if resp.result is not None:
            msg = "Expected None result for unsubscribe"
            raise ValueError(msg)
        self._event_responses.pop(subcription_id)

    async def get_config_entries(self) -> tuple[ConfigEntry, ...]:
        """
        Get all config entries.

        Sends command :code:`{"type": "config_entries/get", ...}`.
        """
        return tuple(
            ConfigEntry.from_json(entry)
            for entry in await self.recv_result_list(
                await self.send("config_entries/get"),
            )
        )

    async def disable_config_entry(self, entry_id: str) -> DisableEnableResult:
        """
        Disable a config entry.

        Sends command :code:`{"type": "config_entries/disable", ...}`.
        """
        result = await self.recv_result_dict(
            await self.send(
                "config_entries/disable",
                entry_id=entry_id,
                disabled_by="user",
            ),
        )
        return DisableEnableResult.from_json(result)

    async def enable_config_entry(self, entry_id: str) -> DisableEnableResult:
        """
        Enable a config entry.

        Sends command :code:`{"type": "config_entries/disable", ...}`.
        """
        result = await self.recv_result_dict(
            await self.send(
                "config_entries/disable",
                entry_id=entry_id,
                disabled_by=None,
            ),
        )
        return DisableEnableResult.from_json(result)

    async def ignore_config_flow(self, flow_id: str, title: str) -> None:
        """
        Ignore a config flow.

        Sends command :code:`{"type": "config_entries/ignore_flow", ...}`.
        """
        await self.recv(
            await self.send(
                "config_entries/ignore_flow",
                flow_id=flow_id,
                title=title,
            ),
        )

    async def get_nonuser_flows_in_progress(self) -> tuple[FlowResult, ...]:
        """
        Get non-user config flows in progress.

        Sends command :code:`{"type": "config_entries/flow/progress", ...}`.
        """
        return tuple(
            FlowResult.from_json(flow)
            for flow in await self.recv_result_list(
                await self.send("config_entries/flow/progress"),
            )
        )

    async def get_entry_subentries(self, entry_id: str) -> tuple[ConfigSubEntry, ...]:
        """
        Get subentries for a config entry.

        Sends command :code:`{"type": "config_entries/subentries/list", ...}`.
        """
        return tuple(
            ConfigSubEntry.from_json(subentry)
            for subentry in await self.recv_result_list(
                await self.send("config_entries/subentries/list", entry_id=entry_id),
            )
        )

    async def delete_entry_subentry(self, entry_id: str, subentry_id: str) -> None:
        """
        Delete a subentry from a config entry.

        Sends command :code:`{"type": "config_entries/subentries/delete", ...}`.
        """
        await self.recv(
            await self.send(
                "config_entries/subentries/delete",
                entry_id=entry_id,
                subentry_id=subentry_id,
            ),
        )

    # ── Entity Registry ─────────────────────────────────────────

    async def list_entity_registry(self) -> tuple[EntityRegistryEntry, ...]:
        """
        List all entity registry entries.

        Sends command :code:`{"type": "config/entity_registry/list", ...}`.
        """
        return tuple(
            EntityRegistryEntry.from_json(entry)
            for entry in await self.recv_result_list(
                await self.send("config/entity_registry/list"),
            )
        )

    async def get_entity_registry_entry(
        self,
        entity_id: str,
    ) -> EntityRegistryEntryExtended:
        """
        Get a single entity registry entry.

        Sends command :code:`{"type": "config/entity_registry/get", ...}`.
        """
        result = await self.recv_result_dict(
            await self.send("config/entity_registry/get", entity_id=entity_id),
        )
        return EntityRegistryEntryExtended.from_json(result)

    async def update_entity_registry_entry(
        self,
        entity_id: str,
        **kwargs: Any,
    ) -> EntityRegistryUpdateResult:
        """
        Update an entity registry entry.

        Sends command :code:`{"type": "config/entity_registry/update", ...}`.
        """
        result = await self.recv_result_dict(
            await self.send(
                "config/entity_registry/update",
                entity_id=entity_id,
                **kwargs,
            ),
        )
        return EntityRegistryUpdateResult.from_json(result)

    async def remove_entity_registry_entry(self, entity_id: str) -> None:
        """
        Remove an entity from the entity registry.

        Sends command :code:`{"type": "config/entity_registry/remove", ...}`.
        """
        await self.recv(
            await self.send("config/entity_registry/remove", entity_id=entity_id),
        )

    @contextlib.asynccontextmanager
    async def listen_config_entries(
        self,
    ) -> AsyncGenerator[AsyncGenerator[list[ConfigEntryEvent], None], None]:
        """
        Listen for config entry changes.

        Sends command :code:`{"type": "config_entries/subscribe", ...}`.
        """
        subscription = (
            await self.recv_result(await self.send("config_entries/subscribe"))
        ).id
        yield self._async_wait_for_config_entries(subscription)
        await self._async_unsubscribe(subscription)

    async def _async_wait_for_config_entries(
        self,
        subscription_id: int,
    ) -> AsyncGenerator[list[ConfigEntryEvent], None]:
        """An async iterator that waits for config entry events."""
        while True:
            event_resp = await self.recv_event(subscription_id)
            if isinstance(event_resp.event, list):
                yield [ConfigEntryEvent.from_json(entry) for entry in event_resp.event]

    async def fire_event(self, event_type: str, **event_data: Any) -> Context:
        """
        Fires a given event_type within Home Assistant.

        Sends command :code:`{"type": "fire_event", ...}`.
        """
        params: dict[str, Any] = {"event_type": event_type}
        if event_data:
            params["event_data"] = event_data
        result = await self.recv_result_dict(
            await self.send("fire_event", include_id=True, **params),
        )
        return Context.from_json(result["context"])
