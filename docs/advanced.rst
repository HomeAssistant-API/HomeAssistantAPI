*******************
Advanced Section
*******************

Persistent Caching
********************

Persistent caching is exactly what it means. It makes your requests cache persist or stay around between :py:class:`Client` objects, and between runs, and contexts (:code:`with client:` statements).
Rather than the default behavior, which is saving the cache to memory or not at all and erasing it after each context and run.


If you want to persist your requests cache you can pass your own custom cached session to :py:class:`Client`'s init method.
You can pass a variety of options to your cached session like how fast to expire the cache, where to cache it (the cache backend), and what to do when the cache is expired.

Depending on whether you are using this in an async or sync project you will want to use either :py:class:`aiohttp_client_cache.backends.CachedSession` or :py:class:`requests_cache.CachedSession` respectively.
See the docs for `requests_cache <https://requests-cache.readthedocs.io/en/latest/>`__ and `aiohttp_client_cache <https://aiohttp-client-cache.readthedocs.io/en/latest/>`__ for how to implement these backends, options, and much more.

You can simply pass them to your client like so.

.. code-block:: python

    from homeassistant_api import Client
    from requests_cache import CachedSession

    client = Client(
        "<API_URL>",
        "<TOKEN>",
        cache_session=CachedSession(
            backend="filesystem",
            expire_after=timedelta(minutes=5)
        )
    )

    # CachedSession is activated by the `with` statement.
    with client:
        # Grab and update some cool entities and services inside your installation.
        ...

    # Or an example for async
    import asyncio
    from homeassistant_api import Client
    from aiohttp_client_cache import CachedSession, FileBackend

    client = Client(
        "<URL>",
        "<TOKEN>",
        cache_session=CachedSession(
            cache=FileBackend(
                expire_after=timedelta(minutes=5)
            )
        ),
        use_async=True
    )
    async def main():
        async with client:
            # Grab and update some cool entities and services inside your installation.
            ...
    asyncio.run(main())


Why the heck is :py:class:`Client` a context manager?
********************************************************

The :py:class:`Client` is a context manager because it activates the cache session and pings Home Assistant to make sure its running.
You might not want this behavior, if you don't then don't use the :code:`with` or :code:`async with` statement.
You can still use the client without it, but you will have to manually activate the cache session before you use it.

Disabling Caching
******************

To explicitly disable the default cache you can pass :code:`cache_session=False` or :code:`async_cache_session=False` to :py:class:`Client`'s init method depending on your use case.
Otherwise the default cache will be used by default when you use :code:`with client:` or :code:`async with client:`.
