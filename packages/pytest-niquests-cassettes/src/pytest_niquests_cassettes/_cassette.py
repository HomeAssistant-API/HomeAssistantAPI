"""
Core cassette machinery: record and replay niquests HTTP and WebSocket interactions.
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING
from typing import Any
from typing import Self

if TYPE_CHECKING:
    from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlparse

import niquests
import yaml
from niquests import AsyncSession
from niquests import Response
from niquests import Session
from niquests.structures import CaseInsensitiveDict

# ── URL utilities ────────────────────────────────────────────────────────────

#: Supported matcher names and the URL component each one examines.
SUPPORTED_MATCHERS: frozenset[str] = frozenset({"method", "host", "path", "query"})

#: Default matchers — path-only matching ignores dynamic query params (timestamps, etc.)
DEFAULT_MATCH_ON: frozenset[str] = frozenset({"method", "path"})


def _http_key(
    method: str,
    url: str,
    match_on: frozenset[str] = DEFAULT_MATCH_ON,
) -> str:
    """Build a cassette lookup key from the parts of the request selected by *match_on*."""
    parsed = urlparse(url)
    parts: list[str] = []
    if "method" in match_on:
        parts.append(method.upper())
    if "host" in match_on:
        parts.append(parsed.netloc)
    if "path" in match_on:
        parts.append(parsed.path)
    if "query" in match_on and parsed.query:
        parts.append(f"?{parsed.query}")
    return " ".join(parts)


def _ws_key(url: str) -> str:
    return f"WS {urlparse(url).path}"


def _is_ws(url: str) -> bool:
    return url.startswith(("ws://", "wss://"))


# ── Fake extensions (replay mode) ────────────────────────────────────────────


class FakeExtension:
    """Replays pre-recorded WebSocket recv frames for sync clients."""

    def __init__(self, frames: list[dict[str, str]]) -> None:
        self._payloads = [f["payload"] for f in frames if f["direction"] == "recv"]
        self._idx = 0

    def next_payload(self) -> str | None:
        if self._idx >= len(self._payloads):
            return None
        payload = self._payloads[self._idx]
        self._idx += 1
        return payload

    def send_payload(self, data: str) -> None:
        pass

    def close(self) -> None:
        pass


class AsyncFakeExtension:
    """Replays pre-recorded WebSocket recv frames for async clients."""

    def __init__(self, frames: list[dict[str, str]]) -> None:
        self._payloads = [f["payload"] for f in frames if f["direction"] == "recv"]
        self._idx = 0

    async def next_payload(self) -> str | None:
        if self._idx >= len(self._payloads):
            return None
        payload = self._payloads[self._idx]
        self._idx += 1
        return payload

    async def send_payload(self, data: str) -> None:
        pass

    async def close(self) -> None:
        pass


# ── Recording extensions (record mode) ───────────────────────────────────────


class RecordingExtension:
    """Wraps a live sync WS extension, appending every frame to a shared list."""

    def __init__(self, real: Any, frames: list[dict[str, str]]) -> None:
        self._real = real
        self._frames = frames

    def next_payload(self) -> str | None:
        raw = self._real.next_payload()
        if raw is not None:
            decoded = raw if isinstance(raw, str) else raw.decode()
            self._frames.append({"direction": "recv", "payload": decoded})
        return raw

    def send_payload(self, data: str) -> None:
        self._frames.append({"direction": "send", "payload": data})
        self._real.send_payload(data)

    def close(self) -> None:
        self._real.close()


class AsyncRecordingExtension:
    """Wraps a live async WS extension, appending every frame to a shared list."""

    def __init__(self, real: Any, frames: list[dict[str, str]]) -> None:
        self._real = real
        self._frames = frames

    async def next_payload(self) -> str | None:
        raw = await self._real.next_payload()
        if raw is not None:
            decoded = raw if isinstance(raw, str) else raw.decode()
            self._frames.append({"direction": "recv", "payload": decoded})
        return raw

    async def send_payload(self, data: str) -> None:
        self._frames.append({"direction": "send", "payload": data})
        await self._real.send_payload(data)

    async def close(self) -> None:
        await self._real.close()


# ── Response construction ─────────────────────────────────────────────────────


class _FakeRaw:
    """Minimal stand-in for urllib3's HTTPResponse, exposing just the extension attribute."""

    def __init__(self, extension: Any) -> None:
        self.extension = extension


def _build_response(recorded: dict[str, Any]) -> Response:
    resp = Response()
    resp.status_code = recorded["status"]
    resp.headers = CaseInsensitiveDict(recorded.get("headers", {}))
    body = recorded.get("body") or ""
    resp._content = body.encode("utf-8") if isinstance(body, str) else bytes(body)
    resp._content_consumed = True
    resp.encoding = "utf-8"
    resp.url = recorded.get("url", "")
    return resp


def _ws_response(url: str, frames: list[dict[str, str]], *, is_async: bool) -> Response:
    ext = AsyncFakeExtension(frames) if is_async else FakeExtension(frames)
    resp = Response()
    resp.status_code = 101
    resp._content = b""
    resp._content_consumed = True
    resp.headers = CaseInsensitiveDict({"Upgrade": "websocket"})
    resp.encoding = "utf-8"
    resp.url = url
    resp.raw = _FakeRaw(ext)
    return resp


# ── Cassette ──────────────────────────────────────────────────────────────────


