"""File for Service and Domain data models"""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING
from typing import Any
from typing import cast

from pydantic import Field
from typing_extensions import Self
from typing_extensions import override

from homeassistant_api.errors import RequestError
from homeassistant_api.errors import ResponseError

from .base import BaseModel

if TYPE_CHECKING:
    from homeassistant_api import AsyncClient
    from homeassistant_api import AsyncWebsocketClient
    from homeassistant_api import Client
    from homeassistant_api import WebsocketClient

    from .states import State

__all__ = (
    "AsyncDomain",
    "AsyncService",
    "BaseDomain",
    "BaseService",
    "Domain",
    "Service",
)


class BaseDomain(BaseModel):
    """Model representing the domain that services belong to."""

    domain_id: str = Field(
        ...,
        description="The name of the domain that services belong to. "
        "(e.g. :code:`frontend` in :code:`frontend.reload_themes`",
    )
    services: dict[str, BaseService] = Field(
        default_factory=dict,
        description="A dictionary of all services belonging to the domain indexed by their names",
    )

    @classmethod
    @override
    def from_json(cls, json: dict[str, Any] | Any | None, **kwargs: Any) -> Self:
        msg = f"`{cls.__name__}` does not support `from_json()`. Use `from_json_with_client()`"
        raise NotImplementedError(msg)

    @classmethod
    def _build_from_json(cls, json: dict[str, Any], **model_kwargs: Any) -> Self:
        """Shared construction logic for Domain models from json data."""
        if "domain" not in json or "services" not in json:
            msg = "Missing services or domain attribute in json argument."
            raise ValueError(msg)
        domain = cls(domain_id=cast("str", json.get("domain")), **model_kwargs)
        services = json.get("services")
        if not isinstance(services, dict):
            msg = f"Expected dict for services, got {type(services)}"
            raise TypeError(msg)
        for service_id, data in services.items():
            domain._add_service(service_id, **data)
        return domain

    def _add_service(self, service_id: str, **data: Any) -> None:
        """Registers services into a domain to be used or accessed. Used internally."""
        raise NotImplementedError

    def get_service(self, service_id: str) -> BaseService | None:
        """Return a Service with the given :code:`service_id`, returns None if no such service exists"""
        return self.services.get(service_id)

    def __getattr__(self, attr: str) -> Any:
        """Allows services accessible as attributes"""
        if attr in self.services:
            return self.get_service(attr)
        try:
            return super().__getattribute__(attr)
        except AttributeError as err:
            try:
                return object.__getattribute__(self, attr)
            except AttributeError as e:
                raise e from err


class Domain(BaseDomain):
    """Sync domain that creates sync Service instances."""

    client: Client | WebsocketClient = Field(exclude=True, repr=False)

    @classmethod
    def from_json_with_client(
        cls,
        json: dict[str, Any],
        client: Client | WebsocketClient,
    ) -> Domain:
        """Constructs Domain and Service models from json data."""
        return cls._build_from_json(json, client=client)

    def _add_service(self, service_id: str, **data: Any) -> None:
        self.services[service_id] = Service(
            service_id=service_id,
            domain=self,
            **data,
        )


class AsyncDomain(BaseDomain):
    """Async domain that creates async Service instances."""

    client: AsyncClient | AsyncWebsocketClient = Field(exclude=True, repr=False)

    @classmethod
    def from_json_with_client(
        cls,
        json: dict[str, Any],
        client: AsyncClient | AsyncWebsocketClient,
    ) -> AsyncDomain:
        """Constructs Domain and Service models from json data."""
        return cls._build_from_json(json, client=client)

    def _add_service(self, service_id: str, **data: Any) -> None:
        self.services[service_id] = AsyncService(
            service_id=service_id,
            domain=self,
            **data,
        )


# Sources:
# https://developers.home-assistant.io/docs/dev_101_services/
# https://www.home-assistant.io/docs/blueprint/selectors/#date-selector
# https://github.com/home-assistant/frontend/blob/dev/src/data/selector.ts
# https://github.com/home-assistant/home-assistant-js-websocket/blob/master/lib/types.ts


