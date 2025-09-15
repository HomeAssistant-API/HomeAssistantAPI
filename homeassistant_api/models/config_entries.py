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
