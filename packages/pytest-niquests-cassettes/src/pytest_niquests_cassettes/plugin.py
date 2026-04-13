"""pytest plugin entry point for pytest-niquests-cassettes."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Generator

from ._cassette import DEFAULT_MATCH_ON
from ._cassette import SUPPORTED_MATCHERS
from ._cassette import Cassette


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("niquests-cassettes")
    group.addoption(
        "--record",
        action="store_true",
        default=False,
        help="Record cassettes from live network traffic instead of replaying stored ones.",
    )
    group.addoption(
        "--cassette-dir",
        default="cassettes",
        help="Directory to store cassette files (relative to rootdir). Default: cassettes/",
    )
    group.addoption(
        "--cassette-file",
        default="session",
        help="Cassette filename without extension. Default: session",
    )
    default_matchers = ",".join(sorted(DEFAULT_MATCH_ON))
    supported = ", ".join(sorted(SUPPORTED_MATCHERS))
    group.addoption(
        "--cassette-match-on",
        default=default_matchers,
        help=(
            f"Comma-separated request components used to match cassette entries. "
            f"Supported: {supported}. Default: {default_matchers}"
        ),
    )


@pytest.fixture(scope="session", autouse=True)
def cassette(request: pytest.FixtureRequest) -> Generator[Cassette, None, None]:
    """
    Session-scoped fixture that activates cassette record/replay for all
    niquests HTTP and WebSocket traffic.

    Pass ``--record`` on the pytest command line to record a fresh cassette
    from a live server. Without ``--record``, traffic is replayed from the
    existing cassette file.
    """
    record: bool = request.config.getoption("--record")
    cassette_dir = Path(request.config.rootdir) / request.config.getoption(
        "--cassette-dir",
    )
    cassette_file = request.config.getoption("--cassette-file")
    path = cassette_dir / f"{cassette_file}.yaml"

    raw_match_on: str = request.config.getoption("--cassette-match-on")
    match_on = frozenset(m.strip() for m in raw_match_on.split(",") if m.strip())

    with Cassette(path=path, record=record, match_on=match_on) as c:
        yield c