# Helpers
class ServiceFieldSelectorEntityFilter(BaseModel):
    integration: str | None = None
    domain: list[str] | str | None = None
    device_class: list[str] | str | None = None
    supported_features: list[int] | int | None = None


class ServiceFieldSelectorDeviceFilter(BaseModel):
    integration: str | None = None
    manufacturer: str | None = None
    model: str | None = None
    model_id: str | None = None


class CropOptions(BaseModel):
    round: bool
    type: str | None = None  # "image/jpeg" / "image/png"
    quality: int | float | None = None
    aspect_ratio: int | float | None = Field(default=None, alias="aspectRatio")


class SelectBoxOptionImage(BaseModel):
    src: str
    src_dark: str | None = None
    flip_rtl: bool | None = None


class ServiceFieldSelectorNumberMode(StrEnum):
    BOX = "box"
    SLIDER = "slider"


class ServiceFieldSelectorSelectMode(StrEnum):
    LIST = "list"
    DROPDOWN = "dropdown"
    BOX = "box"


class ServiceFieldSelectorQRCodeErrorCorrectionLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    QUARTILE = "quartile"
    HIGH = "high"


class ServiceFieldSelectorTextType(StrEnum):
    NUMBER = "number"
    TEXT = "text"
    SEARCH = "search"
    TEL = "tel"
    URL = "url"
    EMAIL = "email"
    PASSWORD = "password"  # noqa: S105
    DATE = "date"
    MONTH = "month"
    WEEK = "week"
    TIME = "time"
    DATETIME_LOCAL = "datetime-local"
    COLOR = "color"


# Selectors
class ServiceFieldSelectorAction(BaseModel):
    options_in_sidebar: bool | None = Field(default=None, alias="optionsInSidebar")


class ServiceFieldSelectorAddon(BaseModel):
    name: str | None = None
    slug: str | None = None


class ServiceFieldSelectorArea(BaseModel):
    entity: (
        list[ServiceFieldSelectorEntityFilter] | ServiceFieldSelectorEntityFilter | None
    ) = None
    device: (
        list[ServiceFieldSelectorDeviceFilter] | ServiceFieldSelectorDeviceFilter | None
    ) = None
    multiple: bool | None = None


class ServiceFieldSelectorAreasDisplay(BaseModel):
    pass


class ServiceFieldSelectorAttribute(BaseModel):
    entity_id: list[str] | str | None = None
    hide_attributes: list[str] | None = None


class ServiceFieldSelectorAssistPipeline(BaseModel):
    include_last_used: bool | None = None


class ServiceFieldSelectorBackground(BaseModel):
    original: bool | None = None
    crop: CropOptions | None = None


class ServiceFieldSelectorBackupLocation(BaseModel):
    pass


class ServiceFieldSelectorBoolean(BaseModel):
    pass


class ServiceFieldSelectorButtonToggle(BaseModel):
    options: list[str | ServiceFieldSelectorSelectOption]
    translation_key: str | None = None
    sort: bool | None = None


class ServiceFieldSelectorColorRGB(BaseModel):
    pass


class ServiceFieldSelectorColorTemp(BaseModel):
    unit: str | None = None
    min: int | float | None = None
    max: int | float | None = None
    min_mireds: int | float | None = None
    max_mireds: int | float | None = None


class ServiceFieldSelectorCondition(BaseModel):
    options_in_sidebar: bool | None = Field(default=None, alias="optionsInSidebar")


class ServiceFieldSelectorConfigEntry(BaseModel):
    integration: str | None = None


class ServiceFieldSelectorConstant(BaseModel):
    label: str | None = None
    value: str | int | float | bool
    translation_key: str | None = None


class ServiceFieldSelectorConversationAgent(BaseModel):
    language: str | None = None  # filtering by language not supported


class ServiceFieldSelectorCountry(BaseModel):
    countries: list[str]
    no_sort: bool | None = None


class ServiceFieldSelectorDate(BaseModel):
    pass


class ServiceFieldSelectorDateTime(BaseModel):
    pass


