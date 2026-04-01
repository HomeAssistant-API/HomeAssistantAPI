"""Module for making sure requests that should not succeed, do indeed fail."""

import json
import os
import unittest.mock
from http import HTTPMethod

import aiohttp
import pytest
import requests
from multidict import CIMultiDict
from multidict import CIMultiDictProxy

from homeassistant_api import AsyncClient
from homeassistant_api import AsyncWebsocketClient
from homeassistant_api import Client
from homeassistant_api import Domain
from homeassistant_api import WebsocketClient
from homeassistant_api.errors import APIConfigurationError
from homeassistant_api.errors import BadTemplateError
from homeassistant_api.errors import EndpointNotFoundError
from homeassistant_api.errors import InternalServerError
from homeassistant_api.errors import MalformedDataError
from homeassistant_api.errors import MethodNotAllowedError
from homeassistant_api.errors import ProcessorNotFoundError
from homeassistant_api.errors import RequestError
from homeassistant_api.errors import RequestTimeoutError
from homeassistant_api.errors import ResponseError
from homeassistant_api.errors import UnauthorizedError
from homeassistant_api.errors import UnexpectedStatusCodeError
from homeassistant_api.models.websocket import Error
from homeassistant_api.processing import Processing
from homeassistant_api.utils import prepare_entity_id

HA_URL = os.environ["HOMEASSISTANTAPI_URL"]
HA_WS_URL = os.environ["HOMEASSISTANTAPI_WS_URL"]
WRONG_TOKEN = "lolthisisawrongtokenforsure"  # noqa: S105


def test_unauthorized() -> None:
    with pytest.raises(UnauthorizedError), Client(HA_URL, WRONG_TOKEN):
        pass


def test_websocket_unauthorized() -> None:
    with pytest.raises(UnauthorizedError), WebsocketClient(HA_WS_URL, WRONG_TOKEN):
        pass


async def test_async_websocket_unauthorized() -> None:
    with pytest.raises(UnauthorizedError):
        async with AsyncWebsocketClient(HA_WS_URL, WRONG_TOKEN):
            pass


async def test_async_unauthorized() -> None:
    with pytest.raises(UnauthorizedError):
        async with AsyncClient(HA_URL, WRONG_TOKEN):
            pass


async def test_domain_missing_services_attribute(cached_client: Client) -> None:
    with pytest.raises(NotImplementedError, match="does not support `from_json\\(\\)`"):
        Domain.from_json({"services": None}, client=cached_client)  # Missing domain
    with pytest.raises(NotImplementedError, match="does not support `from_json\\(\\)`"):
        Domain.from_json({"domain": None}, client=cached_client)  # Missing services


def test_endpoint_not_found_error(cached_client: Client) -> None:
    with pytest.raises(EndpointNotFoundError):
        cached_client.request("qwertyuioasdfghjkzxcvbnm")


async def test_async_endpoint_not_found_error(async_cached_client: AsyncClient) -> None:
    with pytest.raises(EndpointNotFoundError):
        await async_cached_client.request("qwertyuioasdfghjkzxcvbnm")


def test_method_not_allowed_error(cached_client: Client) -> None:
    with pytest.raises(MethodNotAllowedError):
        cached_client.request("", method=HTTPMethod.DELETE)


async def test_async_method_not_allowed_error(async_cached_client: AsyncClient) -> None:
    with pytest.raises(MethodNotAllowedError):
        await async_cached_client.request("", method=HTTPMethod.DELETE)


def test_wrong_headers(cached_client: Client) -> None:
    with pytest.raises(TypeError):
        cached_client.request("", headers=1234567890)  # type: ignore[arg-type]


async def test_async_wrong_headers(async_cached_client: AsyncClient) -> None:
    with pytest.raises(TypeError):
        await async_cached_client.request("", headers=1234567890)  # type: ignore[arg-type]


def test_no_entity_information_provided(cached_client: Client) -> None:
    """Tests that the client raises an error if no entity information is provided."""
    with pytest.raises(
        ValueError,
        match="Neither group_id and slug or entity_id provided",
    ):
        cached_client.get_entity()


async def test_async_no_entity_information_provided(
    async_cached_client: AsyncClient,
) -> None:
    """Tests that the client raises an error if no entity information is provided."""
    with pytest.raises(
        ValueError,
        match=r"Neither group_id and slug or entity_id provided",
    ):
        await async_cached_client.get_entity()


def test_invalid_template(cached_client: Client) -> None:
    with pytest.raises(BadTemplateError):
        cached_client.get_rendered_template("{{ invalid_template lol")


async def test_async_invalid_template(async_cached_client: AsyncClient) -> None:
    with pytest.raises(BadTemplateError):
        await async_cached_client.get_rendered_template("{{ invalid_template lol")


