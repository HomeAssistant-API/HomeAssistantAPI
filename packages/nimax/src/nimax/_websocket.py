"""WebSocket frame model and extension proxy classes."""

from __future__ import annotations

import time
from dataclasses import dataclass
from dataclasses import field
from typing import Any


@dataclass
class Frame:
    """A single recorded WebSocket frame."""

    direction: str  # "send" | "recv"
    type: str  # "text" | "binary" | "ping" | "pong" | "close"
    payload: str | None
    offset_ms: int = 0
    close_code: int | None = None
    close_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "direction": self.direction,
            "type": self.type,
            "payload": self.payload,
            "offset_ms": self.offset_ms,
        }
        if self.close_code is not None:
            d["close_code"] = self.close_code
        if self.close_reason is not None:
            d["close_reason"] = self.close_reason
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Frame:
        return cls(
            direction=d["direction"],
            type=d.get("type", "text"),
            payload=d.get("payload"),
            offset_ms=d.get("offset_ms", 0),
            close_code=d.get("close_code"),
            close_reason=d.get("close_reason"),
        )


@dataclass
class WebSocketSession:
    """Recorded WebSocket session: metadata + ordered frame sequence."""

    uri: str
    handshake_recorded_at: str
    protocol: str | None
    frames: list[Frame] = field(default_factory=list)
    _cursor: int = field(default=0, init=False, repr=False)
    # True once a replay consumer has claimed this session so subsequent
    # connections to the same URI get the next unclaimed session.
    _claimed: bool = field(default=False, init=False, repr=False)

    def claim(self) -> bool:
        """Mark session as claimed. Returns True if it was unclaimed."""
        if self._claimed:
            return False
        self._claimed = True
        return True

    def next_recv_frame(self) -> Frame | None:
        """Return the next unplayed recv-direction frame, advancing the cursor."""
        while self._cursor < len(self.frames):
            frame = self.frames[self._cursor]
            self._cursor += 1
            if frame.direction == "recv":
                return frame
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "uri": self.uri,
            "handshake_recorded_at": self.handshake_recorded_at,
            "protocol": self.protocol,
            "frames": [f.to_dict() for f in self.frames],
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> WebSocketSession:
        # "url" is the legacy key; "uri" is the current format
        uri = d.get("uri") or d.get("url", "")
        session = cls(
            uri=uri,
            handshake_recorded_at=d.get("handshake_recorded_at", ""),
            protocol=d.get("protocol"),
        )
        session.frames = [Frame.from_dict(f) for f in d.get("frames", [])]
        return session


# ── Replay proxies ────────────────────────────────────────────────────────────


class FakeExtension:
    """Replays pre-recorded WebSocket recv frames for sync clients."""

    def __init__(self, session: WebSocketSession) -> None:
        self._session = session

    def next_payload(self) -> str | None:
        frame = self._session.next_recv_frame()
        return frame.payload if frame is not None else None

    def send_payload(self, data: str) -> None:
        pass

    def close(self) -> None:
        pass


class AsyncFakeExtension:
    """Replays pre-recorded WebSocket recv frames for async clients."""

    def __init__(self, session: WebSocketSession) -> None:
        self._session = session

    async def next_payload(self) -> str | None:
        frame = self._session.next_recv_frame()
        return frame.payload if frame is not None else None

    async def send_payload(self, data: str) -> None:
        pass

    async def close(self) -> None:
        pass


# ── Recording proxies ─────────────────────────────────────────────────────────


class RecordingExtension:
    """Wraps a live sync WS extension, recording every frame into *session*."""

    def __init__(self, real: Any, session: WebSocketSession, start: float) -> None:
        self._real = real
        self._session = session
        self._start = start

    def _elapsed_ms(self) -> int:
        return int((time.monotonic() - self._start) * 1000)

    def next_payload(self) -> str | None:
        raw = self._real.next_payload()
        if raw is not None:
            payload = (
                raw if isinstance(raw, str) else raw.decode("utf-8", errors="replace")
            )
            self._session.frames.append(
                Frame(
                    direction="recv",
                    type="text",
                    payload=payload,
                    offset_ms=self._elapsed_ms(),
                ),
            )
        return raw

    def send_payload(self, data: str) -> None:
        self._session.frames.append(
            Frame(
                direction="send",
                type="text",
                payload=data,
                offset_ms=self._elapsed_ms(),
            ),
        )
        self._real.send_payload(data)

    def close(self) -> None:
        self._real.close()


class AsyncRecordingExtension:
    """Wraps a live async WS extension, recording every frame into *session*."""

    def __init__(self, real: Any, session: WebSocketSession, start: float) -> None:
        self._real = real
        self._session = session
        self._start = start

    def _elapsed_ms(self) -> int:
        return int((time.monotonic() - self._start) * 1000)

    async def next_payload(self) -> str | None:
        raw = await self._real.next_payload()
        if raw is not None:
            payload = (
                raw if isinstance(raw, str) else raw.decode("utf-8", errors="replace")
            )
            self._session.frames.append(
                Frame(
                    direction="recv",
                    type="text",
                    payload=payload,
                    offset_ms=self._elapsed_ms(),
                ),
            )
        return raw

    async def send_payload(self, data: str) -> None:
        self._session.frames.append(
            Frame(
                direction="send",
                type="text",
                payload=data,
                offset_ms=self._elapsed_ms(),
            ),
        )
        await self._real.send_payload(data)

    async def close(self) -> None:
        await self._real.close()
