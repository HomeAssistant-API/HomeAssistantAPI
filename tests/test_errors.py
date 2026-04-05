"""Module for making sure requests that should not succeed, do indeed fail."""

import json
import os
import unittest.mock
from http import HTTPMethod

import niquests
import pytest
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
from homeassistant_api.models.states import State
from homeassistant_api.models.websocket import Error
from homeassistant_api.processing import async_process_response
from homeassistant_api.processing import process_response
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
) -> niquests.Response:
    """Make a :py:class:`niquests.Response` object from a status_code, headers, content."""
    return unittest.mock.Mock(
        spec=niquests.Response,
        status_code=status_code,
        text=content,
        url="http://localhost/api/test",
        request=unittest.mock.Mock(method="GET"),
        headers=CIMultiDictProxy(CIMultiDict(headers)),
        json=unittest.mock.Mock(
            side_effect=json.JSONDecodeError("This is a fake message", "", 1),
        ),
    )


def make_async_response(
    status_code: int,
    content: str,
    headers: dict[str, str],
) -> niquests.Response:
    """Make a :py:class:`niquests.Response` mock for async processing tests."""
    return unittest.mock.Mock(
        spec=niquests.Response,
        status_code=status_code,
        text=content,
        url="http://localhost/api/test",
        request=unittest.mock.Mock(method="GET"),
        headers=CIMultiDictProxy(CIMultiDict(headers)),
        json=unittest.mock.Mock(
            side_effect=json.JSONDecodeError("This is a fake message", "", 1),
        ),
    )


def test_exception_malformed_data_error() -> None:
    with pytest.raises(MalformedDataError):
        process_response(
            make_response(
                200,
                "{this is not valid json}",
                {"Content-Type": "application/json"},
            ),
        )


async def test_async_exception_malformed_data_error() -> None:
    with pytest.raises(MalformedDataError):
        await async_process_response(
            make_async_response(
                200,
                "{this is not valid json}",
                {"Content-Type": "application/json"},
            ),
        )


def test_exception_internal_server_error() -> None:
    with pytest.raises(InternalServerError):
        process_response(make_response(500, "", {}))


def test_exception_processor_not_found_error() -> None:
    with pytest.raises(ProcessorNotFoundError):
        process_response(
            make_response(200, "", {"Content-Type": "this_type/does-not-exist"}),
        )


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
        process_response(make_response(0, "", {}))


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
    assert (
        str(err)
        == "An error occurred while making the request to 'http://localhost/api'"
    )


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


# --- Processing: async processor not found ---


async def test_async_exception_processor_not_found_error() -> None:
    """Tests that async_process_response raises ProcessorNotFoundError for unknown MIME types."""
    with pytest.raises(ProcessorNotFoundError, match="this_type/does-not-exist"):
        await async_process_response(
            make_async_response(200, "", {"Content-Type": "this_type/does-not-exist"}),
        )


async def test_async_exception_bad_request() -> None:
    """Tests that async_process_response raises RequestError for 400 responses."""
    with pytest.raises(RequestError):
        await async_process_response(
            make_async_response(400, "bad request data", {}),
        )


async def test_async_exception_internal_server_error() -> None:
    """Tests that async_process_response raises InternalServerError for 500 responses."""
    with pytest.raises(InternalServerError):
        await async_process_response(make_async_response(500, "server broke", {}))


async def test_async_exception_unexpected_status_code() -> None:
    """Tests that async_process_response raises UnexpectedStatusCodeError for unknown status."""
    with pytest.raises(UnexpectedStatusCodeError):
        await async_process_response(make_async_response(0, "", {}))


# --- WebSocket: NotImplementedError stubs ---


def test_websocket_set_state_not_supported(websocket_client: WebsocketClient) -> None:
    """Tests that WebsocketClient.set_state raises NotImplementedError."""
    state = State(state="test", entity_id="sun.sun")
    with pytest.raises(
        NotImplementedError,
        match="not supported over the WebSocket API",
    ):
        websocket_client.set_state(state)


def test_websocket_get_entity_histories_not_supported(
    websocket_client: WebsocketClient,
) -> None:
    """Tests that WebsocketClient.get_entity_histories raises NotImplementedError."""
    with pytest.raises(
        NotImplementedError,
        match="not supported over the WebSocket API",
    ):
        list(websocket_client.get_entity_histories())


async def test_async_websocket_set_state_not_supported(
    async_websocket_client: AsyncWebsocketClient,
) -> None:
    """Tests that AsyncWebsocketClient.set_state raises NotImplementedError."""
    state = State(state="test", entity_id="sun.sun")
    with pytest.raises(
        NotImplementedError,
        match="not supported over the WebSocket API",
    ):
        await async_websocket_client.set_state(state)


async def test_async_websocket_get_entity_histories_not_supported(
    async_websocket_client: AsyncWebsocketClient,
) -> None:
    """Tests that AsyncWebsocketClient.get_entity_histories raises NotImplementedError."""
    with pytest.raises(
        NotImplementedError,
        match="not supported over the WebSocket API",
    ):
        async for _ in async_websocket_client.get_entity_histories():
            pass


def test_client_default_session() -> None:
    """Tests that Client creates a niquests.Session by default."""
    token = os.environ["HOMEASSISTANTAPI_TOKEN"]
    client = Client(HA_URL, token)
    assert isinstance(client._session, niquests.Session)


async def test_async_client_default_session() -> None:
    """Tests that AsyncClient creates a niquests.AsyncSession by default."""
    token = os.environ["HOMEASSISTANTAPI_TOKEN"]
    client = AsyncClient(HA_URL, token)
    assert isinstance(client._session, niquests.AsyncSession)