def test_prepare_entity_id() -> None:
    """Tests all cases for :py:meth:`Client.prepare_entity_id`."""
    assert prepare_entity_id(group_id="person", slug="me") == "person.me"
    assert prepare_entity_id(entity_id="person.me") == "person.me"
    assert (
        prepare_entity_id(
            group_id="person",
            entity_id="person.you",
        )
        == "person.you"
    )
    assert (
        prepare_entity_id(
            slug="me",
            entity_id="person.you",
        )
        == "person.you"
    )
    with pytest.raises(ValueError, match="pass both, not just one"):
        prepare_entity_id(group_id="person")  # No slug
    with pytest.raises(ValueError, match="pass both, not just one"):
        prepare_entity_id(slug="me")  # No group
    with pytest.raises(ValueError, match="pass both, not just one"):
        prepare_entity_id()  # No entity_id


def make_response(
    status_code: int,
    content: str,
    headers: dict[str, str],
) -> requests.Response:
    """Make a :py:class:`requests.Response` object from a status_code, headers, content."""
    return unittest.mock.Mock(
        spec=requests.Response,
        status_code=status_code,
        text=content,
        headers=CIMultiDictProxy(CIMultiDict(headers)),
        json=unittest.mock.Mock(
            side_effect=json.JSONDecodeError("This is a fake message", "", 1),
        ),
    )


def make_async_response(
    status_code: int,
    content: str,
    headers: dict[str, str],
) -> aiohttp.ClientResponse:
    """Make an :py:class:`aiohttp.ClientResponse` object from a status_code, headers, content."""
    return unittest.mock.Mock(
        spec=aiohttp.ClientResponse,
        status=status_code,
        text=unittest.mock.AsyncMock(return_value=content),
        content=unittest.mock.Mock(_buffer=[content.encode()]),
        headers=CIMultiDictProxy(CIMultiDict(headers)),
        json=unittest.mock.AsyncMock(
            side_effect=json.JSONDecodeError("This is a fake message", "", 1),
        ),
    )


def test_exception_malformed_data_error() -> None:
    with pytest.raises(MalformedDataError):
        Processing(
            make_response(
                200,
                "{this is not valid json}",
                {"Content-Type": "application/json"},
            ),
        ).process()


async def test_async_exception_malformed_data_error() -> None:
    with pytest.raises(MalformedDataError):
        await Processing(
            make_async_response(
                200,
                "{this is not valid json}",
                {"Content-Type": "application/json"},
            ),
        ).process()


def test_exception_internal_server_error() -> None:
    with pytest.raises(InternalServerError):
        Processing(make_response(500, "", {})).process()


def test_exception_processor_not_found_error() -> None:
    with pytest.raises(ProcessorNotFoundError):
        Processing(
            make_response(200, "", {"Content-Type": "this_type/does-not-exist"}),
        ).process()


def test_exception_api_config_error() -> None:
    msg = "(Fake) Server has invalid configuration.yaml"
    with pytest.raises(APIConfigurationError):
        raise APIConfigurationError(msg)


def test_exception_response_error() -> None:
    msg = "(Fake) Server returned a problematic response."
    with pytest.raises(ResponseError):
        raise ResponseError(msg)


def test_exception_unexpected_status_code() -> None:
    with pytest.raises(UnexpectedStatusCodeError):
        Processing(make_response(0, "", {})).process()


def test_unkown_scheme() -> None:
    with pytest.raises(ValueError, match="Unknown scheme"):
        Client("ftp://example.com", "token")


def test_request_error_with_message_and_data() -> None:
    """Tests RequestError when both message and data are provided."""
    err = RequestError(
        "some_data",
        url="http://localhost/api",
        message="Custom message",
    )
    assert "Custom message" in str(err)
    assert "'http://localhost/api'" in str(err)
    assert "'some_data'" in str(err)


def test_request_error_no_data() -> None:
    """Tests RequestError when data is None and no message."""
    err = RequestError(None, url="http://localhost/api")
    assert "'http://localhost/api'" in str(err)
    assert "data" not in str(err)


def test_request_timeout_error() -> None:
    """Tests RequestTimeoutError constructor."""
    err = RequestTimeoutError("Connection timed out", url="http://localhost/api")
    assert "Connection timed out" in str(err)
    assert "'http://localhost/api'" in str(err)
    assert isinstance(err, RequestError)


def test_websocket_invalid_scheme() -> None:
    """Tests that WebsocketClient raises ValueError for non-ws schemes."""
    with pytest.raises(ValueError, match="Unknown scheme"):
        WebsocketClient("http://localhost", "token")


def test_error_model_without_optional_fields() -> None:
    """Tests that Error model accepts responses missing optional translation fields."""
    error = Error(code="invalid_format", message="required key not provided")
    assert error.code == "invalid_format"
    assert error.translation_key is None
    assert error.translation_placeholders is None
    assert error.translation_domain is None
