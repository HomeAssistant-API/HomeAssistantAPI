"""
Core cassette machinery: record and replay niquests HTTP and WebSocket interactions.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from http import HTTPStatus
from typing import TYPE_CHECKING
from typing import Any
from typing import Self
from unittest.mock import patch
from urllib.parse import urlparse

import niquests
from niquests import AsyncSession
from niquests import Response
from niquests import Session
from niquests.structures import CaseInsensitiveDict

from ._matchers import BUILTIN_MATCHERS
from ._matchers import BaseMatcher
from ._placeholders import Placeholder
from ._placeholders import apply_placeholders
from ._placeholders import restore_placeholders
from ._record_mode import RecordMode
from ._serializers import BaseSerializer
from ._serializers import JSONSerializer
from ._serializers import YAMLSerializer
from ._websocket import AsyncFakeExtension
from ._websocket import AsyncRecordingExtension
from ._websocket import FakeExtension
from ._websocket import RecordingExtension
from ._websocket import WebSocketSession

if TYPE_CHECKING:
    from pathlib import Path

NIMAX_VERSION = "0.1.0"

#: Supported matcher names.
SUPPORTED_MATCHERS: frozenset[str] = frozenset(BUILTIN_MATCHERS.keys())

#: Default matchers — path-only matching ignores dynamic query params.
DEFAULT_MATCH_ON: frozenset[str] = frozenset({"method", "path"})


# ── Helpers ───────────────────────────────────────────────────────────────────


def _is_ws(url: str) -> bool:
    return url.startswith(("ws://", "wss://"))


def _normalize_status(status: Any) -> dict[str, Any]:
    """Coerce status to ``{"code": int, "message": str}`` (handles legacy int form)."""
    if isinstance(status, dict):
        return status
    code = int(status)
    try:
        message = HTTPStatus(code).phrase
    except ValueError:
        message = ""
    return {"code": code, "message": message}


def _normalize_body(body: Any) -> dict[str, str] | None:
    """Coerce body to ``{"string": "..."}`` (handles legacy bare-string form)."""
    if body is None:
        return None
    if isinstance(body, dict):
        return body
    text = body if isinstance(body, str) else body.decode("utf-8", errors="replace")
    return {"string": text} if text else None


def _normalize_headers(headers: dict[str, Any]) -> dict[str, list[str]]:
    """Ensure all header values are lists of strings."""
    return {k: [v] if isinstance(v, str) else v for k, v in headers.items()}


def _migrate_interaction(entry: dict[str, Any]) -> dict[str, Any]:
    """Upgrade a legacy cassette entry to the current format in place."""
    req = dict(entry["request"])
    resp = dict(entry["response"])

    # request.url → request.uri
    if "url" in req and "uri" not in req:
        req["uri"] = req.pop("url")
    req.setdefault("headers", {})
    req.setdefault("body", None)

    resp["status"] = _normalize_status(resp.get("status", 200))
    resp["body"] = _normalize_body(resp.get("body"))
    resp["headers"] = _normalize_headers(resp.get("headers", {}))
    resp.setdefault("protocol", None)
    resp.setdefault("url", req.get("uri", ""))

    return {
        "request": req,
        "response": resp,
        "recorded_at": entry.get("recorded_at", ""),
    }


# ── Data model ────────────────────────────────────────────────────────────────


@dataclass
class Interaction:
    request: dict[str, Any]
    response: dict[str, Any]
    recorded_at: str
    used: bool = field(default=False, compare=False)


# ── Fake raw (replay WebSocket) ───────────────────────────────────────────────


class _FakeRaw:
    """Minimal stand-in for urllib3's HTTPResponse exposing just the extension."""

    def __init__(self, extension: Any) -> None:
        self.extension = extension


# ── Cassette ──────────────────────────────────────────────────────────────────


