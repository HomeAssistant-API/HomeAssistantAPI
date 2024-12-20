from typing import Any, cast

from homeassistant_api.models.domains import Domain
from .rawwebsocket import RawWebSocketClient

import urllib.parse as urlparse

import logging


logger = logging.getLogger(__name__)


class WebSocketClient(RawWebSocketClient):
    def __init__(
        self,
        api_url: str,
        token: str,
    ) -> None:
        parsed = urlparse.urlparse(api_url)

        if parsed.scheme not in {"ws", "wss"}:
            raise ValueError(f"Unknown scheme {parsed.scheme} in {api_url}")
        super().__init__(api_url, token)
        logger.info(f"WebSocketClient initialized with api_url: {api_url}")

    def get_config(self) -> dict[str, Any]:
        """Get the configuration."""
        return self.recv(self.send("get_config"))["result"]

    def get_entities(self) -> list[dict[str, str]]:
        """Get a list of entities."""

        # Note: Even though it says "get_states" this is actually comparable
        # to the `get_entities` method from the REST API clients.
        # TODO: do the same parsing logic as in the REST API client
        return self.recv(self.send("get_states"))

    def get_domains(self) -> list[str]:
        """Get a list of (service) domains."""
        data = self.recv(self.send("get_services"))["result"]
        domains = map(
            lambda item: Domain.from_json(
                {"domain": item[0], "services": item[1]},
                client=cast(WebSocketClient, self),
            ),
            cast(dict[str, Any], data).items(),
        )
        return {domain.domain_id: domain for domain in domains}

    def trigger_service(self, domain: str, service: str, **service_data) -> None:
        """Trigger a service."""
        pass

    def get_events(self) -> list[dict[str, str]]:
        """Get a list of events."""
        pass

    def subscribe_event(self, event_type: str) -> None:
        """Subscribe to an event."""
        pass

    def unsubscribe_event(self, event_type: str) -> None:
        """Unsubscribe from an event."""
        pass

    def subscribe_trigger(self, entity_id: str) -> None:
        """Subscribe to a trigger."""
        pass

    def unsubscribe_trigger(self, entity_id: str) -> None:
        """Unsubscribe from a trigger."""
        pass
