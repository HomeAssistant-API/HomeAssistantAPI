"""Stream live state_changed events for entities in a given domain.

Usage:
    python websocket_state_monitor.py [domain]

    domain defaults to "light". Press Ctrl+C to stop.

Environment variables:
    HOMEASSISTANT_WS_ENDPOINT  e.g. ws://localhost:8123/api/websocket
    HOMEASSISTANT_API_TOKEN    Long-lived access token
"""

import os
import sys

from homeassistant_api import WebsocketClient
from homeassistant_api.models.websocket import FiredEvent

url = os.environ["HOMEASSISTANT_WS_ENDPOINT"]
token = os.environ["HOMEASSISTANT_API_TOKEN"]


def monitor_domain(domain: str) -> None:
    with WebsocketClient(url, token) as ws:
        print(f"Monitoring '{domain}' state changes. Press Ctrl+C to stop.")  # noqa: T201
        with ws.listen_events("state_changed") as events:
            for event in events:
                if not isinstance(event, FiredEvent):
                    continue
                entity_id: str = event.data.get("entity_id", "")
                if not entity_id.startswith(f"{domain}."):
                    continue
                old_state = (event.data.get("old_state") or {}).get(
                    "state",
                    "unavailable",
                )
                new_state = (event.data.get("new_state") or {}).get(
                    "state",
                    "unavailable",
                )
                timestamp = event.time_fired.strftime("%H:%M:%S")
                print(f"[{timestamp}] {entity_id}: {old_state} → {new_state}")  # noqa: T201


if __name__ == "__main__":
    domain = sys.argv[1] if len(sys.argv) > 1 else "light"
    monitor_domain(domain)