class ServiceFieldSelectorDevice(BaseModel):
    entity: (
        list[ServiceFieldSelectorEntityFilter] | ServiceFieldSelectorEntityFilter | None
    ) = None
    filter: (
        list[ServiceFieldSelectorDeviceFilter] | ServiceFieldSelectorDeviceFilter | None
    ) = None
    multiple: bool | None = None


class ServiceFieldSelectorDeviceLegacy(ServiceFieldSelectorDevice):
    integration: str | None = None
    manufacturer: str | None = None
    model: str | None = None


class ServiceFieldSelectorDuration(BaseModel):
    enable_day: bool | None = None
    enable_millisecond: bool | None = None


class ServiceFieldSelectorEntity(BaseModel):
    multiple: bool | None = None
    include_entities: list[str] | None = None
    exclude_entities: list[str] | None = None
    filter: (
        list[ServiceFieldSelectorEntityFilter] | ServiceFieldSelectorEntityFilter | None
    ) = None
    reorder: bool | None = None


class ServiceFieldSelectorEntityLegacy(ServiceFieldSelectorEntity):
    integration: str | None = None
    domain: list[str] | str | None = None
    device_class: list[str] | str | None = None


class ServiceFieldSelectorFloor(BaseModel):
    entity: (
        list[ServiceFieldSelectorEntityFilter] | ServiceFieldSelectorEntityFilter | None
    ) = None
    device: (
        list[ServiceFieldSelectorDeviceFilter] | ServiceFieldSelectorDeviceFilter | None
    ) = None
    multiple: bool | None = None


class ServiceFieldSelectorFile(BaseModel):
    accept: str


class ServiceFieldSelectorIcon(BaseModel):
    placeholder: str | None = None
    fallback_path: str | None = Field(default=None, alias="fallbackPath")


class ServiceFieldSelectorImage(BaseModel):
    original: bool | None = None
    crop: CropOptions | None = None


class ServiceFieldSelectorLabel(BaseModel):
    multiple: bool | None = None


class ServiceFieldSelectorLanguage(BaseModel):
    languages: list[str] | None = None
    native_name: bool | None = None
    no_sort: bool | None = None


class ServiceFieldSelectorLocation(BaseModel):
    radius: bool | None = None
    radius_readonly: bool | None = None
    icon: str | None = None


class ServiceFieldSelectorMedia(BaseModel):
    accept: list[str] | None = None
    multiple: bool = False


class ServiceFieldSelectorNavigation(BaseModel):
    pass


class ServiceFieldSelectorNumber(BaseModel):
    min: int | float | None = None
    max: int | float | None = None
    step: int | float | str | None = None
    unit_of_measurement: str | None = None
    mode: ServiceFieldSelectorNumberMode | None = None
    slider_ticks: bool | None = None
    translation_key: str | None = None


class ServiceFieldSelectorObjectField(BaseModel):
    selector: ServiceFieldSelector
    label: str | None = None
    required: bool | None = None


class ServiceFieldSelectorObject(BaseModel):
    label_field: str | None = None
    description_field: str | None = None
    translation_key: str | None = None
    fields: dict[str, ServiceFieldSelectorObjectField] | None = None
    multiple: bool | None = None


class ServiceFieldSelectorQRCode(BaseModel):
    data: str
    scale: int | float | None = None
    error_correction_level: ServiceFieldSelectorQRCodeErrorCorrectionLevel | None = None
    center_image: str | None = None


class ServiceFieldSelectorSelectOption(BaseModel):
    label: str
    value: Any
    description: str | None = None
    image: str | SelectBoxOptionImage | None = None
    disable: bool | None = None


class ServiceFieldSelectorSelect(BaseModel):
    multiple: bool | None = None
    custom_value: bool | None = None
    mode: ServiceFieldSelectorSelectMode | None = None
    options: list[str | ServiceFieldSelectorSelectOption]
    translation_key: str | None = None
    sort: bool | None = None
    reorder: bool | None = None
    box_max_columns: int | None = None


class ServiceFieldSelectorSelector(BaseModel):
    pass


