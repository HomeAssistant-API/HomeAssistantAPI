import os

from homeassistant_api import Client

api_url = os.getenv("API_URL")
token = os.getenv("TOKEN")


def main() -> None:
    # Intitializes the main Client
    client = Client(api_url, token)
    # Verifies the extistence of the specified server and opens efficient ClientSessions.
    with client:
        light = client.get_domain("light")
        if light is None:
            return
        print(light.model_dump())  # noqa: T201


if __name__ == "__main__":
    main()
