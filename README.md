# HomeassistantAPI

[![Code Coverage](https://img.shields.io/codecov/c/github/GrandMoff100/HomeAssistantAPI/dev?style=for-the-badge&token=SJFC3HX5R1)](https://codecov.io/gh/GrandMoff100/HomeAssistantAPI)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/HomeAssistant-API?style=for-the-badge)](https://pypistats.org/packages/homeassistant-api)
![GitHub commits since latest release (by date including pre-releases)](https://img.shields.io/github/commits-since/GrandMoff100/HomeassistantAPI/latest/dev?include_prereleases&style=for-the-badge)
[![Read the Docs (version)](https://img.shields.io/readthedocs/homeassistantapi?style=for-the-badge)](https://homeassistantapi.readthedocs.io/en/latest/?badge=latest)
[![GitHub release (latest by date)](https://img.shields.io/github/v/release/GrandMoff100/HomeassistantAPI?style=for-the-badge)](https://github.com/GrandMoff100/HomeassistantAPI/releases)

<a href="https://home-assistant.io">
    <img src="https://github.com/GrandMoff100/HomeAssistantAPI/blob/7edb4e6298d37bda19c08b807613c6d351788491/docs/images/homeassistant-logo.png?raw=true" width="60%">
</a>

## Python wrapper for Homeassistant's [REST API](https://developers.home-assistant.io/docs/api/rest/)

Here is a quick example.

```py
from homeassistant_api import Client

with Client(
    '<API Server URL>',
    '<Your Long Lived Access-Token>'
) as client:

    light = client.get_domain("light")

    light.turn_on(entity_id="light.living_room_lamp")
```

All the methods also support async!
Just prefix the method with `async_`
(i.e. `await light.async_turn_on(...)`).

## Documentation

All documentation, API reference, contribution guidelines and pretty much everything else
you'd want to know is on our readthedocs site [here](https://homeassistantapi.readthedocs.io)

If there is something missing, open an issue and let us know! Thanks!

Go make some cool stuff! Maybe come back and tell us about it in a
[discussion](https://github.com/GrandMoff100/HomeAssistantAPI/discussions)?
We'd love to hear about how you use our library!!

## License

This project is under the GNU GPLv3 license, as defined by the Free Software Foundation.
