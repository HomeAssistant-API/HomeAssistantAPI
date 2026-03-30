import contextlib
import json
import logging
import time
from typing import Any, Dict, Generator, Optional, Tuple, Union, cast

import websockets.sync.client as ws
from pydantic import ValidationError

from homeassistant_api.errors import (
    ReceivingError,
    ResponseError,
    UnauthorizedError,
)
from homeassistant_api.models import (
    ConfigEntry,
    ConfigEntryEvent,
    ConfigSubEntry,
    Domain,
    Entity,
    Group,
    State,
)
from homeassistant_api.models.config_entries import DisableEnableResult, FlowResult
from homeassistant_api.models.states import Context
from homeassistant_api.models.websocket import (
    AuthInvalid,
    AuthOk,
    AuthRequired,
    EventResponse,
    FiredEvent,
    FiredTrigger,
    PingResponse,
    ResultResponse,
    TemplateEvent,
)
from homeassistant_api.basewebsocket import BaseWebsocketClient
from homeassistant_api.utils import JSONType, prepare_entity_id

logger = logging.getLogger(__name__)


class WebsocketClient(BaseWebsocketClient):
    _conn: Optional[ws.ClientConnection]

    def __init__(self, api_url: str, token: str) -> None:
        super().__init__(api_url, token)
        self._conn = None

        self._id_counter = 0
        self._result_responses: dict[
            int, Optional[ResultResponse]
        ] = {}  # id -> response
        self._event_responses: dict[
            int, list[EventResponse]
        ] = {}  # id -> [response, ...]
        self._ping_responses: dict[int, PingResponse] = {}  # id -> (sent, received)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.api_url!r})"

    def __enter__(self):
        self._conn = ws.connect(self.api_url)
        self._conn.__enter__()
        okay = self.authentication_phase()
        logging.info("Authenticated with Home Assistant (%s)", okay.ha_version)
        self.supported_features_phase()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if not self._conn:
            raise ReceivingError("Connection is not open!")
        self._conn.__exit__(exc_type, exc_value, traceback)
        self._conn = None

    def _send(self, data: dict[str, JSONType]) -> None:
        """Send a message to the websocket server."""
        logger.debug(f"Sending message: {data}")
        if self._conn is None:
            raise ReceivingError("Connection is not open!")
        self._conn.send(json.dumps(data))

    def _recv(self) -> dict[str, JSONType]:
        """Receive a message from the websocket server."""
        if self._conn is None:
            raise ReceivingError("Connection is not open!")
        _bytes = self._conn.recv()
        logger.debug("Received message: %s", _bytes)
        return cast(dict[str, JSONType], json.loads(_bytes))

    def send(self, type: str, include_id: bool = True, **data: Any) -> int:
        """
        Send a command message to the websocket server and wait for a "result" response.

        Returns the id of the message sent.
        """
        if include_id:  # auth messages don't have an id
            data["id"] = self._request_id()

        data["type"] = type
        self._send(data)

        if "id" in data:
            assert isinstance(data["id"], int)
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

    def recv(self, id: int) -> Union[EventResponse, ResultResponse, PingResponse]:
        """Receive a response to a message from the websocket server."""
        while True:
            ## have we received a message with the id we're looking for?
            if self._result_responses.get(id) is not None:
                return cast(dict[int, ResultResponse], self._result_responses).pop(
                    id
                )  # ughhh why can't mypy figure this out
            if self._event_responses.get(id, []):
                return self._event_responses[id].pop(0)
            if self._ping_responses.get(id) is not None:
                if self._ping_responses[id].end is not None:
                    return self._ping_responses.pop(id)

            ## if not, keep receiving messages until we do
            self.handle_recv(self._recv())

    def authentication_phase(self) -> AuthOk:
        """Authenticate with the websocket server."""
        # Capture the first message from the server saying we need to authenticate
        try:
            welcome = AuthRequired.model_validate(self._recv())
            logger.debug(f"Received welcome message: {welcome}")
        except ValidationError as e:
            raise ResponseError("Unexpected response during authentication") from e

        # Send our authentication token
        self.send("auth", access_token=self.token, include_id=False)
        logger.debug("Sent auth message")

        # Check the response
        resp = self._recv()
        try:
            return AuthOk.model_validate(resp)
        except ValidationError as e:
            error_resp = AuthInvalid.model_validate(resp)
            raise UnauthorizedError(error_resp.message) from e
        except Exception as e:
            raise ResponseError(
                "Unexpected response during authentication", resp["message"]
            ) from e

    def supported_features_phase(self) -> None:
        """Get the supported features from the websocket server."""
        resp = self.recv(
            self.send(
                "supported_features",
                features={
                    # "coalesce_messages": 42, # including this key sets it to True
                },
            )
        )
        assert cast(ResultResponse, resp).result is None

    def ping_latency(self) -> float:
        """Get the latency (in milliseconds) of the connection by sending a ping message."""
        pong = cast(PingResponse, self.recv(self.send("ping")))
        assert pong.end is not None
        return (pong.end - pong.start) / 1_000_000

    def get_rendered_template(self, template: str) -> str:
        """
        Renders a Jinja2 template with Home Assistant context data.
        See https://www.home-assistant.io/docs/configuration/templating.

        Sends command :code:`{"type": "render_template", ...}`.
        """
        id = self.send("render_template", template=template, report_errors=True)
        first = self.recv(id)
        assert cast(ResultResponse, first).result is None
        second = self.recv(id)
        self._unsubscribe(id)
        return cast(TemplateEvent, cast(EventResponse, second).event).result

    def get_config(self) -> dict[str, JSONType]:
        """
        Get the Home Assistant configuration.

        Sends command :code:`{"type": "get_config", ...}`.
        """
        return cast(
            dict[str, JSONType],
            cast(
                ResultResponse,
                self.recv(self.send("get_config")),
            ).result,
        )

    def get_states(self) -> Tuple[State, ...]:
        """
        Get a list of states.

        Sends command :code:`{"type": "get_states", ...}`.
        """
        return tuple(
            State.from_json(state)
            for state in cast(
                list[dict[str, JSONType]],
                cast(ResultResponse, self.recv(self.send("get_states"))).result,
            )
        )

    def get_state(  # pylint: disable=duplicate-code
        self,
        *,
        entity_id: Optional[str] = None,
        group_id: Optional[str] = None,
        slug: Optional[str] = None,
    ) -> State:
        """
        Just calls the :py:meth:`get_states` method and filters the result.

        Please tell home-assistant/core to add a :code:`{"type": "get_state", ...}` command to the WS API!
        There is a lot of disappointment and frustration in the community because this is not available.
        """
        entity_id = prepare_entity_id(
            group_id=group_id,
            slug=slug,
            entity_id=entity_id,
        )

        for state in self.get_states():
            if state.entity_id == entity_id:
                return state
        raise ValueError(f"Entity {entity_id} not found!")

    def get_entities(self) -> Dict[str, Group]:
        """
        Fetches all entities from the Websocket API and returns them as a dictionary of :py:class:`Group`'s.
        For example :code:`light.living_room` would be in the group :code:`light` (i.e. :code:`get_entities()["light"].living_room`).
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

        Calls :py:meth:`get_states` under the hood.

        Please tell home-assistant/core to add a :code:`{"type": "get_state", ...}` command to the WS API!
        There is a lot of disappointment and frustration in the community because this is not available.
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

    def get_domains(self) -> dict[str, Domain]:
        """
        Get a list of services that Home Assistant offers (organized into a dictionary of service domains).

        For example, the service :code:`light.turn_on` would be in the domain :code:`light`.

        Sends command :code:`{"type": "get_services", ...}`.
        """
        resp = self.recv(self.send("get_services"))
        domains = map(
            lambda item: Domain.from_json_with_client(
                {"domain": item[0], "services": item[1]},
                client=cast("WebsocketClient", self),
            ),
            cast(dict[str, JSONType], cast(ResultResponse, resp).result).items(),
        )
        return {domain.domain_id: domain for domain in domains}

    def get_domain(self, domain: str) -> Domain:
        """Get a domain.

        Note: This is not a method in the WS API client... yet.

        Please tell home-assistant/core to add a `get_domain` command to the WS API!

        For now, just call the :py:meth":`get_domains` method and parsing the result.
        """
        return self.get_domains()[domain]

    def trigger_service(
        self,
        domain: str,
        service: str,
        entity_id: Optional[str] = None,
        **service_data,
    ) -> None:
        """
        Trigger a service (that doesn't return a response).

        Sends command :code:`{"type": "call_service", ...}`.
        """
        params = {
            "domain": domain,
            "service": service,
            "service_data": service_data,
            "return_response": False,
        }
        if entity_id is not None:
            params["target"] = {"entity_id": entity_id}

        data = self.recv(self.send("call_service", include_id=True, **params))

        # TODO: handle data["result"]["context"] ?

        assert (
            cast(
                dict[str, JSONType],
                cast(ResultResponse, data).result,
            ).get("response")
            is None
        )  # should always be None for services without a response

    def trigger_service_with_response(
        self,
        domain: str,
        service: str,
        entity_id: Optional[str] = None,
        **service_data,
    ) -> dict[str, JSONType]:
        """
        Trigger a service (that returns a response) and return the response.

        Sends command :code:`{"type": "call_service", ...}`.
        """
        params = {
            "domain": domain,
            "service": service,
            "service_data": service_data,
            "return_response": True,
        }
        if entity_id is not None:
            params["target"] = {"entity_id": entity_id}

        data = self.recv(self.send("call_service", include_id=True, **params))

        return cast(dict[str, dict[str, JSONType]], cast(ResultResponse, data).result)[
            "response"
        ]

    @contextlib.contextmanager
    def listen_events(
        self,
        event_type: Optional[str] = None,
    ) -> Generator[Generator[FiredEvent, None, None], None, None]:
        """
        Listen for all events of a certain type.

        For example, to listen for all events of type `test_event`:

        .. code-block:: python

            with ws_client.listen_events("test_event") as events:
                for i, event in zip(range(2), events):  # to only wait for two events to be received
                    print(event)
        """
        subscription = self._subscribe_events(event_type)
        yield cast(Generator[FiredEvent, None, None], self._wait_for(subscription))
        self._unsubscribe(subscription)

    def _subscribe_events(self, event_type: Optional[str]) -> int:
        """
        Subscribe to all events of a certain type.


        Sends command :code:`{"type": "subscribe_events", ...}`.
        """
        params = {"event_type": event_type} if event_type else {}
        return self.recv(self.send("subscribe_events", include_id=True, **params)).id

    @contextlib.contextmanager
    def listen_trigger(
        self, trigger: str, **trigger_fields
    ) -> Generator[Generator[dict[str, JSONType], None, None], None, None]:
        """
        Listen to a Home Assistant trigger.
        Allows additional trigger keyword parameters with :code:`**kwargs` (i.e. passing :code:`tag_id=...` for NFC tag triggers).

        For example, in Home Assistant Automations we can subscribe to a state trigger for a light entity with YAML:

        .. code-block:: yaml

            triggers:
            # ...
            - trigger: state
              entity_id: light.kitchen

        To subscribe to that same state trigger with :py:class:`WebsocketClient` instead

        .. code-block:: python

            with ws_client.listen_trigger("state", entity_id="light.kitchen") as trigger:
                for event in trigger:  # will iterate until we manually break out of the loop
                    print(event)
                    if <some_condition>:
                        break
                # exiting the context manager unsubscribes from the trigger

        Woohoo! We can now listen to triggers in Python code!
        """
        subscription = self._subscribe_trigger(trigger, **trigger_fields)
        yield (
            fired_trigger.variables
            for fired_trigger in cast(
                Generator[FiredTrigger, None, None],
                self._wait_for(subscription),
            )
        )
        self._unsubscribe(subscription)

    def _subscribe_trigger(self, trigger: str, **trigger_fields) -> int:
        """
        Return the subscription id of the trigger we subscribe to.

        Sends command :code:`{"type": "subscribe_trigger", ...}`.
        """
        return self.recv(
            self.send(
                "subscribe_trigger", trigger={"platform": trigger, **trigger_fields}
            )
        ).id

    def _wait_for(
        self, subscription_id: int
    ) -> Generator[Union[FiredEvent, FiredTrigger], None, None]:
        """
        An iterator that waits for events of a certain type.
        """
        while True:
            yield cast(
                Union[
                    FiredEvent, FiredTrigger
                ],  # we can cast this because TemplateEvent is only used for rendering templates
                cast(EventResponse, self.recv(subscription_id)).event,
            )

    def _unsubscribe(self, subcription_id: int) -> None:
        """
        Unsubscribe from all events of a certain type.

        Sends command :code:`{"type": "unsubscribe_events", ...}`.
        """
        resp = self.recv(self.send("unsubscribe_events", subscription=subcription_id))
        assert cast(ResultResponse, resp).result is None
        self._event_responses.pop(subcription_id)

    def get_config_entries(self) -> Tuple[ConfigEntry, ...]:
        """
        Get all config entries.

        Sends command :code:`{"type": "config_entries/get", ...}`.
        """
        resp = self.recv(self.send("config_entries/get"))
        return tuple(
            ConfigEntry.from_json(entry)
            for entry in cast(
                list[dict[str, JSONType]],
                cast(ResultResponse, resp).result,
            )
        )

    def disable_config_entry(self, entry_id: str) -> DisableEnableResult:
        """
        Disable a config entry.

        Sends command :code:`{"type": "config_entries/disable", ...}`.
        """
        resp = self.recv(
            self.send(
                "config_entries/disable",
                entry_id=entry_id,
                disabled_by="user",
            )
        )
        return DisableEnableResult.from_json(
            cast(dict[str, JSONType], cast(ResultResponse, resp).result)
        )

    def enable_config_entry(self, entry_id: str) -> DisableEnableResult:
        """
        Enable a config entry.

        Sends command :code:`{"type": "config_entries/disable", ...}`.
        """
        resp = self.recv(
            self.send(
                "config_entries/disable",
                entry_id=entry_id,
                disabled_by=None,
            )
        )
        return DisableEnableResult.from_json(
            cast(dict[str, JSONType], cast(ResultResponse, resp).result)
        )

    def ignore_config_flow(self, flow_id: str, title: str) -> None:
        """
        Ignore a config flow.

        Sends command :code:`{"type": "config_entries/ignore_flow", ...}`.
        """
        self.recv(
            self.send(
                "config_entries/ignore_flow",
                flow_id=flow_id,
                title=title,
            )
        )

    def get_nonuser_flows_in_progress(self) -> Tuple[FlowResult, ...]:
        """
        Get non-user config flows in progress.

        Sends command :code:`{"type": "config_entries/flow/progress", ...}`.
        """
        resp = self.recv(self.send("config_entries/flow/progress"))
        return tuple(
            FlowResult.from_json(flow)
            for flow in cast(
                list[dict[str, JSONType]],
                cast(ResultResponse, resp).result,
            )
        )

    def get_entry_subentries(self, entry_id: str) -> Tuple[ConfigSubEntry, ...]:
        """
        Get subentries for a config entry.

        Sends command :code:`{"type": "config_entries/subentries/list", ...}`.
        """
        resp = self.recv(self.send("config_entries/subentries/list", entry_id=entry_id))
        return tuple(
            ConfigSubEntry.from_json(subentry)
            for subentry in cast(
                list[dict[str, JSONType]],
                cast(ResultResponse, resp).result,
            )
        )

    def delete_entry_subentry(self, entry_id: str, subentry_id: str) -> None:
        """
        Delete a subentry from a config entry.

        Sends command :code:`{"type": "config_entries/subentries/delete", ...}`.
        """
        self.recv(
            self.send(
                "config_entries/subentries/delete",
                entry_id=entry_id,
                subentry_id=subentry_id,
            )
        )

    @contextlib.contextmanager
    def listen_config_entries(
        self,
    ) -> Generator[Generator[list[ConfigEntryEvent], None, None], None, None]:
        """
        Listen for config entry changes.

        Sends command :code:`{"type": "config_entries/subscribe", ...}`.
        """
        subscription = self.recv(self.send("config_entries/subscribe")).id
        yield self._wait_for_config_entries(subscription)
        self._unsubscribe(subscription)

    def _wait_for_config_entries(
        self, subscription_id: int
    ) -> Generator[list[ConfigEntryEvent], None, None]:
        """An iterator that waits for config entry events."""
        while True:
            event_resp = cast(EventResponse, self.recv(subscription_id))
            entries = cast(list[dict[str, JSONType]], event_resp.event)
            yield [ConfigEntryEvent.from_json(entry) for entry in entries]

    def fire_event(self, event_type: str, **event_data) -> Context:
        """
        Fire an event.

        Sends command :code:`{"type": "fire_event", ...}`.
        """
        params: dict[str, JSONType] = {"event_type": event_type}
        if event_data:
            params["event_data"] = event_data
        return Context.from_json(
            cast(
                dict[str, dict[str, JSONType]],
                cast(
                    ResultResponse,
                    self.recv(self.send("fire_event", include_id=True, **params)),
                ).result,
            )["context"]
        )
