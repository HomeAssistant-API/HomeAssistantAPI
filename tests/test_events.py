from datetime import datetime

import pytest

from homeassistant_api.websocket import WebsocketClient


def test_listen_events(websocket_client: WebsocketClient) -> None:
    with websocket_client.listen_events("test_event") as events:
        websocket_client.fire_event(
            "test_event", message="Triggered by websocket client"
        )
        for _, event in zip(range(1), events):
            assert event.origin == "LOCAL"
            assert event.event_type == "test_event"
            assert event.data["message"] == "Triggered by websocket client"


def test_listen_trigger(websocket_client: WebsocketClient) -> None:
    future = datetime.fromisoformat(
        websocket_client.get_rendered_template("{{ (now() + timedelta(seconds=1)) }}")
    )
    with websocket_client.listen_trigger(
        "time", at=future.strftime("%H:%M:%S")
    ) as triggers:
        for _, trigger in zip(range(1), triggers):
            assert trigger["trigger"]["platform"] == "time"
            assert datetime.fromisoformat(
                trigger["trigger"]["now"]
            ).timestamp() == pytest.approx(future.timestamp(), abs=0.5)
