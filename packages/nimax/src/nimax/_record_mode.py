"""RecordMode enum for nimax cassette recording behaviour."""

from __future__ import annotations

from enum import Enum


class RecordMode(str, Enum):
    """Controls when cassette interactions are recorded vs replayed.

    NONE        — Never record; raise on any unmatched request.
    ONCE        — Record if cassette is absent; replay (and error on miss) if present.
    NEW_EPISODES — Replay matched interactions; record unmatched ones.
    ALL         — Re-record every interaction, replacing the cassette each run.
    """

    NONE = "none"
    ONCE = "once"
    NEW_EPISODES = "new_episodes"
    ALL = "all"
