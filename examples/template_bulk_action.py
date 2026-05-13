"""Use a Jinja2 template to find all lights that are on, then turn them off.

Demonstrates combining get_rendered_template with trigger_service to perform
bulk operations based on server-side state queries.

Environment variables:
    HOMEASSISTANT_API_ENDPOINT  e.g. http://localhost:8123/api
    HOMEASSISTANT_API_TOKEN     Long-lived access token
"""

import os

from homeassistant_api import Client

url = os.environ["HOMEASSISTANT_API_ENDPOINT"]
token = os.environ["HOMEASSISTANT_API_TOKEN"]

FIND_ON_LIGHTS = """\
{{ states.light
   | selectattr('state', 'eq', 'on')
   | map(attribute='entity_id')
   | list
   | join(',') }}"""


def main() -> None:
    with Client(url, token) as client:
        rendered = client.get_rendered_template(FIND_ON_LIGHTS)
        entity_ids = [e.strip() for e in rendered.split(",") if e.strip()]

        if not entity_ids:
            print("No lights are currently on.")  # noqa: T201
            return

        print(f"Turning off {len(entity_ids)} light(s)...")  # noqa: T201
        for entity_id in entity_ids:
            client.trigger_service("light", "turn_off", entity_id=entity_id)
            print(f"  off: {entity_id}")  # noqa: T201


if __name__ == "__main__":
    main()
