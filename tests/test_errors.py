"""Module for making sure requests that should not succeed, do indeed fail."""

import json
import os
import unittest.mock
from typing import Dict

import aiohttp
import pytest
import requests
from multidict import CIMultiDict, CIMultiDictProxy

from homeassistant_api import Client, Domain, UnauthorizedError
from homeassistant_api.errors import (
    APIConfigurationError,
    BadTemplateError,
    EndpointNotFoundError,
    InternalServerError,
    MalformedDataError,
    MethodNotAllowedError,
    ProcessorNotFoundError,
    ResponseError,
    UnexpectedStatusCodeError,
)
from homeassistant_api.processing import Processing


def test_unauthorized() -> None:
    with pytest.raises(UnauthorizedError):
        with Client(os.environ["HOMEASSISTANTAPI_URL"], "lolthisisawrongtokenforsure"):
            pass


async def test_async_unauthorized() -> None:
    with pytest.raises(UnauthorizedError):
        async with Client(
            os.environ["HOMEASSISTANTAPI_URL"],
            "lolthisisawrongtokenforsure",
            use_async=True,
        ):
            pass


async def test_domain_missing_services_attribute(cached_client: Client) -> None:
    with pytest.raises(ValueError):
        Domain.from_json({"services": None}, client=cached_client)  # Missing domain
    with pytest.raises(ValueError):
        Domain.from_json({"domain": None}, client=cached_client)  # Missing services


def test_endpoint_not_found_error(cached_client: Client) -> None:
    with pytest.raises(EndpointNotFoundError):
        cached_client.request("qwertyuioasdfghjkzxcvbnm")


async def test_async_endpoint_not_found_error(async_cached_client: Client) -> None:
    with pytest.raises(EndpointNotFoundError):
        await async_cached_client.async_request("qwertyuioasdfghjkzxcvbnm")


def test_method_not_allowed_error(cached_client: Client) -> None:
    with pytest.raises(MethodNotAllowedError):
        cached_client.request("", method="DELETE")


async def test_async_method_not_allowed_error(async_cached_client: Client) -> None:
    with pytest.raises(MethodNotAllowedError):
        await async_cached_client.async_request("", method="DELETE")


def test_wrong_headers(cached_client: Client) -> None:
    with pytest.raises(ValueError):
        cached_client.request("", headers=1234567890)  # type: ignore[arg-type]


async def test_async_wrong_headers(async_cached_client: Client) -> None:
    with pytest.raises(ValueError):
        await async_cached_client.async_request("", headers=1234567890)  # type: ignore[arg-type]


def test_no_entity_information_provided(cached_client: Client) -> None:
    """Tests that the client raises an error if no entity information is provided."""
    with pytest.raises(ValueError):
        cached_client.get_entity()


async def test_async_no_entity_information_provided(
    async_cached_client: Client,
) -> None:
    """Tests that the client raises an error if no entity information is provided."""
    with pytest.raises(ValueError):
        await async_cached_client.async_get_entity()


def test_invalid_template(cached_client: Client) -> None:
    with pytest.raises(BadTemplateError):
        cached_client.get_rendered_template("{{ invalid_template lol")


async def test_async_invalid_template(async_cached_client: Client) -> None:
    with pytest.raises(BadTemplateError):
        await async_cached_client.async_get_rendered_template("{{ invalid_template lol")


def test_prepare_entity_id(cached_client: Client) -> None:
    """Tests all cases for :py:meth:`Client.prepare_entity_id`."""
    assert cached_client.prepare_entity_id(group_id="person", slug="me") == "person.me"
    assert cached_client.prepare_entity_id(entity_id="person.me") == "person.me"
    assert "person.you" == cached_client.prepare_entity_id(
        group_id="person",
        entity_id="person.you",
    )
    assert "person.you" == cached_client.prepare_entity_id(
        slug="me",
        entity_id="person.you",
    )
    with pytest.raises(ValueError):
        cached_client.prepare_entity_id(group_id="person")  # No slug
    with pytest.raises(ValueError):
        cached_client.prepare_entity_id(slug="me")  # No group
    with pytest.raises(ValueError):
        cached_client.prepare_entity_id()  # No entity_id


def make_response(
    status_code: int,
    content: str,
    headers: Dict[str, str],
) -> requests.Response:
    """Make a :py:class:`requests.Response` object from a status_code, headers, content."""
    return unittest.mock.Mock(
        spec=requests.Response,
        status_code=status_code,
        text=content,
        headers=CIMultiDictProxy(CIMultiDict(headers)),
        json=unittest.mock.Mock(
            side_effect=json.JSONDecodeError("This is a fake message", "", 1)
        ),
    )


def make_async_response(
    status_code: int,
    content: str,
    headers: Dict[str, str],
) -> aiohttp.ClientResponse:
    """Make an :py:class:`aiohttp.ClientResponse` object from a status_code, headers, content."""
    return unittest.mock.Mock(
        spec=aiohttp.ClientResponse,
        status=status_code,
        text=unittest.mock.AsyncMock(return_value=content),
        content=unittest.mock.Mock(_buffer=[content.encode()]),
        headers=CIMultiDictProxy(CIMultiDict(headers)),
        json=unittest.mock.AsyncMock(
            side_effect=json.JSONDecodeError("This is a fake message", "", 1)
        ),
    )


def test_exception_malformed_data_error() -> None:
    with pytest.raises(MalformedDataError):
        Processing(
            make_response(
                200,
                "{this is not valid json}",
                {"Content-Type": "application/json"},
            )
        ).process()


async def test_async_exception_malformed_data_error() -> None:
    with pytest.raises(MalformedDataError):
        await Processing(
            make_async_response(
                200,
                "{this is not valid json}",
                {"Content-Type": "application/json"},
            )
        ).process()


def test_exception_internal_server_error() -> None:
    with pytest.raises(InternalServerError):
        Processing(make_response(500, "", {})).process()


def test_exception_processor_not_found_error() -> None:
    with pytest.raises(ProcessorNotFoundError):
        Processing(
            make_response(200, "", {"Content-Type": "this_type/does-not-exist"})
        ).process()


def test_exception_api_config_error() -> None:
    with pytest.raises(APIConfigurationError):
        raise APIConfigurationError("(Fake) Server has invalid configuration.yaml")


def test_exception_response_error() -> None:
    with pytest.raises(ResponseError):
        raise ResponseError("(Fake) Server returned a problematic response.")


def test_exception_unexpected_status_code() -> None:
    with pytest.raises(UnexpectedStatusCodeError):
        Processing(make_response(0, "", {})).process()


def test_unkown_scheme(cached_client: Client) -> None:
    with pytest.raises(ValueError):
        cached_client.request("ftp://example.com")