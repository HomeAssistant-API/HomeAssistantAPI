import contextlib
import logging
import urllib.parse as urlparse
from typing import Dict, Generator, Optional, Tuple, Union, cast

from homeassistant_api.models import Domain, Entity, Group, State
from homeassistant_api.models.states import Context
from homeassistant_api.models.websocket import (
    EventResponse,
    FiredEvent,
    FiredTrigger,
    ResultResponse,
    TemplateEvent,
)
from homeassistant_api.utils import JSONType, prepare_entity_id

from .rawwebsocket import RawWebsocketClient

logger = logging.getLogger(__name__)


class WebsocketClient(RawWebsocketClient):
    """

    The main class for interactign with the Home Assistant WebSocket API client.

    Here's a quick example of how to use the :py:class:`WebsocketClient` class:

    .. code-block:: python

        from homeassistant_api import WebsocketClient

        with WebsocketClient(
            '<WS API Server URL>', # i.e. 'ws://homeassistant.local:8123/api/websocket'
            '<Your Long Lived Access-Token>'
        ) as ws_client:
            light = ws_client.trigger_service('light', 'turn_on', entity_id="light.living_room")
    """

    def __init__(
        self,
        api_url: str,
        token: str,
    ) -> None:
        parsed = urlparse.urlparse(api_url)

        if parsed.scheme not in {"ws", "wss"}:
            raise ValueError(f"Unknown scheme {parsed.scheme} in {api_url}")
        super().__init__(api_url, token)
        logger.debug(f"WebSocketClient initialized with api_url: {api_url}")

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
            lambda item: Domain.from_json(
                {"domain": item[0], "services": item[1]},
                client=self,
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
