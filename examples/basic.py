import os

from homeassistant_api import Client

api_url = "https://homeassistant.duckdns.org:8123/api"  # Something like http://localhost:8123/api
token = os.getenv(
    "HOMEASSISTANT_TOKEN",
)  # Used to aunthenticate yourself with homeassistant
# See the documentation on how to obtain a Long Lived Access Token


def main() -> None:
    with Client(
        api_url,
        token,
    ) as client:  # Create Client object and check that its running.
        cover = client.get_domain("cover")
        if cover is None:
            return

        # Tells Home Assistant to trigger the toggle service on the given entity_id
        cover.toggle(entity_id="cover.garage_door")


if __name__ == "__main__":
    main()
