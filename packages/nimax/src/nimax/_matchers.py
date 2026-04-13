"""Matcher ABCs and built-in matcher implementations."""

from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from typing import Any
from urllib.parse import parse_qs
from urllib.parse import urlparse


class BaseMatcher(ABC):
    """Abstract base for all request matchers.

    A matcher compares a recorded request dict (from the cassette) with a live
    ``PreparedRequest`` and returns ``True`` if they are considered equivalent
    for the component this matcher is responsible for.
    """

    name: str

    @abstractmethod
    def match(self, recorded: dict[str, Any], live: Any) -> bool:
        """Return True if *live* matches the *recorded* request for this component."""


class MethodMatcher(BaseMatcher):
    name = "method"

    def match(self, recorded: dict[str, Any], live: Any) -> bool:
        return recorded.get("method", "").upper() == (live.method or "").upper()


class URIMatcher(BaseMatcher):
    """Exact URI match including query string."""

    name = "uri"

    def match(self, recorded: dict[str, Any], live: Any) -> bool:
        return recorded.get("uri", "") == (live.url or "")


class HostMatcher(BaseMatcher):
    name = "host"

    def match(self, recorded: dict[str, Any], live: Any) -> bool:
        recorded_host = urlparse(recorded.get("uri", "")).netloc
        live_host = urlparse(live.url or "").netloc
        return recorded_host == live_host


class PathMatcher(BaseMatcher):
    name = "path"

    def match(self, recorded: dict[str, Any], live: Any) -> bool:
        recorded_path = urlparse(recorded.get("uri", "")).path
        live_path = urlparse(live.url or "").path
        return recorded_path == live_path


class QueryMatcher(BaseMatcher):
    """Order-insensitive query-string comparison."""

    name = "query"

    def match(self, recorded: dict[str, Any], live: Any) -> bool:
        recorded_q = parse_qs(urlparse(recorded.get("uri", "")).query)
        live_q = parse_qs(urlparse(live.url or "").query)
        return recorded_q == live_q


class HeadersMatcher(BaseMatcher):
    """Checks that all recorded request headers are present in the live request."""

    name = "headers"

    def match(self, recorded: dict[str, Any], live: Any) -> bool:
        recorded_headers: dict[str, list[str]] = recorded.get("headers") or {}
        live_headers = live.headers or {}
        for key, values in recorded_headers.items():
            live_val = live_headers.get(key)
            if live_val is None:
                return False
            expected = values[0] if isinstance(values, list) else values
            if live_val != expected:
                return False
        return True


class BodyMatcher(BaseMatcher):
    name = "body"

    def match(self, recorded: dict[str, Any], live: Any) -> bool:
        recorded_body = recorded.get("body")
        live_body = live.body
        if isinstance(live_body, bytes):
            live_body = live_body.decode("utf-8", errors="replace")
        return recorded_body == live_body


class ProtocolMatcher(BaseMatcher):
    """Match the negotiated HTTP protocol (HTTP/1.1, HTTP/2, HTTP/3)."""

    name = "protocol"

    def match(self, recorded: dict[str, Any], live: Any) -> bool:  # noqa: ARG002
        # Protocol is not available on the PreparedRequest; always pass at
        # match time and validate post-response in the adapter layer.
        return True


# Registry of all built-in matchers keyed by name.
BUILTIN_MATCHERS: dict[str, type[BaseMatcher]] = {
    m.name: m  # type: ignore[attr-defined]
    for m in (
        MethodMatcher,
        URIMatcher,
        HostMatcher,
        PathMatcher,
        QueryMatcher,
        HeadersMatcher,
        BodyMatcher,
        ProtocolMatcher,
    )
}
