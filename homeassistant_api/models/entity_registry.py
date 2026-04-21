"""Models for Home Assistant entity registry responses."""

from enum import Enum
from typing import Any

from pydantic import Field
from pydantic import field_validator

from .base import BaseModel
from .base import DatetimeIsoField


class EntityDisabledBy(str, Enum):
    """What disabled an entity."""

    CONFIG_ENTRY = "config_entry"
    DEVICE = "device"
    HASS = "hass"
    INTEGRATION = "integration"
    USER = "user"


class EntityHiddenBy(str, Enum):
    """What hid an entity."""

    INTEGRATION = "integration"
    USER = "user"


class EntityCategory(str, Enum):
    """Category of an entity."""

    CONFIG = "config"
    DIAGNOSTIC = "diagnostic"


class EntityRegistryEntry(BaseModel):
    """An entity registry entry as returned by ``config/entity_registry/list``."""

    area_id: str | None = None
    categories: dict[str, str] = Field(default_factory=dict)
    config_entry_id: str | None = None
    config_subentry_id: str | None = None
    created_at: DatetimeIsoField
    device_id: str | None = None
    disabled_by: EntityDisabledBy | None = None
    entity_category: EntityCategory | None = None
    entity_id: str
    has_entity_name: bool
    hidden_by: EntityHiddenBy | None = None
    icon: str | None = None
    id: str
    modified_at: DatetimeIsoField
    name: str | None = None
    options: dict[str, Any] = Field(default_factory=dict)
    original_name: str | None = None
    platform: str
    translation_key: str | None = None
    unique_id: str


class EntityRegistryEntryExtended(EntityRegistryEntry):
    """Extended entity registry entry as returned by ``config/entity_registry/get`` and ``update``."""

    aliases: list[str] = Field(default_factory=list)
    capabilities: dict[str, Any] | None = None

    @field_validator("aliases", mode="before")
    @classmethod
    def _drop_none_aliases(cls, v: list) -> list:
        return [a for a in v if a is not None]

    device_class: str | None = None
    original_device_class: str | None = None
    original_icon: str | None = None


class EntityRegistryUpdateResult(BaseModel):
    """Result from ``config/entity_registry/update``."""

    entity_entry: EntityRegistryEntryExtended
    reload_delay: int | None = None
    require_restart: bool = False
