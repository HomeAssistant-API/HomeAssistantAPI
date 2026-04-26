"""Unit tests for WebsocketClient, AsyncWebsocketClient error paths."""

from typing import Any

import pytest
from _pytest.monkeypatch import MonkeyPatch

from homeassistant_api.asyncwebsocket import AsyncWebsocketClient
from homeassistant_api.errors import ReceivingError
from homeassistant_api.errors import ResponseError
from homeassistant_api.models import websocket as ws_models
from homeassistant_api.websocket import WebsocketClient


def make_sync_client() -> WebsocketClient:
    """Create a WebsocketClient without connecting."""
    return WebsocketClient("ws://localhost:8123/api/websocket", "fake_token")


def make_async_client() -> AsyncWebsocketClient:
    """Create an AsyncWebsocketClient without connecting."""
    return AsyncWebsocketClient("ws://localhost:8123/api/websocket", "fake_token")


def test_exit_without_connection() -> None:
    """Tests __exit__ raises AttributeError when used outside context manager."""
    client = make_sync_client()
    with pytest.raises(AttributeError):
        client.__exit__(None, None, None)


def test_send_without_connection() -> None:
    """Tests _send raises AttributeError when used outside context manager."""
    client = make_sync_client()
    with pytest.raises(AttributeError):
        client._send({"type": "test"})


def test_recv_without_connection() -> None:
    """Tests _recv raises AttributeError when used outside context manager."""
    client = make_sync_client()
    with pytest.raises(AttributeError):
        client._recv()


def test_handle_recv_message_without_id() -> None:
    """Tests handle_recv raises ReceivingError for messages missing an id."""
    client = make_sync_client()
    with pytest.raises(ReceivingError, match="without an id"):
        client.handle_recv({"type": "result", "success": True})


def test_parse_response_error_result() -> None:
    """Tests parse_response raises ResponseError for failed result messages."""
    client = make_sync_client()
    client._result_responses[1] = None
    with pytest.raises(ResponseError):
        client.parse_response(
            {
                "id": 1,
                "type": "result",
                "success": False,
                "error": {"code": "not_found", "message": "Entity not found"},
            },
        )


def test_parse_response_unexpected_type() -> None:
    """Tests parse_response raises ReceivingError for unknown message types."""
    client = make_sync_client()
    with pytest.raises(ReceivingError, match="unexpected message type"):
        client.parse_response({"id": 1, "type": "unknown_type"})


def test_authentication_phase_invalid_welcome(monkeypatch: MonkeyPatch) -> None:
    """Tests authentication_phase raises ResponseError on invalid welcome message."""
    client = make_sync_client()
    monkeypatch.setattr(client, "_recv", lambda: {"type": "not_auth_required"})
    with pytest.raises(
        ResponseError,
        match="Unexpected response during authentication",
    ):
        client.authentication_phase()


def test_authentication_phase_unexpected_auth_response(
    monkeypatch: MonkeyPatch,
) -> None:
    """Tests authentication_phase raises ResponseError when AuthOk.model_validate raises a non-ValidationError."""
    call_count = 0

    def fake_recv():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return {"type": "auth_required", "ha_version": "2024.1.0"}
        return {"type": "auth_ok", "ha_version": "2024.1.0", "message": "unexpected"}

    client = make_sync_client()
    monkeypatch.setattr(client, "_recv", fake_recv)
    monkeypatch.setattr(client, "_send", lambda _: None)

    # Patch AuthOk.model_validate to raise a non-ValidationError exception

    def raise_runtime_error(*args: Any, **kwargs: Any):  # noqa: ARG001
        msg = "something went wrong"
        raise RuntimeError(msg)

    monkeypatch.setattr(ws_models.AuthOk, "model_validate", raise_runtime_error)

    with pytest.raises(
        ResponseError,
        match="Unexpected response during authentication",
    ):
        client.authentication_phase()


async def test_async_aexit_without_connection() -> None:
    """Tests __aexit__ raises AttributeError when used outside context manager."""
    client = make_async_client()
    with pytest.raises(AttributeError):
        await client.__aexit__(None, None, None)


async def test_async_send_without_connection() -> None:
    """Tests _async_send raises AttributeError when used outside context manager."""
    client = make_async_client()
    with pytest.raises(AttributeError):
        await client._async_send({"type": "test"})


async def test_async_recv_without_connection() -> None:
    """Tests _async_recv raises AttributeError when used outside context manager."""
    client = make_async_client()
    with pytest.raises(AttributeError):
        await client._async_recv()


async def test_async_authentication_phase_invalid_welcome(
    monkeypatch: MonkeyPatch,
) -> None:
    """Tests authentication_phase raises ResponseError on invalid welcome message."""
    client = make_async_client()

    async def fake_recv():
        return {"type": "not_auth_required"}

    monkeypatch.setattr(client, "_async_recv", fake_recv)
    with pytest.raises(
        ResponseError,
        match="Unexpected response during authentication",
    ):
        await client.authentication_phase()


async def test_async_authentication_phase_unexpected_auth_response(
    monkeypatch: MonkeyPatch,
) -> None:
    """Tests authentication_phase raises ResponseError when AuthOk.model_validate raises a non-ValidationError."""
    call_count = 0

    async def fake_recv():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return {"type": "auth_required", "ha_version": "2024.1.0"}
        return {"type": "auth_ok", "ha_version": "2024.1.0", "message": "unexpected"}

    client = make_async_client()
    monkeypatch.setattr(client, "_async_recv", fake_recv)

    async def fake_send(data: Any):
        pass

    monkeypatch.setattr(client, "_async_send", fake_send)

    def raise_runtime_error(*args: Any, **kwargs: Any) -> None:  # noqa: ARG001
        msg = "something went wrong"
        raise RuntimeError(msg)

    monkeypatch.setattr(ws_models.AuthOk, "model_validate", raise_runtime_error)

    with pytest.raises(
        ResponseError,
        match="Unexpected response during authentication",
    ):
        await client.authentication_phase()
