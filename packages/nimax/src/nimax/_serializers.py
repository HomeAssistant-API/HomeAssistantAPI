"""Serializer ABCs and built-in serializer implementations."""

from __future__ import annotations

import json
from abc import ABC
from abc import abstractmethod

import yaml


class BaseSerializer(ABC):
    """Abstract base for cassette serializers."""

    extension: str

    @abstractmethod
    def serialize(self, data: dict) -> str:
        """Convert cassette data dict to a string for writing to disk."""

    @abstractmethod
    def deserialize(self, raw: str) -> dict:
        """Parse a cassette file string back to a data dict."""


class JSONSerializer(BaseSerializer):
    extension = "json"

    def serialize(self, data: dict) -> str:
        return json.dumps(data, indent=2, ensure_ascii=False)

    def deserialize(self, raw: str) -> dict:
        return json.loads(raw)


class YAMLSerializer(BaseSerializer):
    extension = "yaml"

    def serialize(self, data: dict) -> str:
        return yaml.dump(
            data,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )

    def deserialize(self, raw: str) -> dict:
        return yaml.safe_load(raw) or {}


# Registry of all built-in serializers keyed by name / extension.
BUILTIN_SERIALIZERS: dict[str, type[BaseSerializer]] = {
    "json": JSONSerializer,
    "yaml": YAMLSerializer,
}
