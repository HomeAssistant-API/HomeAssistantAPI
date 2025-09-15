"""File for models used in responses from config entries."""

import asyncio
from enum import Enum
from typing import Any, Container, Dict, Tuple, Union

from .base import BaseModel


class FlowResultType(Enum):
    """Result type for a data entry flow."""

    FORM = "form"
    CREATE_ENTRY = "create_entry"
    ABORT = "abort"
    EXTERNAL_STEP = "external"
    EXTERNAL_STEP_DONE = "external_done"
    SHOW_PROGRESS = "progress"
    SHOW_PROGRESS_DONE = "progress_done"
    MENU = "menu"


class DiscoveryKey(BaseModel):
    """Serializable discovery key."""

    domain: str
    key: Union[str, Tuple[str, ...]]
    version: int


class FlowContext(BaseModel):
    """Base flow context"""

    show_advanced_options: Union[bool, None] = None
    source: str


class ConfigFlowContext(FlowContext):
    """Context for config flow."""

    alternative_domain: str | None = None
    configuration_url: str | None = None
    confirm_only: bool | None = None
    discovery_key: DiscoveryKey
    entry_id: str | None = None
    title_placeholders: Dict[str, str] | None = None
    unique_id: str | None = None


class FlowResult(BaseModel):
    """Base flow result ."""

    context: ConfigFlowContext
    data_schema: Any | None | None = None
    data: Dict[str, Any] | None = None
    description_placeholders: Dict[str, str] | None = None
    description: str | None = None
    errors: dict[str, str] | None = None
    extra: str | None = None
    flow_id: str
    handler: str
    last_step: bool | None = None
    menu_options: Container[str] | None = None
    preview: str | None = None
    progress_action: str | None = None
    progress_task: asyncio.Task[Any] | None = None
    reason: str | None = None
    required: bool | None = None
    result: Any | None = None
    step_id: str | None = None
    title: str | None = None
    translation_domain: str | None = None
    type: FlowResultType | None = None
    url: str | None = None


class DisableEnableResult(BaseModel):
    """Result from a disable/enable config entry call."""

    require_restart: bool


class IntegrationTypes(Enum):
    """Types of integrations."""

    ENTITY = "entity"
    DEVICE = "device"
    HARDWARE = "hardware"
    HELPER = "helper"
    HUB = "hub"
    SERVICE = "service"
    SYSTEM = "system"
    VIRTUAL = "virtual"


class ConfigEntryState(str, Enum):
    """Config entry state."""

    LOADED = "loaded"
    SETUP_ERROR = "setup_error"
    MIGRATION_ERROR = "migration_error"
    SETUP_RETRY = "setup_retry"
    NOT_LOADED = "not_loaded"
    FAILED_UNLOAD = "failed_unload"
    SETUP_IN_PROGRESS = "setup_in_progress"
    UNLOAD_IN_PROGRESS = "unload_in_progress"


class ConfigEntryDisabler(Enum):
    """What disabled a config entry."""

    USER = "user"


class ConfigEntry(BaseModel):
    """A configuration entry. This is the model that Home Assistant returns, but not what is used internally."""

    created_at: float
    entry_id: str
    domain: str
    modified_at: float
    title: str
    source: str
    state: ConfigEntryState
    supports_options: bool
    supports_remove_device: bool
    supports_unload: bool
    supports_reconfigure: bool
    supported_subentry_types: Dict[str, Dict[str, bool]]
    pref_disable_new_entities: bool
    pref_disable_polling: bool
    disabled_by: ConfigEntryDisabler | None
    reason: str | None
    error_reason_translation_key: str | None
    error_reason_translation_placeholders: dict[str, Any] | None
    num_subentries: int
