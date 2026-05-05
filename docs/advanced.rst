*******************
Advanced Section
*******************

Caching
**********

By default, caching is **disabled**. You can enable the built-in in-memory cache by passing :code:`use_cache=True`:

.. code-block:: python

    from homeassistant_api import Client

    client = Client("<API_URL>", "<TOKEN>", use_cache=True)

This creates an in-memory cache that expires after 300 seconds.

Persistent Caching
********************

If you want your cache to persist between runs (e.g. to a filesystem), you can pass your own custom cached session via the :code:`session` parameter.

Depending on whether you are using a sync or async client you will want to use either :py:class:`niquests_cache.session.CachedSession` or :py:class:`niquests_cache.session.AsyncCachedSession` respectively.
See the docs for `niquests_cache <https://niquests-cache.readthedocs.io/en/stable/#example-usage>`__ for backend options and more.

.. code-block:: python

    from datetime import timedelta
    from homeassistant_api import Client
    from niquests_cache.session import CachedSession

    client = Client(
        "<API_URL>",
        "<TOKEN>",
        session=CachedSession(cache_name=Path('.cache') / 'http'),  # defaults to sqlite cache
    )

    with client:
        # Grab and update some cool entities and services inside your installation.
        ...

.. code-block:: python

    # Or an example for async
    import asyncio
    from datetime import timedelta
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
