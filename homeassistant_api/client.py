"""Module containing the primary Client class."""

import logging
from typing import Any
import urllib.parse as urlparse
import warnings

from .rawasyncclient import RawAsyncClient
from .rawclient import RawClient

logger = logging.getLogger(__name__)


class Client(RawClient, RawAsyncClient):
    """
    The all-in-one class to interact with Home Assistant!

    :param api_url: The location of the api endpoint. e.g. :code:`http://localhost:8123/api` Required.
    :param token: The refresh or long lived access token to authenticate your requests. Required.
    :param global_request_kwargs: A dictionary or dict-like object of kwargs to pass to :func:`requests.request` or :meth:`aiohttp.ClientSession.request`. Optional.
    :param cache_session: A :py:class:`requests_cache.CachedSession` object to use for caching requests. Optional.
    :param async_cache_session: A :py:class:`aiohttp_client_cache.CachedSession` object to use for caching requests. Optional.
    """  # pylint: disable=line-too-long

    def __init__(
        self,
        api_url: str,
        token: str,
        use_async: bool = False,
        verify_ssl: bool = True,
        **kwargs: Any,
    ) -> None:
        parsed = urlparse.urlparse(api_url)

        if parsed.scheme in {"http", "https"}:
            if use_async:
                RawAsyncClient.__init__(
                    self, api_url, token, verify_ssl=verify_ssl, **kwargs
                )
            else:
                RawClient.__init__(
                    self, api_url, token, verify_ssl=verify_ssl, **kwargs
                )
            warnings.warn(
                "The REST API is being phased out and will be removed in a far future release. Please use the WebSocket API instead.",
                DeprecationWarning,
            )
        else:
            raise ValueError(f"Unknown scheme {parsed.scheme} in {api_url}")
