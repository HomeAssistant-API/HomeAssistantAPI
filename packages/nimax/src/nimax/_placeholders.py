"""Placeholder / sanitization support for cassette sensitive values."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Placeholder:
    """Maps a real value to a redacted placeholder stored in the cassette.

    :param placeholder: The token written to the cassette (e.g. ``"<API_KEY>"``).
    :param replace:     The real value present in requests/responses.
    """

    placeholder: str
    replace: str


def apply_placeholders(text: str, placeholders: list[Placeholder]) -> str:
    """Replace real values with placeholder tokens before writing a cassette."""
    for p in placeholders:
        text = text.replace(p.replace, p.placeholder)
    return text


def restore_placeholders(text: str, placeholders: list[Placeholder]) -> str:
    """Replace placeholder tokens with real values after reading a cassette."""
    for p in placeholders:
        text = text.replace(p.placeholder, p.replace)
    return text
