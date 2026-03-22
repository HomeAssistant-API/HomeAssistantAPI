import contextlib
import json
import logging
import time
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncGenerator,
    Dict,
    Optional,
    Tuple,
    Union,
    cast,
)

import websockets.asyncio.client as ws
from pydantic import ValidationError

from homeassistant_api.errors import (
    ReceivingError,
    ResponseError,
    UnauthorizedError,
)
from homeassistant_api.models import Domain, Entity, Group, State
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
from homeassistant_api.rawbasewebsocket import RawBaseWebsocketClient
from homeassistant_api.utils import JSONType, prepare_entity_id

if TYPE_CHECKING:
    from homeassistant_api import WebsocketClient
else:
    WebsocketClient = None  # pylint: disable=invalid-name

logger = logging.getLogger(__name__)


class RawAsyncWebsocketClient(RawBaseWebsocketClient):
    _async_conn: Optional[ws.ClientConnection]

    def __init__(self, api_url: str, token: str) -> None:
        super().__init__(api_url, token)
        self._async_conn = None

    async def __aenter__(self):
        self._async_conn = await ws.connect(self.api_url)
        await self._async_conn.__aenter__()
        okay = await self.async_authentication_phase()
        logging.info("Authenticated with Home Assistant (%s)", okay.ha_version)
        await self.async_supported_features_phase()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        if not self._async_conn:
            raise ReceivingError("Connection is not open!")
        await self._async_conn.__aexit__(exc_type, exc_value, traceback)
        self._async_conn = None

    async def _async_send(self, data: dict[str, JSONType]) -> None:
        """Send a message to the websocket server."""
        logger.debug(f"Sending message: {data}")
        if self._async_conn is None:
            raise ReceivingError("Connection is not open!")
        await self._async_conn.send(json.dumps(data))

    async def _async_recv(self) -> dict[str, JSONType]:
        """Receive a message from the websocket server."""
        if self._async_conn is None:
            raise ReceivingError("Connection is not open!")
        _bytes = await self._async_conn.recv()
        logger.debug("Received message: %s", _bytes)
        return cast(dict[str, JSONType], json.loads(_bytes))

    async def async_send(self, type: str, include_id: bool = True, **data: Any) -> int:
        """
        Send a command message to the websocket server and wait for a "result" response.

        Returns the id of the message sent.
        """
        if include_id:  # auth messages don't have an id
            data["id"] = self._request_id()

        data["type"] = type
        await self._async_send(data)

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

    async def async_recv(
        self, id: int
    ) -> Union[EventResponse, ResultResponse, PingResponse]:
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
            self.handle_recv(await self._async_recv())

    async def async_authentication_phase(self) -> AuthOk:
        """Authenticate with the websocket server."""
        # Capture the first message from the server saying we need to authenticate
        try:
            welcome = AuthRequired.model_validate(await self._async_recv())
            logger.debug(f"Received welcome message: {welcome}")
        except ValidationError as e:
            raise ResponseError("Unexpected response during authentication") from e

        # Send our authentication token
        await self.async_send("auth", access_token=self.token, include_id=False)
        logger.debug("Sent auth message")

        # Check the response
        resp = await self._async_recv()
        try:
            return AuthOk.model_validate(resp)
        except ValidationError as e:
            error_resp = AuthInvalid.model_validate(resp)
            raise UnauthorizedError(error_resp.message) from e
        except Exception as e:
            raise ResponseError(
                "Unexpected response during authentication", resp["message"]
            ) from e

    async def async_supported_features_phase(self) -> None:
        """Get the supported features from the websocket server."""
        resp = await self.async_recv(
            await self.async_send(
                "supported_features",
                features={
                    # "coalesce_messages": 42, # including this key sets it to True
                },
            )
        )
        assert cast(ResultResponse, resp).result is None

    async def async_ping_latency(self) -> float:
        """Get the latency (in milliseconds) of the connection by sending a ping message."""
        pong = cast(PingResponse, await self.async_recv(await self.async_send("ping")))
        assert pong.end is not None
        return (pong.end - pong.start) / 1_000_000

    async def async_get_rendered_template(self, template: str) -> str:
        """
        Renders a Jinja2 template with Home Assistant context data.
        See https://www.home-assistant.io/docs/configuration/templating.

        Sends command :code:`{"type": "render_template", ...}`.
        """
        id = await self.async_send(
            "render_template", template=template, report_errors=True
        )
        first = await self.async_recv(id)
        assert cast(ResultResponse, first).result is None
        second = await self.async_recv(id)
        await self._async_unsubscribe(id)
        return cast(TemplateEvent, cast(EventResponse, second).event).result

    async def async_get_config(self) -> dict[str, JSONType]:
        """
        Get the Home Assistant configuration.

        Sends command :code:`{"type": "get_config", ...}`.
        """
        return cast(
            dict[str, JSONType],
            cast(
                ResultResponse,
                await self.async_recv(await self.async_send("get_config")),
            ).result,
        )

    async def async_get_states(self) -> Tuple[State, ...]:
        """
        Get a list of states.

        Sends command :code:`{"type": "get_states", ...}`.
        """
        return tuple(
            State.from_json(state)
            for state in cast(
                list[dict[str, JSONType]],
                cast(
                    ResultResponse,
                    await self.async_recv(await self.async_send("get_states")),
                ).result,
            )
        )

    async def async_get_state(  # pylint: disable=duplicate-code
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

        for state in await self.async_get_states():
            if state.entity_id == entity_id:
                return state
        raise ValueError(f"Entity {entity_id} not found!")

    async def async_get_entities(self) -> Dict[str, Group]:
        """
        Fetches all entities from the Websocket API and returns them as a dictionary of :py:class:`Group`'s.
        For example :code:`light.living_room` would be in the group :code:`light` (i.e. :code:`get_entities()["light"].living_room`).
        """
        entities: Dict[str, Group] = {}
        for state in await self.async_get_states():
            group_id, entity_slug = state.entity_id.split(".")
            if group_id not in entities:
                entities[group_id] = Group(
                    group_id=group_id,
                    _client=self,  # type: ignore[arg-type]
                )
            entities[group_id]._add_entity(entity_slug, state)
        return entities

    async def async_get_entity(
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
            state = await self.async_get_state(group_id=group_id, slug=slug)
        elif entity_id is not None:
            state = await self.async_get_state(entity_id=entity_id)
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

    async def async_get_domains(self) -> dict[str, Domain]:
        """
        Get a list of services that Home Assistant offers (organized into a dictionary of service domains).

        For example, the service :code:`light.turn_on` would be in the domain :code:`light`.

        Sends command :code:`{"type": "get_services", ...}`.
        """
        resp = await self.async_recv(await self.async_send("get_services"))
        domains = map(
            lambda item: Domain.from_json_with_client(
                {"domain": item[0], "services": item[1]},
                client=cast(WebsocketClient, self),
            ),
            cast(dict[str, JSONType], cast(ResultResponse, resp).result).items(),
        )
        return {domain.domain_id: domain for domain in domains}

    async def async_get_domain(self, domain: str) -> Domain:
        """Get a domain.

        Note: This is not a method in the WS API client... yet.

        Please tell home-assistant/core to add a `get_domain` command to the WS API!

        For now, just call the :py:meth":`get_domains` method and parsing the result.
        """
        return (await self.async_get_domains())[domain]

    async def async_trigger_service(
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

        data = await self.async_recv(
            await self.async_send("call_service", include_id=True, **params)
        )

        # TODO: handle data["result"]["context"] ?

        assert (
            cast(
                dict[str, JSONType],
                cast(ResultResponse, data).result,
            ).get("response")
            is None
        )  # should always be None for services without a response

    async def async_trigger_service_with_response(
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

        data = await self.async_recv(
            await self.async_send("call_service", include_id=True, **params)
        )

        return cast(dict[str, dict[str, JSONType]], cast(ResultResponse, data).result)[
            "response"
        ]

    @contextlib.asynccontextmanager
    async def async_listen_events(
        self,
        event_type: Optional[str] = None,
    ) -> AsyncGenerator[AsyncGenerator[FiredEvent, None], None]:
        """
        Listen for all events of a certain type.

        For example, to listen for all events of type `test_event`:

        .. code-block:: python

            async with ws_client.listen_events("test_event") as events:
                async for i, event in zip(range(2), events):  # to only wait for two events to be received
                    print(event)
        """
        subscription = await self._async_subscribe_events(event_type)
        yield cast(AsyncGenerator[FiredEvent, None], self._async_wait_for(subscription))
        await self._async_unsubscribe(subscription)

    async def _async_subscribe_events(self, event_type: Optional[str]) -> int:
        """
        Subscribe to all events of a certain type.


        Sends command :code:`{"type": "subscribe_events", ...}`.
        """
        params = {"event_type": event_type} if event_type else {}
        return (
            await self.async_recv(
                await self.async_send("subscribe_events", include_id=True, **params)
            )
        ).id

    @contextlib.asynccontextmanager
    async def async_listen_trigger(
        self, trigger: str, **trigger_fields
    ) -> AsyncGenerator[AsyncGenerator[dict[str, JSONType], None], None]:
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
            async for fired_trigger in cast(
                AsyncGenerator[FiredTrigger, None],
                self._async_wait_for(subscription),
            )
        )
        await self._async_unsubscribe(subscription)

    async def _async_subscribe_trigger(self, trigger: str, **trigger_fields) -> int:
        """
        Return the subscription id of the trigger we subscribe to.

        Sends command :code:`{"type": "subscribe_trigger", ...}`.
        """
        return (
            await self.async_recv(
                await self.async_send(
                    "subscribe_trigger", trigger={"platform": trigger, **trigger_fields}
                )
            )
        ).id

    async def _async_wait_for(
        self, subscription_id: int
    ) -> AsyncGenerator[Union[FiredEvent, FiredTrigger], None]:
        """
        An iterator that waits for events of a certain type.
        """
        while True:
            yield cast(
                Union[
                    FiredEvent, FiredTrigger
                ],  # we can cast this because TemplateEvent is only used for rendering templates
                cast(EventResponse, await self.async_recv(subscription_id)).event,
            )

    async def _async_unsubscribe(self, subcription_id: int) -> None:
        """
        Unsubscribe from all events of a certain type.

        Sends command :code:`{"type": "unsubscribe_events", ...}`.
        """
        resp = await self.async_recv(
            await self.async_send("unsubscribe_events", subscription=subcription_id)
        )
        assert cast(ResultResponse, resp).result is None
        self._event_responses.pop(subcription_id)

    async def async_fire_event(self, event_type: str, **event_data) -> Context:
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
                    await self.async_recv(
                        await self.async_send("fire_event", include_id=True, **params)
                    ),
                ).result,
            )["context"]
        )
