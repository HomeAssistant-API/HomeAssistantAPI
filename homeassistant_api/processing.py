"""Module for processing API responses from homeassistant."""

import inspect
import json
import logging
from typing import Any, Callable, ClassVar, Dict, Tuple, Union, cast

import simplejson
from aiohttp import ClientResponse
from aiohttp_client_cache.response import CachedResponse as AsyncCachedResponse
from requests import Response
from requests_cache.models.response import CachedResponse

from homeassistant_api.errors import (
    EndpointNotFoundError,
    InternalServerError,
    MalformedDataError,
    MethodNotAllowedError,
    ProcessorNotFoundError,
    RequestError,
    UnauthorizedError,
    UnexpectedStatusCodeError,
)
from homeassistant_api.utils import JSONType

logger = logging.getLogger(__name__)


AsyncResponseType = Union[AsyncCachedResponse, ClientResponse]
ResponseType = Union[Response, CachedResponse]
AllResponseType = Union[AsyncCachedResponse, ClientResponse, Response, CachedResponse]
ProcessorType = Callable[[AllResponseType], Any]


class Processing:
    """Uses to processor functions to convert json data into common python data types."""

    _response: AllResponseType
    _processors: ClassVar[Dict[str, Tuple[ProcessorType, ...]]] = {}

    def __init__(self, response: AllResponseType, decode_bytes: bool = True) -> None:
        self._response = response
        self._decode_bytes = decode_bytes

    @staticmethod
    def processor(mimetype: str) -> Callable[[ProcessorType], ProcessorType]:
        """A decorator used to register a response converter function."""

        def register_processor(processor: ProcessorType) -> ProcessorType:
            if mimetype not in Processing._processors:
                Processing._processors[mimetype] = tuple()
            Processing._processors[mimetype] += (processor,)
            return processor

        return register_processor

    def process_content(self, *, async_: bool = False) -> Any:
        """
        Looks up processors by their Content-Type header and then
        calls the processor with the response.
        """

        mimetype_header = self._response.headers.get(
            "content-type",
            "text/plain",
        )
        mimetype = mimetype_header.split(";")[0]
        for processor in self._processors.get(mimetype, ()):
            if not async_ ^ inspect.iscoroutinefunction(processor):
                logger.debug("Using processor %r on %r", processor, self._response)
                return processor(self._response)
        raise ProcessorNotFoundError(
            f"No response processor found for mimetype {mimetype!r}."
        )

    def process(self) -> Any:
        """Validates the http status code before starting to process the repsonse content"""
        content: Union[str, bytes]
        if async_ := isinstance(self._response, (ClientResponse, AsyncCachedResponse)):
            status_code = self._response.status
            _buffer = self._response.content._buffer
            content = b"" if not _buffer else _buffer[0]
        elif isinstance(self._response, (Response, CachedResponse)):
            status_code = self._response.status_code
            content = self._response.content
        else:
            raise TypeError(
                f"Unsupported response type: {type(self._response).__name__}"
            )
        if self._decode_bytes and isinstance(content, bytes):
            content = content.decode()
        if status_code in (200, 201):
            return self.process_content(async_=async_)
        if status_code == 400:
            raise RequestError(content, url=self._response.url)  # type: ignore
        if status_code == 401:
            raise UnauthorizedError()
        if status_code == 404:
            raise EndpointNotFoundError(self._response.url)  # type: ignore
        if status_code == 405:
            if isinstance(self._response, (Response, CachedResponse)):
                method = self._response.request.method
            else:
                method = self._response.method
            raise MethodNotAllowedError(cast(str, method))
        if status_code >= 500:
            raise InternalServerError(status_code, content)
        raise UnexpectedStatusCodeError(status_code)


# List of default processors
@Processing.processor("application/json")  # type: ignore[arg-type]
def process_json(response: ResponseType) -> dict[str, JSONType]:
    """Returns the json dict content of the response."""
    try:
        return cast(dict[str, JSONType], response.json())
    except (json.JSONDecodeError, simplejson.JSONDecodeError) as err:
        raise MalformedDataError(
            f"Home Assistant responded with non-json response: {repr(response.text)}"
        ) from err


@Processing.processor("text/plain")  # type: ignore[arg-type]
@Processing.processor("application/octet-stream")  # type: ignore[arg-type]
def process_text(response: ResponseType) -> str:
    """Returns the plaintext of the reponse."""
    return response.text


@Processing.processor("application/json")  # type: ignore[arg-type]
async def async_process_json(response: AsyncResponseType) -> dict[str, JSONType]:
    """Returns the json dict content of the response."""
    try:
        return cast(dict[str, JSONType], await response.json())
    except (json.JSONDecodeError, simplejson.JSONDecodeError) as err:
        raise MalformedDataError(
            f"Home Assistant responded with non-json response: {repr(await response.text())}"
        ) from err


@Processing.processor("text/plain")  # type: ignore[arg-type]
@Processing.processor("application/octet-stream")  # type: ignore[arg-type]
async def async_process_text(response: AsyncResponseType) -> str:
    """Returns the plaintext of the reponse."""
    return await response.text()
