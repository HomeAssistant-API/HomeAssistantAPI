"""File for models used in responses from config entries."""

import asyncio
from enum import Enum
from typing import Any, Container, Dict, Optional, Tuple, Union

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

    alternative_domain: Optional[str] = None
    configuration_url: Optional[str] = None
    confirm_only: Optional[bool] = None
    discovery_key: DiscoveryKey
    entry_id: Optional[str] = None
    title_placeholders: Optional[Dict[str, str]] = None
    unique_id: Optional[str] = None


class FlowResult(BaseModel):
    """Base flow result ."""

    context: ConfigFlowContext
    data_schema: Optional[Any] = None
    data: Optional[Dict[str, Any]] = None
    description_placeholders: Optional[Dict[str, str]] = None
    description: Optional[str] = None
    errors: Optional[Dict[str, str]] = None
    extra: Optional[str] = None
    flow_id: str
    handler: str
    last_step: Optional[bool] = None
    menu_options: Optional[Container[str]] = None
    preview: Optional[str] = None
    progress_action: Optional[str] = None
    progress_task: Optional[asyncio.Task[Any]] = None
    reason: Optional[str] = None
    required: Optional[bool] = None
    result: Optional[Any] = None
    step_id: Optional[str] = None
    title: Optional[str] = None
    translation_domain: Optional[str] = None
    type: Optional[FlowResultType] = None
    url: Optional[str] = None


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
    disabled_by: Optional[ConfigEntryDisabler]
    reason: Optional[str]
    error_reason_translation_key: Optional[str]
    error_reason_translation_placeholders: Optional[Dict[str, Any]]
    num_subentries: int


class ConfigSubEntry(BaseModel):
    """A configuration sub-entry. This is the model that Home Assistant returns, but not what is used internally."""

    subentry_id: str
    subentry_type: str
    title: str
    unique_id: Optional[str]
