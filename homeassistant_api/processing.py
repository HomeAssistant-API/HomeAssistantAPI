"""Module for processing API responses from homeassistant."""

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from http import HTTPStatus
from typing import Any

import simplejson
from niquests import Response

from homeassistant_api.errors import EndpointNotFoundError
from homeassistant_api.errors import InternalServerError
from homeassistant_api.errors import MalformedDataError
from homeassistant_api.errors import MethodNotAllowedError
from homeassistant_api.errors import ProcessorNotFoundError
from homeassistant_api.errors import RequestError
from homeassistant_api.errors import UnauthorizedError
from homeassistant_api.errors import UnexpectedStatusCodeError

logger = logging.getLogger(__name__)

ResponseType = Response


@dataclass(frozen=True)
class ResponseInfo:
    """Extracted metadata from an HTTP response for status code validation."""

    status_code: int
    url: str
    method: str | None


# --- Status code validation ---


def _check_status(info: ResponseInfo, content: str) -> None:
    """Raise appropriate error for non-success status codes.

    Content is only used in error messages for 400/500+ responses.
    """
    if info.status_code in (HTTPStatus.OK, HTTPStatus.CREATED):
        return  # pragma: no cover
    if info.status_code == HTTPStatus.BAD_REQUEST:
        raise RequestError(content, url=info.url)
    if info.status_code == HTTPStatus.UNAUTHORIZED:
        raise UnauthorizedError
    if info.status_code == HTTPStatus.NOT_FOUND:
        raise EndpointNotFoundError(info.url)
    if info.status_code == HTTPStatus.METHOD_NOT_ALLOWED:
        raise MethodNotAllowedError(info.method or "UNKNOWN")
    if info.status_code >= HTTPStatus.INTERNAL_SERVER_ERROR:
        raise InternalServerError(info.status_code, content)
    raise UnexpectedStatusCodeError(info.status_code)


def _extract_info(response: ResponseType) -> ResponseInfo:
    """Extract status code, URL, and method from a response."""
    if response.status_code is None:
        msg = "Response is missing status code."
        raise ValueError(msg)
    if response.request is None:
        msg = "Response is missing request information."
        raise ValueError(msg)
    if response.url is None:
        msg = "Response is missing URL information."
        raise ValueError(msg)
    return ResponseInfo(
        status_code=response.status_code,
        url=response.url,
        method=response.request.method,
    )


def _check_sync_status(response: ResponseType) -> None:
    """Validate a response status code, lazily reading content only on error."""
    info = _extract_info(response)
    if info.status_code in (HTTPStatus.OK, HTTPStatus.CREATED):
        return
    _check_status(info, content=_parse_text(response))


# --- Individual parse functions ---


def _parse_json(response: ResponseType) -> Any:
    """Parse a sync response as JSON."""
    try:
        return response.json()
    except (json.JSONDecodeError, simplejson.JSONDecodeError) as err:
        msg = f"Home Assistant responded with non-json response: {response.text!r}"
        raise MalformedDataError(msg) from err


def _parse_text(response: ResponseType) -> str:
    """Return the plaintext content of a sync response."""
    if response.text is None:
        msg = "Response is missing text content."
        raise MalformedDataError(msg)
    return response.text


# --- MIME dispatch table ---

_PARSERS: dict[str, Callable[[ResponseType], Any]] = {
    "application/json": _parse_json,
    "text/plain": _parse_text,
    "application/octet-stream": _parse_text,
}


# --- Content dispatch ---


def _parse_content(response: ResponseType) -> Any:
    """Look up and call the appropriate parser by content-type."""
    content_type = response.headers.get("content-type", "text/plain")
    if isinstance(content_type, bytes):
        content_type = content_type.decode("utf-8")  # pragma: no cover
    mimetype = str(content_type).split(";")[0].strip().lower()

    if (parser := _PARSERS.get(mimetype)) is None:
        msg = f"No response processor found for mimetype {mimetype!r}."
        raise ProcessorNotFoundError(msg)
    return parser(response)


# --- Top-level entry points ---


def process_response(response: ResponseType) -> Any:
    """Process a sync HTTP response: validate status, then parse content."""
    _check_sync_status(response)
    return _parse_content(response)


async def async_process_response(response: ResponseType) -> Any:
    """Process an async HTTP response: validate status, then parse content."""
    return process_response(response)
