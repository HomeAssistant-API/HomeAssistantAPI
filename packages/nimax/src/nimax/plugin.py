"""pytest plugin entry point for nimax."""

from __future__ import annotations

from pathlib import Path  # noqa: TC003
from typing import TYPE_CHECKING

import niquests
import pytest
import pytest_asyncio
import tomllib

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator
    from collections.abc import Generator

from ._adapter import NimaxRecorder
from ._cassette import DEFAULT_MATCH_ON
from ._cassette import SUPPORTED_MATCHERS
from ._record_mode import RecordMode
from ._serializers import JSONSerializer

# ── pyproject.toml config ─────────────────────────────────────────────────────


def _load_nimax_config(config: pytest.Config) -> dict:
    """Read ``[tool.nimax]`` from the project's ``pyproject.toml``, if present."""
    pyproject = config.rootpath / "pyproject.toml"
    if not pyproject.exists():
        return {}
    with pyproject.open("rb") as fh:
        data = tomllib.load(fh)
    return data.get("tool", {}).get("nimax", {})


# ── CLI options ───────────────────────────────────────────────────────────────


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("niquests-cassettes")
    group.addoption(
        "--record",
        action="store_true",
        default=False,
        help="Shorthand for --record-mode=all: record cassettes from live traffic.",
    )
    group.addoption(
        "--record-mode",
        default=None,
        choices=[m.value for m in RecordMode],
        help=(
            "Cassette record mode. One of: "
            + ", ".join(m.value for m in RecordMode)
            + ". Default: once"
        ),
    )
    group.addoption(
        "--cassette-dir",
        default=None,
        help="Directory to store cassette files (relative to rootdir). Default: cassettes/",
    )
    default_matchers = ",".join(sorted(DEFAULT_MATCH_ON))
    supported = ", ".join(sorted(SUPPORTED_MATCHERS))
    group.addoption(
        "--cassette-match-on",
        default=None,
        help=(
            f"Comma-separated request components used to match cassette entries. "
            f"Supported: {supported}. Default: {default_matchers}"
        ),
    )


# ── Shared config resolution ──────────────────────────────────────────────────


def _resolve_config(request: pytest.FixtureRequest) -> dict:
    """Merge pyproject.toml config with CLI options (CLI wins)."""
    toml_cfg = _load_nimax_config(request.config)

    # Record mode
    if request.config.getoption("--record"):
        record_mode = RecordMode.ALL
    elif request.config.getoption("--record-mode") is not None:
        record_mode = RecordMode(request.config.getoption("--record-mode"))
    elif "record_mode" in toml_cfg:
        record_mode = RecordMode(toml_cfg["record_mode"])
    else:
        record_mode = RecordMode.ONCE

    # Cassette directory
    if request.config.getoption("--cassette-dir") is not None:
        cassette_dir_str: str = request.config.getoption("--cassette-dir")
    else:
        cassette_dir_str = toml_cfg.get("cassette_library_dir", "cassettes")

    # Matchers
    if request.config.getoption("--cassette-match-on") is not None:
        raw: str = request.config.getoption("--cassette-match-on")
        match_on = frozenset(m.strip() for m in raw.split(",") if m.strip())
    elif "match_on" in toml_cfg:
        cfg_match = toml_cfg["match_on"]
        if isinstance(cfg_match, list):
            match_on = frozenset(cfg_match)
        else:
            match_on = frozenset(
                m.strip() for m in str(cfg_match).split(",") if m.strip()
            )
    else:
        match_on = DEFAULT_MATCH_ON

    return {
        "record_mode": record_mode,
        "cassette_dir": request.config.rootpath / cassette_dir_str,
        "match_on": match_on,
    }


# ── Per-test fixtures ─────────────────────────────────────────────────────────


def _test_cassette_path(
    request: pytest.FixtureRequest,
    cassette_dir: Path,
) -> Path:
    """Build a per-test cassette path: ``{cassette_dir}/{module}/{test}.json``."""
    module = request.path.stem
    test_name = request.node.name
    # Sanitise parameterised-test brackets for filesystem safety
    safe_name = test_name.replace("[", "_").replace("]", "").replace("/", "_")
    return cassette_dir / module / f"{safe_name}.json"


@pytest.fixture
def nimax_session(
    request: pytest.FixtureRequest,
) -> Generator[niquests.Session, None, None]:
    """Per-test fixture: a ``niquests.Session`` backed by its own cassette.

    Cassette is named ``{cassette_dir}/{module}/{test}.json``.
    """
    cfg = _resolve_config(request)
    path = _test_cassette_path(request, cfg["cassette_dir"])
    session = niquests.Session()
    recorder = NimaxRecorder(session)
    with recorder.use_cassette(
        path.stem,
        cassette_dir=path.parent,
        record_mode=cfg["record_mode"],
        match_on=cfg["match_on"],
        serializer=JSONSerializer(),
    ):
        yield session


@pytest_asyncio.fixture
async def nimax_async_session(
    request: pytest.FixtureRequest,
) -> AsyncGenerator[niquests.AsyncSession, None]:
    """Per-test fixture: a ``niquests.AsyncSession`` backed by its own cassette.

    Cassette is named ``{cassette_dir}/{module}/{test}.json``.
    """
    cfg = _resolve_config(request)
    path = _test_cassette_path(request, cfg["cassette_dir"])
    session = niquests.AsyncSession()
    recorder = NimaxRecorder(session)
    with recorder.use_cassette(
        path.stem,
        cassette_dir=path.parent,
        record_mode=cfg["record_mode"],
        match_on=cfg["match_on"],
        serializer=JSONSerializer(),
    ):
        yield session
