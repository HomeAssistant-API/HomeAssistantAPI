import asyncio
import os

from homeassistant_api import AsyncClient

url = os.getenv("HOMEASSISTANT_API_ENDPOINT")
token = os.getenv("HOMEASSISTANT_API_TOKEN")


async def main() -> None:
    # Initialize main object
    client = AsyncClient(url, token)
    # Uses async context manager to ping the server and initialize caching.
    async with client:
        # All async methods are prefixed with `async_`.
        await client.get_entities()


loop = asyncio.get_event_loop()
loop.run_until_complete(main())