class Cassette:
    """
    Context manager that intercepts ``niquests.Session.send`` and
    ``niquests.AsyncSession.send`` to record or replay HTTP and WebSocket
    interactions.

    :param path:         Path to the cassette file (extension determines serializer
                         when *serializer* is ``None``).
    :param record_mode:  :class:`RecordMode` controlling when recording is allowed.
                         Defaults to ``ONCE``.
    :param match_on:     Set of matcher names used to find stored interactions.
                         Defaults to ``{"method", "path"}``.
    :param serializer:   Explicit serializer instance.  When ``None``, inferred from
                         *path* extension (``.yaml`` → YAML, otherwise JSON).
    :param placeholders: List of :class:`Placeholder` objects for value sanitization.
    :param record:       Deprecated boolean shorthand.  ``True`` → ``RecordMode.ALL``,
                         ``False`` → ``RecordMode.NONE``.
    """

    def __init__(  # noqa: PLR0913
        self,
        path: Path,
        *,
        record_mode: RecordMode = RecordMode.ONCE,
        match_on: frozenset[str] = DEFAULT_MATCH_ON,
        serializer: BaseSerializer | None = None,
        placeholders: list[Placeholder] | None = None,
        record: bool | None = None,
    ) -> None:
        # Backward-compat shim
        if record is not None:
            record_mode = RecordMode.ALL if record else RecordMode.NONE

        unknown = match_on - SUPPORTED_MATCHERS
        if unknown:
            msg = f"Unknown matcher(s): {unknown!r}. Supported: {SUPPORTED_MATCHERS!r}"
            raise ValueError(msg)

        self._path = path
        self._record_mode = record_mode
        self._matchers: list[BaseMatcher] = [
            BUILTIN_MATCHERS[name]() for name in match_on
        ]
        self._placeholders: list[Placeholder] = placeholders or []
        self._serializer: BaseSerializer = serializer or self._infer_serializer()

        self._interactions: list[Interaction] = []
        self._ws_sessions: list[WebSocketSession] = []
        self._lock = threading.Lock()
        self._patches: list[Any] = []

        # Determine whether this run is a recording pass
        if record_mode == RecordMode.NONE:
            self._recording_active = False
        elif record_mode == RecordMode.ONCE:
            self._recording_active = not path.exists()
        else:  # ALL, NEW_EPISODES
            self._recording_active = True

        if not self._recording_active:
            self._load()

    # ── Serializer inference ──────────────────────────────────────────────────

    def _infer_serializer(self) -> BaseSerializer:
        ext = self._path.suffix.lstrip(".")
        if ext == "yaml":
            return YAMLSerializer()
        return JSONSerializer()

    # ── Persistence ───────────────────────────────────────────────────────────

    def _load(self) -> None:
        if not self._path.exists():
            return
        raw = self._path.read_text(encoding="utf-8")
        if self._placeholders:
            raw = restore_placeholders(raw, self._placeholders)

        # Use YAML for .yaml files regardless of configured serializer
        ext = self._path.suffix.lstrip(".")
        if ext == "yaml":
            data: dict[str, Any] = YAMLSerializer().deserialize(raw)
        else:
            data = self._serializer.deserialize(raw)

        # Support both legacy "interactions" key and current "http_interactions"
        interactions_raw = data.get("http_interactions") or data.get("interactions", [])
        for entry in interactions_raw:
            migrated = _migrate_interaction(entry)
            self._interactions.append(
                Interaction(
                    request=migrated["request"],
                    response=migrated["response"],
                    recorded_at=migrated["recorded_at"],
                ),
            )

        for ws_entry in data.get("websocket_sessions", []):
            # Migrate legacy frame format (direction + payload only)
            frames_raw = ws_entry.get("frames", [])
            for f in frames_raw:
                f.setdefault("type", "text")
                f.setdefault("offset_ms", 0)
            self._ws_sessions.append(WebSocketSession.from_dict(ws_entry))

    def save(self) -> None:
        if not self._recording_active:
            return

        with self._lock:
            http_interactions = [
                {
                    "request": i.request,
                    "response": i.response,
                    "recorded_at": i.recorded_at,
                }
                for i in self._interactions
            ]
            ws_sessions = [ws.to_dict() for ws in self._ws_sessions]

        data: dict[str, Any] = {
            "nimax_version": NIMAX_VERSION,
            "http_interactions": http_interactions,
            "websocket_sessions": ws_sessions,
        }
        serialized = self._serializer.serialize(data)
        if self._placeholders:
            serialized = apply_placeholders(serialized, self._placeholders)

        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(serialized, encoding="utf-8")

    # ── Matching & recording ──────────────────────────────────────────────────

    def find_match(self, live_request: Any) -> Interaction | None:
        """Return the first unused stored interaction that satisfies all matchers."""
        with self._lock:
            for interaction in self._interactions:
                if interaction.used:
                    continue
                if all(
                    m.match(interaction.request, live_request) for m in self._matchers
                ):
                    interaction.used = True
                    return interaction
        return None

    def save_interaction(self, method: str, url: str, resp: Response) -> None:
        """Append a recorded HTTP interaction."""
        body_str = resp.text if resp._content else ""
        try:
            message = HTTPStatus(resp.status_code).phrase
        except ValueError:
            message = ""
        headers = _normalize_headers(dict(resp.headers))
        now = datetime.now(tz=timezone.utc).isoformat()
        interaction = Interaction(
            request={"method": method, "uri": url, "headers": {}, "body": None},
            response={
                "status": {"code": resp.status_code, "message": message},
                "headers": headers,
                "body": {"string": body_str} if body_str else None,
                "protocol": None,
                "url": url,
            },
            recorded_at=now,
        )
        with self._lock:
            self._interactions.append(interaction)

    def record_ws(self, url: str) -> tuple[WebSocketSession, float]:
        """Register a new WS session and return it with the monotonic start time."""
        now = datetime.now(tz=timezone.utc).isoformat()
        session = WebSocketSession(
            uri=url,
            handshake_recorded_at=now,
            protocol=None,
        )
        with self._lock:
            self._ws_sessions.append(session)
        return session, time.monotonic()

    def find_ws_session(self, url: str) -> WebSocketSession | None:
        """Return the first unclaimed WS session matching *url* by path."""
        parsed_path = urlparse(url).path
        with self._lock:
            for ws in self._ws_sessions:
                if urlparse(ws.uri).path == parsed_path and ws.claim():
                    return ws
        return None

    # ── Response construction ─────────────────────────────────────────────────

    def _build_response(self, interaction: Interaction, request: Any) -> Response:
        resp_data = interaction.response
        resp = Response()
        resp.status_code = _normalize_status(resp_data["status"])["code"]
        headers_raw = resp_data.get("headers", {})
        resp.headers = CaseInsensitiveDict(
            {k: (v[0] if isinstance(v, list) else v) for k, v in headers_raw.items()},
        )
        body_data = resp_data.get("body")
        if body_data is None:
            resp._content = b""
        elif isinstance(body_data, dict):
            resp._content = body_data.get("string", "").encode("utf-8")
        else:
            resp._content = (
                body_data.encode("utf-8")
                if isinstance(body_data, str)
                else bytes(body_data)
            )
        resp._content_consumed = True
        resp.encoding = "utf-8"
        resp.url = resp_data.get("url", "")
        resp.request = request
        return resp

    def _ws_response(
        self,
        url: str,
        ws_session: WebSocketSession,
        *,
        is_async: bool,
    ) -> Response:
        ext: Any = (
            AsyncFakeExtension(ws_session) if is_async else FakeExtension(ws_session)
        )
        resp = Response()
        resp.status_code = 101
        resp._content = b""
        resp._content_consumed = True
        resp.headers = CaseInsensitiveDict({"Upgrade": "websocket"})
        resp.encoding = "utf-8"
        resp.url = url
        resp.raw = _FakeRaw(ext)
        return resp

    # ── Send interceptors ─────────────────────────────────────────────────────

    def _make_sync_send(self, original: Any) -> Any:
        cassette = self

        def send(session_self: Session, request: Any, **kwargs: Any) -> Response:
            url = request.url or ""
            method = request.method or "GET"

            if _is_ws(url):
                if cassette._recording_active:
                    resp = original(session_self, request, **kwargs)
                    if resp.extension is not None:
                        ws_session, start = cassette.record_ws(url)
                        resp.raw._extension = RecordingExtension(
                            resp.extension,
                            ws_session,
                            start,
                        )
                    return resp
                ws_session = cassette.find_ws_session(url)
                if ws_session is None:
                    msg = (
                        f"No recorded WS session for {url!r}"
                        " — re-run with --record to update cassettes"
                    )
                    raise KeyError(msg)
                return cassette._ws_response(url, ws_session, is_async=False)

            match = cassette.find_match(request)
            if match is not None:
                return cassette._build_response(match, request)

            if cassette._recording_active:
                resp = original(session_self, request, **kwargs)
                cassette.save_interaction(method, url, resp)
                return resp

            msg = (
                f"No recorded response for {method} {url!r}"
                " — re-run with --record to update cassettes"
            )
            raise KeyError(msg)

        return send

    def _make_async_send(self, original: Any) -> Any:
        cassette = self

        async def send(
            session_self: AsyncSession,
            request: Any,
            **kwargs: Any,
        ) -> Response:
            url = request.url or ""
            method = request.method or "GET"

            if _is_ws(url):
                if cassette._recording_active:
                    resp = await original(session_self, request, **kwargs)
                    if resp.extension is not None:
                        ws_session, start = cassette.record_ws(url)
                        resp.raw._extension = AsyncRecordingExtension(
                            resp.extension,
                            ws_session,
                            start,
                        )
                    return resp
                ws_session = cassette.find_ws_session(url)
                if ws_session is None:
                    msg = (
                        f"No recorded WS session for {url!r}"
                        " — re-run with --record to update cassettes"
                    )
                    raise KeyError(msg)
                return cassette._ws_response(url, ws_session, is_async=True)

            match = cassette.find_match(request)
            if match is not None:
                return cassette._build_response(match, request)

            if cassette._recording_active:
                resp = await original(session_self, request, **kwargs)
                cassette.save_interaction(method, url, resp)
                return resp

            msg = (
                f"No recorded response for {method} {url!r}"
                " — re-run with --record to update cassettes"
            )
            raise KeyError(msg)

        return send

    # ── Context manager ───────────────────────────────────────────────────────

    def _start_patching(self) -> None:
        sync_orig = niquests.Session.send
        async_orig = niquests.AsyncSession.send
        self._patches = [
            patch.object(niquests.Session, "send", self._make_sync_send(sync_orig)),
            patch.object(
                niquests.AsyncSession,
                "send",
                self._make_async_send(async_orig),
            ),
        ]
        for p in self._patches:
            p.start()

    def _stop_patching(self) -> None:
        for p in self._patches:
            p.stop()
        self._patches = []

    def __enter__(self) -> Self:
        self._start_patching()
        return self

    def __exit__(self, *_: object) -> None:
        self._stop_patching()
        self.save()
