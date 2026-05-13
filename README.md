# HomeassistantAPI

[![Code Coverage](https://img.shields.io/codecov/c/github/HomeAssistant-API/HomeAssistantAPI/dev?style=for-the-badge&token=SJFC3HX5R1)](https://codecov.io/gh/HomeAssistant-API/HomeAssistantAPI)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/HomeAssistant-API?style=for-the-badge)](https://pypistats.org/packages/homeassistant-api)
![GitHub commits since latest release (by date including pre-releases)](https://img.shields.io/github/commits-since/HomeAssistant-API/HomeAssistantAPI/latest/dev?include_prereleases&style=for-the-badge)
[![Read the Docs (version)](https://img.shields.io/readthedocs/homeassistantapi?style=for-the-badge)](https://homeassistantapi.readthedocs.io/en/latest/?badge=latest)
[![GitHub release (latest by date)](https://img.shields.io/github/v/release/HomeAssistant-API/HomeAssistantAPI?style=for-the-badge)](https://github.com/HomeAssistant-API/HomeAssistantAPI/releases)

<a href="https://home-assistant.io">
    <img src="https://github.com/HomeAssistant-API/HomeAssistantAPI/blob/7edb4e6298d37bda19c08b807613c6d351788491/docs/images/homeassistant-logo.png?raw=true" width="80%">
</a>

## Python wrapper for Homeassistant's [Websocket API](https://developers.home-assistant.io/docs/api/websocket/) and [REST API](https://developers.home-assistant.io/docs/api/rest/)

> Note: As of [this comment](https://github.com/home-assistant/architecture/discussions/1074#discussioncomment-9196867) the REST API is not getting any new features or endpoints.
> However, it is not going to be deprecated according to [this comment](https://github.com/home-assistant/developers.home-assistant/pull/2150#pullrequestreview-2017433583)
> But it is recommended to use the Websocket API for new integrations.

### REST API Examples

```py
from homeassistant_api import Client

with Client(
    '<API Server URL>', # i.e. 'http://homeassistant.local:8123/api/'
    '<Your Long Lived Access-Token>'
) as client:
    client.trigger_service('light', 'turn_on', entity_id="light.living_room")
```

All four client classes share the same method names.
The async clients (`AsyncClient`, `AsyncWebsocketClient`) use `async def` methods that you `await`.

```py
import asyncio
from homeassistant_api import AsyncClient

async def main():
    async with AsyncClient(
        '<REST API Server URL>', # i.e. 'http://homeassistant.local:8123/api/'
        '<Your Long Lived Access-Token>',
    ) as client:
        await client.trigger_service('light', 'turn_on', entity_id="light.living_room")

asyncio.run(main())
```

### Websocket API Example

```py
from homeassistant_api import WebsocketClient

with WebsocketClient(
    '<WS API Server URL>', # i.e. 'ws://homeassistant.local:8123/api/websocket'
    '<Your Long Lived Access-Token>'
) as ws_client:
    ws_client.trigger_service('light', 'turn_on', entity_id="light.living_room")
```

## Documentation

All documentation, API reference, contribution guidelines and pretty much everything else
you'd want to know is on our readthedocs site [here](https://homeassistantapi.readthedocs.io)

If there is something missing, open an issue and let us know! Thanks!

Go make some cool stuff! Maybe come back and tell us about it in a
[discussion](https://github.com/HomeAssistant-API/HomeAssistantAPI/discussions)?
We'd love to hear about how you use our library!!

## License

This project is under the GNU GPLv3 license, as defined by the Free Software Foundation.