class Cassette:
    """
    Context manager that intercepts ``niquests.Session.send`` and
    ``niquests.AsyncSession.send`` to record or replay HTTP and WebSocket
    interactions.

    **Record mode** (``record=True``): calls pass through to the real network;
    each interaction is captured and written to ``path`` on exit.

    **Replay mode** (default): responses are returned from the cassette file
    without any network access. Responses are queued per the key derived from
    ``match_on`` and popped FIFO, so repeated calls to the same endpoint work.

    :param match_on: Set of request components used to build the lookup key.
        Supported values: ``"method"``, ``"host"``, ``"path"``, ``"query"``.
        Defaults to ``{"method", "path"}``, which ignores dynamic query params
        such as timestamps or pagination tokens.
    """

    def __init__(
        self,
        path: Path,
        *,
        record: bool = False,
        match_on: frozenset[str] = DEFAULT_MATCH_ON,
    ) -> None:
        unknown = match_on - SUPPORTED_MATCHERS
        if unknown:
            msg = f"Unknown matcher(s): {unknown!r}. Supported: {SUPPORTED_MATCHERS!r}"
            raise ValueError(msg)
        self._path = path
        self._record = record
        self._match_on = match_on
        # recorded[key] = list of raw interaction dicts (populated in record mode)
        self._recorded: dict[str, list[Any]] = defaultdict(list)
        # queues[key] = FIFO list of pre-loaded response dicts (replay mode)
        self._queues: dict[str, list[Any]] = defaultdict(list)
        self._patches: list[Any] = []

        if not record:
            self._load()

    # ── Persistence ──────────────────────────────────────────────────────────

    def _load(self) -> None:
        if not self._path.exists():
            return
        data = yaml.safe_load(self._path.read_text()) or {}
        for entry in data.get("interactions", []):
            # Cassettes store the full URL so all matchers work at load time.
            key = _http_key(
                entry["request"]["method"],
                entry["request"]["url"],
                self._match_on,
            )
            self._queues[key].append(entry["response"])
        for ws in data.get("websocket_sessions", []):
            key = _ws_key(ws["url"])
            self._queues[key].append(ws["frames"])

    def save(self) -> None:
        if not self._record:
            return
        interactions = []
        ws_sessions = []
        for key, entries in self._recorded.items():
            for entry in entries:
                if key.startswith("WS "):
                    ws_sessions.append(entry)
                else:
                    interactions.append(entry)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            yaml.dump(
                {"interactions": interactions, "websocket_sessions": ws_sessions},
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            ),
        )

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _record_http(self, method: str, url: str, resp: Response) -> None:
        body = resp.text if resp._content else ""
        # Store the full URL (not just path) so all match_on components are
        # available when the cassette is loaded back for replay.
        self._recorded[_http_key(method, url, self._match_on)].append(
            {
                "request": {"method": method, "url": url},
                "response": {
                    "status": resp.status_code,
                    "headers": dict(resp.headers),
                    "body": body,
                    "url": url,
                },
            },
        )

    def _record_ws(self, url: str) -> list[dict[str, str]]:
        """Register a new WS session recording and return its mutable frame list."""
        frames: list[dict[str, str]] = []
        self._recorded[_ws_key(url)].append({"url": url, "frames": frames})
        return frames

    def _replay_http(self, method: str, url: str, request: Any) -> Response:
        key = _http_key(method, url, self._match_on)
        if not self._queues.get(key):
            msg = f"No recorded response for {key!r} — re-run with --record to update cassettes"
            raise KeyError(msg)
        resp = _build_response(self._queues[key].pop(0))
        resp.request = request
        return resp

    def _replay_ws(self, url: str, *, is_async: bool) -> Response:
        key = _ws_key(url)
        if not self._queues.get(key):
            msg = f"No recorded WS session for {key!r} — re-run with --record to update cassettes"
            raise KeyError(msg)
        return _ws_response(url, self._queues[key].pop(0), is_async=is_async)

    # ── Send interceptors ─────────────────────────────────────────────────────

    def _make_sync_send(self, original: Any) -> Any:
        cassette = self

        def send(session_self: Session, request: Any, **kwargs: Any) -> Response:
            url = request.url or ""
            method = request.method or "GET"
            if cassette._record:
                resp = original(session_self, request, **kwargs)
                if _is_ws(url) and resp.extension is not None:
                    resp.raw._extension = RecordingExtension(
                        resp.extension,
                        cassette._record_ws(url),
                    )
                else:
                    cassette._record_http(method, url, resp)
                return resp
            if _is_ws(url):
                return cassette._replay_ws(url, is_async=False)
            return cassette._replay_http(method, url, request)

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
            if cassette._record:
                resp = await original(session_self, request, **kwargs)
                if _is_ws(url) and resp.extension is not None:
                    resp.raw._extension = AsyncRecordingExtension(
                        resp.extension,
                        cassette._record_ws(url),
                    )
                else:
                    cassette._record_http(method, url, resp)
                return resp
            if _is_ws(url):
                return cassette._replay_ws(url, is_async=True)
            return cassette._replay_http(method, url, request)

        return send

    # ── Context manager ───────────────────────────────────────────────────────

    def __enter__(self) -> Self:
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
        return self

    def __exit__(self, *_: object) -> None:
        for p in self._patches:
            p.stop()
        self.save()
