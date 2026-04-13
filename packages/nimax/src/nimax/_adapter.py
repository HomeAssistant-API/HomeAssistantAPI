"""NimaxRecorder: programmatic API for wrapping a session with a cassette."""

from __future__ import annotations

import contextlib
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import ClassVar

from ._cassette import DEFAULT_MATCH_ON
from ._cassette import Cassette
from ._matchers import BUILTIN_MATCHERS
from ._matchers import BaseMatcher
from ._record_mode import RecordMode
from ._serializers import BUILTIN_SERIALIZERS
from ._serializers import BaseSerializer
from ._serializers import JSONSerializer

if TYPE_CHECKING:
    from collections.abc import Generator
    from collections.abc import Iterable

    import niquests

    from ._placeholders import Placeholder


class NimaxRecorder:
    """Wraps a niquests session to provide cassette recording and replay.

    Usage::

        recorder = NimaxRecorder(session)
        with recorder.use_cassette("my_test") as cassette:
            resp = session.get("https://example.com")

    The recorder patches ``niquests.Session.send`` and
    ``niquests.AsyncSession.send`` class-wide for the duration of the context,
    so any sessions created inside the block are also intercepted.

    Custom matchers and serializers can be registered at the class level::

        NimaxRecorder.register_matcher(MyMatcher)
        NimaxRecorder.register_serializer(MySerializer)
    """

    _matchers: ClassVar[dict[str, type[BaseMatcher]]] = dict(BUILTIN_MATCHERS)
    _serializers: ClassVar[dict[str, type[BaseSerializer]]] = dict(BUILTIN_SERIALIZERS)

    def __init__(self, session: niquests.Session | niquests.AsyncSession) -> None:
        self._session = session

    @classmethod
    def register_matcher(cls, matcher: type[BaseMatcher]) -> None:
        """Register a custom matcher, making it available by name."""
        cls._matchers[matcher.name] = matcher

    @classmethod
    def register_serializer(cls, serializer: type[BaseSerializer]) -> None:
        """Register a custom serializer, making it available by extension."""
        cls._serializers[serializer.extension] = serializer

    @contextlib.contextmanager
    def use_cassette(  # noqa: PLR0913
        self,
        name: str,
        *,
        cassette_dir: Path | str = "cassettes",
        record_mode: RecordMode = RecordMode.ONCE,
        match_on: Iterable[str] = DEFAULT_MATCH_ON,
        serializer: BaseSerializer | None = None,
        placeholders: list[Placeholder] | None = None,
    ) -> Generator[Cassette, None, None]:
        """Context manager that activates a named cassette for the session.

        :param name:         Cassette name (used as the filename stem).
        :param cassette_dir: Directory to store cassette files.
        :param record_mode:  When to record vs replay.
        :param match_on:     Iterable of matcher names.
        :param serializer:   Explicit serializer (defaults to JSON).
        :param placeholders: Sensitive values to redact in the cassette.
        """
        resolved_serializer = serializer or JSONSerializer()
        path = Path(cassette_dir) / f"{name}.{resolved_serializer.extension}"
        cassette = Cassette(
            path=path,
            record_mode=record_mode,
            match_on=frozenset(match_on),
            serializer=resolved_serializer,
            placeholders=placeholders,
        )
        with cassette:
            yield cassette

    # Convenience: expose session on the recorder for use inside the context
    @property
    def session(self) -> Any:
        return self._session
