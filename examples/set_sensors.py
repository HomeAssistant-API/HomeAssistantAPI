from homeassistant_api import Client
from homeassistant_api import State

with Client(
    "http://homeassistant.local:8123/api",
    "myfabulousapikey",
) as client:
    new_state = client.set_state(
        state=State(entity_id="some_entity", state="42 the answer to everything"),
    )