class ServiceFieldSelectorStateOption(BaseModel):
    label: str
    value: Any


class ServiceFieldSelectorState(BaseModel):
    extra_options: list[ServiceFieldSelectorStateOption] | None = None
    entity_id: str | list[str] | None = None
    attribute: str | None = None
    hide_states: list[str] | None = None
    multiple: bool | None = None


class ServiceFieldSelectorStatistic(BaseModel):
    device_class: str | None = None
    multiple: bool | None = None


class ServiceFieldSelectorTarget(BaseModel):
    entity: (
        list[ServiceFieldSelectorEntityFilter] | ServiceFieldSelectorEntityFilter | None
    ) = None
    device: (
        list[ServiceFieldSelectorDeviceFilter] | ServiceFieldSelectorDeviceFilter | None
    ) = None


class ServiceFieldSelectorTemplate(BaseModel):
    pass


class ServiceFieldSelectorSTT(BaseModel):
    language: str | None = None


class ServiceFieldSelectorText(BaseModel):
    multiline: bool | None = None
    type: ServiceFieldSelectorTextType | None = None
    prefix: str | None = None
    suffix: str | None = None
    autocomplete: str | None = None
    multiple: bool | None = None


class ServiceFieldSelectorTheme(BaseModel):
    include_default: bool | None = None


class ServiceFieldSelectorTime(BaseModel):
    no_second: bool | None = None


class ServiceFieldSelectorTrigger(BaseModel):
    pass


class ServiceFieldSelectorTTS(BaseModel):
    language: str | None = None


class ServiceFieldSelectorTTSVoice(BaseModel):
    engine_id: str | None = Field(default=None, alias="engineId")
    language: str | None = None


class ServiceFieldSelectorUIAction(BaseModel):
    pass


class ServiceFieldSelectorUIColor(BaseModel):
    default_color: str | None = None
    include_none: bool | None = None
    include_state: bool | None = None


class ServiceFieldSelectorUIStateContext(BaseModel):
    entity_id: str | None = None
    allow_name: bool | None = None


class ServiceFieldSelector(BaseModel):
    action: ServiceFieldSelectorAction | None = None
    addon: ServiceFieldSelectorAddon | None = None
    area: ServiceFieldSelectorArea | None = None
    areas_display: ServiceFieldSelectorAreasDisplay | None = None
    attribute: ServiceFieldSelectorAttribute | None = None
    assist_pipeline: ServiceFieldSelectorAssistPipeline | None = None
    backup_location: ServiceFieldSelectorBackupLocation | None = None
    background: ServiceFieldSelectorBackground | None = None
    boolean: ServiceFieldSelectorBoolean | None = None
    button_toggle: ServiceFieldSelectorButtonToggle | None = None
    color_rgb: ServiceFieldSelectorColorRGB | None = None
    color_temp: ServiceFieldSelectorColorTemp | None = None
    condition: ServiceFieldSelectorCondition | None = None
    config_entry: ServiceFieldSelectorConfigEntry | None = None
    constant: ServiceFieldSelectorConstant | None = None
    conversation_agent: ServiceFieldSelectorConversationAgent | None = None
    country: ServiceFieldSelectorCountry | None = None
    date: ServiceFieldSelectorDate | None = None
    datetime: ServiceFieldSelectorDateTime | None = None
    device: ServiceFieldSelectorDevice | ServiceFieldSelectorDeviceLegacy | None = None
    duration: ServiceFieldSelectorDuration | None = None
    entity: ServiceFieldSelectorEntity | ServiceFieldSelectorEntityLegacy | None = None
    floor: ServiceFieldSelectorFloor | None = None
    file: ServiceFieldSelectorFile | None = None
    icon: ServiceFieldSelectorIcon | None = None
    image: ServiceFieldSelectorImage | None = None
    label: ServiceFieldSelectorLabel | None = None
    language: ServiceFieldSelectorLanguage | None = None
    location: ServiceFieldSelectorLocation | None = None
    media: ServiceFieldSelectorMedia | None = None
    navigation: ServiceFieldSelectorNavigation | None = None
    number: ServiceFieldSelectorNumber | None = None
    object: ServiceFieldSelectorObject | None = None
    qr_code: ServiceFieldSelectorQRCode | None = None
    select: ServiceFieldSelectorSelect | None = None
    selector: ServiceFieldSelectorSelector | None = None
    state: ServiceFieldSelectorState | None = None
    statistic: ServiceFieldSelectorStatistic | None = None
    target: ServiceFieldSelectorTarget | None = None
    template: ServiceFieldSelectorTemplate | None = None
    stt: ServiceFieldSelectorSTT | None = None
    text: ServiceFieldSelectorText | None = None
    theme: ServiceFieldSelectorTheme | None = None
    time: ServiceFieldSelectorTime | None = None
    trigger: ServiceFieldSelectorTrigger | None = None
    tts: ServiceFieldSelectorTTS | None = None
    tts_voice: ServiceFieldSelectorTTSVoice | None = None
    ui_action: ServiceFieldSelectorUIAction | None = None
    ui_color: ServiceFieldSelectorUIColor | None = None
    ui_state_content: ServiceFieldSelectorUIStateContext | None = None


