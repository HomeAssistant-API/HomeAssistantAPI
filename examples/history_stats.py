"""Fetch 24h history for numeric sensors and print min/max/avg per entity.

Environment variables:
    HOMEASSISTANT_API_ENDPOINT  e.g. http://localhost:8123/api
    HOMEASSISTANT_API_TOKEN     Long-lived access token
"""

import os
from datetime import datetime
from datetime import timedelta
from datetime import timezone

from homeassistant_api import Client

url = os.environ["HOMEASSISTANT_API_ENDPOINT"]
token = os.environ["HOMEASSISTANT_API_TOKEN"]

SENSOR_IDS = [
    "sensor.living_room_temperature",
    "sensor.outdoor_temperature",
    "sensor.energy_consumption",
]


def _to_float(value: str) -> float | None:
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def main() -> None:
    now = datetime.now(tz=timezone.utc)
    yesterday = now - timedelta(hours=24)

    with Client(url, token) as client:
        entities = [
            entity
            for sensor_id in SENSOR_IDS
            if (entity := client.get_entity(entity_id=sensor_id)) is not None
        ]

        for history in client.get_entity_histories(
            entities=tuple(entities),
            start_timestamp=yesterday,
            end_timestamp=now,
        ):
            values = [
                v for s in history.states if (v := _to_float(s.state)) is not None
            ]
            if not values:
                print(f"{history.entity_id}: no numeric data in last 24h")  # noqa: T201
                continue
            print(  # noqa: T201
                f"{history.entity_id}: "
                f"min={min(values):.2f}  "
                f"max={max(values):.2f}  "
                f"avg={sum(values) / len(values):.2f}  "
                f"({len(values)} samples)",
            )


if __name__ == "__main__":
    main()
