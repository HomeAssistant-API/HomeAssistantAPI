"""Models for Home Assistant entity registry responses."""

from enum import StrEnum
from typing import Any
from typing import TypedDict

from pydantic import Field
from typing_extensions import NotRequired

from .base import BaseModel
from .base import DatetimeIsoField


class EntityDisabledBy(StrEnum):
    """What disabled an entity."""

    CONFIG_ENTRY = "config_entry"
    DEVICE = "device"
    HASS = "hass"
    INTEGRATION = "integration"
    USER = "user"


class EntityHiddenBy(StrEnum):
    """What hid an entity."""

    INTEGRATION = "integration"
    USER = "user"


class EntityCategory(StrEnum):
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
    """Extended entity registry entry as returned by ``config/entity_registry/get``."""

    aliases: list[str] | tuple[None] = Field(default_factory=list)
    capabilities: dict[str, Any] | None = None
    device_class: str | None = None
    original_device_class: str | None = None
    original_icon: str | None = None


class EntityRegistryUpdateResult(BaseModel):
    """Result from ``config/entity_registry/update``."""

    entity_entry: EntityRegistryEntryExtended
    reload_delay: int | None = None
    require_restart: bool = False


class EntityRegistryUpdateParams(TypedDict):
    """Parameters used in ``config/entity_registry/update``."""

    aliases: NotRequired[list[str]]
    area_id: NotRequired[str | None]
    categories: NotRequired[dict[str, str]]
    device_class: NotRequired[str | None]
    disabled_by: NotRequired[EntityHiddenBy | None]
    entity_id: str
    hidden_by: NotRequired[EntityHiddenBy | None]
    icon: NotRequired[str | None]
    labels: NotRequired[list[str]]
    name: NotRequired[str | None]
    new_entity_id: NotRequired[str]
    # options and options_domain are inclusive, meaning only both or none of them have to be defined
    options_domain: NotRequired[str]
    options: NotRequired[dict[str, Any]]
