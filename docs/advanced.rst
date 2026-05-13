*******************
Advanced Section
*******************

Caching
**********

The packaged :py:class:`Client` and :py:class:`AsyncClient` do not come with any built-in caching.
A convenient option is to use the :py:class:`niquests_cache.session.CachedSession` or :py:class:`niquests_cache.session.AsyncCachedSession` classes from the `niquests_cache` library.


.. code-block:: python

    from homeassistant_api import Client

    from niquests_cache.session import CachedSession
    from niquests_cache.backend import MemoryBackend

    client = Client("<API_URL>", "<TOKEN>", session=CachedSession(backend=MemoryBackend(), expire_after=300))

.. code-block:: python

    from homeassistant_api import AsyncClient

    from niquests_cache.session import AsyncCachedSession
    from niquests_cache.backend import MemoryBackend

    client = AsyncClient("<API_URL>", "<TOKEN>", session=AsyncCachedSession(backend=MemoryBackend(), expire_after=300))


This creates an in-memory cache that expires after 300 seconds. You can adjust the `expire_after` value to fit your needs or set it to `-1` to disable expiration.
For more information on the available caching options, see the `niquests_cache <https://niquests-cache.readthedocs.io/en/stable/>`__ documentation.


Persistent Caching
********************

If you want your cache to persist between runs (e.g. to a filesystem), you can pass your own custom cached session via the :code:`session` parameter.

.. code-block:: python

    from pathlib import Path
    from homeassistant_api import Client
    from niquests_cache.session import CachedSession

    client = Client(
        "<API_URL>",
        "<TOKEN>",
        session=CachedSession(cache_name=Path('.cache') / 'http'),  # by default uses sqlite backend
    )

    with client:
        # Grab and update some cool entities and services inside your installation.
        ...

.. code-block:: python

    # Or an example for async
    import asyncio
    from pathlib import Path
    from homeassistant_api import AsyncClient
    from niquests_cache.session import AsyncCachedSession

    client = AsyncClient(
        "<API_URL>",
        "<TOKEN>",
        session=AsyncCachedSession(
            cache_name=Path('.cache') / 'http',
        ),
    )

    async def main():
        async with client:
            # Grab and update some cool entities and services inside your installation.
            ...

    asyncio.run(main())


Why is :py:class:`Client` a context manager?
********************************************************

The :py:class:`Client` is a context manager because it manages the underlying HTTP session and pings Home Assistant to make sure it's running.
You don't have to use the context manager — the client works without it — but you'll need to manage the session lifecycle yourself.
