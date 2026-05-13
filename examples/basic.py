import os

from homeassistant_api import Client

api_url = "http://localhost:8123/api"  # Something like http://<host>:8123/api, the /api is important!
token = os.getenv(
    "HOMEASSISTANT_TOKEN",  # Used to aunthenticate yourself with homeassistant
)
# See the documentation on how to obtain a Long Lived Access Token


def main() -> None:
    # Create Client object and check that its running.
    with Client(api_url, token) as client:
        cover = client.get_domain("cover")
        if cover is None:
            return

        # Tells Home Assistant to trigger the toggle service on the given entity_id
        cover.toggle(entity_id="cover.garage_door")


if __name__ == "__main__":
    main()