# Service bases
class ServiceFieldFilter(BaseModel):
    supported_features: list[int] | int | None = (
        None  # Bitset (any needs to be supported [or all within specified list])
    )
    attribute: dict[str, list[str] | str] | None = None


class ServiceField(BaseModel):
    """Model for service parameters/fields."""

    description: str | None = None
    example: Any | None = None
    default: Any | None = None
    name: str | None = None
    required: bool | None = None
    advanced: bool | None = None
    selector: ServiceFieldSelector | None = None
    filter: ServiceFieldFilter | None = None


class ServiceFieldCollection(BaseModel):
    collapsed: bool | None = None
    fields: dict[str, ServiceField]


class ServiceResponse(BaseModel):
    optional: bool | None = None


class BaseService(BaseModel):
    """Model representing services from homeassistant"""

    service_id: str
    name: str | None = None
    description: str | None = None
    fields: dict[str, ServiceField | ServiceFieldCollection] | None = None
    target: ServiceFieldSelectorTarget | None = None
    response: ServiceResponse | None = None


class Service(BaseService):
    """Sync service with sync trigger method."""

    domain: Domain = Field(exclude=True, repr=False)

    def trigger(
        self,
        **service_data: Any,
    ) -> (
        tuple[State, ...]
        | tuple[tuple[State, ...], dict[str, Any]]
        | dict[str, Any]
        | None
    ):
        """Triggers the service associated with this object."""
        try:
            return self.domain.client.trigger_service_with_response(
                self.domain.domain_id,
                self.service_id,
                **service_data,
            )
        except (RequestError, ResponseError):
            return self.domain.client.trigger_service(
                self.domain.domain_id,
                self.service_id,
                **service_data,
            )

    def __call__(
        self,
        **service_data: Any,
    ) -> (
        tuple[State, ...]
        | tuple[tuple[State, ...], dict[str, Any]]
        | dict[str, Any]
        | None
    ):
        """Calls the service associated with this object."""
        return self.trigger(**service_data)


class AsyncService(BaseService):
    """Async service with async trigger method."""

    domain: AsyncDomain = Field(exclude=True, repr=False)

    async def trigger(
        self,
        **service_data: Any,
    ) -> (
        tuple[State, ...]
        | tuple[tuple[State, ...], dict[str, Any]]
        | dict[str, Any]
        | None
    ):
        """Triggers the service associated with this object."""
        try:
            return await self.domain.client.trigger_service_with_response(
                self.domain.domain_id,
                self.service_id,
                **service_data,
            )
        except (RequestError, ResponseError):
            return await self.domain.client.trigger_service(
                self.domain.domain_id,
                self.service_id,
                **service_data,
            )

    async def __call__(
        self,
        **service_data: Any,
    ) -> (
        tuple[State, ...]
        | tuple[tuple[State, ...], dict[str, Any]]
        | dict[str, Any]
        | None
    ):
        """Calls the service associated with this object."""
        return await self.trigger(**service_data)
