import contextlib
from typing import Any, Dict, Generator, Optional, Tuple, cast

from homeassistant_api.models import Domain, Entity, State, Group
from homeassistant_api.models.states import Context
from homeassistant_api.models.websocket import EventResponse, FiredEvent, FiredTrigger, ResultResponse
from homeassistant_api.utils import prepare_entity_id
from .rawwebsocket import RawWebsocketClient

import urllib.parse as urlparse

import logging


logger = logging.getLogger(__name__)


class WebsocketClient(RawWebsocketClient):
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
        :code:`"type": "render_template"`
        """
        id = self.send("render_template", template=template, report_errors=True)
        first = self.recv(id)
        assert first.result is None
        second = self.recv(id)
        self._unsubscribe(id)
        return second.event.result

    def get_config(self) -> dict[str, Any]:
        """Get the Home Assistant configuration."""
        return self.recv(self.send("get_config"))["result"]

    def get_states(self) -> Tuple[State, ...]:
        """Get a list of states."""
        return [
            State.from_json(state)
            for state in self.recv(self.send("get_states"))["result"]
        ]

    def get_state(  # pylint: disable=duplicate-code
        self,
        *,
        entity_id: Optional[str] = None,
        group_id: Optional[str] = None,
        slug: Optional[str] = None,
    ) -> State:
        """
        Just calls the `get_states` method and filters the result.

        Please tell home-assistant/core to add a `get_state` command to the WS API!
        """
        entity_id = prepare_entity_id(
            group_id=group_id,
            slug=slug,
            entity_id=entity_id,
        )

        for state in self.get_states():
            if state.entity_id == entity_id:
                return state

    def get_entities(self) -> Dict[str, Group]:
        """
        Fetches all entities from the Websocket API and returns them as a dictionary of :py:class:`Group`'s.
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
        group_id: str | None = None,
        slug: str | None = None,
        entity_id: str | None = None,
    ) -> Optional[Entity]:
        """
        Returns an :py:class:`Entity` model for an :code:`entity_id`.

        Calls :py:meth:`get_state` in the process.

        Please tell home-assistant/core to add a `get_state` command to the WS API!
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
        """Get a list of (service) domains."""
        data = self.recv(self.send("get_services"))["result"]
        domains = map(
            lambda item: Domain.from_json(
                {"domain": item[0], "services": item[1]},
                client=cast(WebsocketClient, self),
            ),
            cast(dict[str, Any], data).items(),
        )
        return {domain.domain_id: domain for domain in domains}

    def get_domain(self, domain: str) -> Domain:
        """Get a domain.

        Note: This is not a method in the WS API client... yet.

        Please tell home-assistant/core to add a `get_domain` command to the WS API!

        For now, just call the `get_services` method and parsing the result.
        """
        return self.get_domains()[domain]

    def trigger_service(
        self,
        domain: str,
        service: str,
        entity_id: str | None = None,
        **service_data,
    ) -> None:
        """Trigger a service."""
        params = {
            "domain": domain,
            "service": service,
            "service_data": service_data,
            "return_response": False,
        }
        if entity_id is not None:
            params["target"] = {"entity_id": entity_id}

        data = self.recv(self.send("call_service", **params))

        # TODO: handle data["result"]["context"]

        return data["result"].get(
            "response"
        )  # should always be None for services without a response

    def trigger_service_with_response(
        self,
        domain: str,
        service: str,
        entity_id: str | None = None,
        **service_data,
    ) -> dict[str, Any]:
        params = {
            "domain": domain,
            "service": service,
            "service_data": service_data,
            "return_response": True,
        }
        if entity_id is not None:
            params["target"] = {"entity_id": entity_id}

        data = self.recv(self.send("call_service", **params))

        return data["result"]["response"]

    @contextlib.contextmanager
    def subscribe_events(
        self, event_type: Optional[str] = None,
    ) -> Generator[Generator[FiredEvent, None, None], None, None]:
        """
        Subscribe to all events of a certain type and calls `unsubscribe_events` when done.
        """
        subscription = self._subscribe_events(event_type)
        yield cast(Generator[FiredEvent, None, None], self._wait_for(subscription))
        self._unsubscribe(subscription)

    def _subscribe_events(self, event_type: Optional[str]) -> int:
        """Subscribe to all events of a certain type."""
        params = {"event_type": event_type} if event_type else {}
        return self.recv(self.send("subscribe_events", **params)).id

    @contextlib.contextmanager
    def subscribe_trigger(self, trigger: str, **trigger_fields) -> Generator[Generator[FiredTrigger, None, None], None, None]:
        """
        Subscribe to a Home Assistant trigger.
        Allows additional trigger keyword parameters with **kwargs (i.e. passing `tag_id=...` for NFC tag triggers).

        Ex.
        ```
        - trigger: state
          entity_id: light.kitchen
        ``` -> `subscribe_trigger("state", entity_id="light.kitchen")`
        """
        subscription = self._subscribe_trigger(trigger, **trigger_fields)
        yield cast(Generator[FiredTrigger, None, None], self._wait_for(subscription))
        self._unsubscribe(subscription)

    def _subscribe_trigger(self, trigger: str, **trigger_fields) -> int:
        """Return the subscription id of the trigger we subscribe to."""
        return self.recv(
            self.send(
                "subscribe_trigger", trigger={"platform": trigger, **trigger_fields}
            )
        ).id

    def _wait_for(self, subscription_id: int) -> Generator[FiredEvent | FiredTrigger, None, None]:
        """
        An iterator that waits for events of a certain type.
        """
        while True:
            yield cast(EventResponse, self.recv(subscription_id)).event

    def _unsubscribe(self, subcription_id: int) -> None:
        """Unsubscribe from all events of a certain type."""
        resp = self.recv(self.send("unsubscribe_events", subscription=subcription_id))
        assert resp.result is None
        self._event_responses.pop(subcription_id)

    def fire_event(self, event_type: str, **event_data) -> Context:
        """Fire an event."""
        params = {"event_type": event_type}
        if event_data:
            params["event_data"] = event_data
        return Context.from_json(
            cast(
                ResultResponse,
                self.recv(self.send("fire_event", **params)),
            ).result["context"]
        )
