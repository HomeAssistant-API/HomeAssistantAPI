"""File for Service and Domain data models"""

from __future__ import annotations

import gc
import inspect
from enum import Enum
from typing import (
    TYPE_CHECKING,
    Any,
    Coroutine,
    Dict,
    List,
    Optional,
    Tuple,
    Union,
    cast,
)

from pydantic import Field

from homeassistant_api.errors import RequestError
from homeassistant_api.utils import JSONType

from .base import BaseModel
from .states import State

if TYPE_CHECKING:
    from homeassistant_api import Client, WebsocketClient


class Domain(BaseModel):
    """Model representing the domain that services belong to."""

    def __init__(
        self,
        *args,
        _client: Optional[Union["Client", "WebsocketClient"]] = None,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        if _client is None:
            raise ValueError("No client passed.")
        object.__setattr__(self, "_client", _client)

    _client: Union["Client", "WebsocketClient"]
    domain_id: str = Field(
        ...,
        description="The name of the domain that services belong to. "
        "(e.g. :code:`frontend` in :code:`frontend.reload_themes`",
    )
    services: Dict[str, "Service"] = Field(
        {},
        description="A dictionary of all services belonging to the domain indexed by their names",
    )

    @classmethod
    def from_json(
        cls, json: Dict[str, JSONType], client: Union["Client", "WebsocketClient"]
    ) -> "Domain":
        """Constructs Domain and Service models from json data."""
        if "domain" not in json or "services" not in json:
            raise ValueError("Missing services or domain attribute in json argument.")
        domain = cls(domain_id=cast(str, json.get("domain")), _client=client)
        services = cast(dict[str, dict[str, JSONType]], json.get("services"))
        assert isinstance(services, dict)
        for service_id, data in services.items():
            domain._add_service(service_id, **data)
        return domain

    def _add_service(self, service_id: str, **data) -> None:
        """Registers services into a domain to be used or accessed. Used internally."""
        # raise ValueError(data)
        self.services.update(
            {
                service_id: Service(
                    service_id=service_id,
                    domain=self,
                    **data,
                )
            }
        )

    def get_service(self, service_id: str) -> Optional["Service"]:
        """Return a Service with the given service_id, returns None if no such service exists"""
        return self.services.get(service_id)

    def __getattr__(self, attr: str):
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


# Sources:
# https://developers.home-assistant.io/docs/dev_101_services/
# https://www.home-assistant.io/docs/blueprint/selectors/#date-selector
# https://github.com/home-assistant/frontend/blob/dev/src/data/selector.ts
# https://github.com/home-assistant/home-assistant-js-websocket/blob/master/lib/types.ts


# Helpers
class ServiceFieldSelectorEntityFilter(BaseModel):
    integration: Optional[str] = None
    domain: Optional[Union[List[str], str]] = None
    device_class: Optional[Union[List[str], str]] = None
    supported_features: Optional[Union[List[int], int]] = None


class ServiceFieldSelectorDeviceFilter(BaseModel):
    integration: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    model_id: Optional[str] = None


class CropOptions(BaseModel):
    round: bool
    type: Optional[str] = None  # "image/jpeg" / "image/png"
    quality: Optional[Union[int, float]] = None
    aspectRatio: Optional[Union[int, float]] = None


class SelectBoxOptionImage(BaseModel):
    src: str
    src_dark: Optional[str] = None
    flip_rtl: Optional[bool] = None


class ServiceFieldSelectorNumberMode(str, Enum):
    BOX = "box"
    SLIDER = "slider"


class ServiceFieldSelectorSelectMode(str, Enum):
    LIST = "list"
    DROPDOWN = "dropdown"
    BOX = "box"


class ServiceFieldSelectorQRCodeErrorCorrectionLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    QUARTILE = "quartile"
    HIGH = "high"


class ServiceFieldSelectorTextType(str, Enum):
    NUMBER = "number"
    TEXT = "text"
    SEARCH = "search"
    TEL = "tel"
    URL = "url"
    EMAIL = "email"
    PASSWORD = "password"
    DATE = "date"
    MONTH = "month"
    WEEK = "week"
    TIME = "time"
    DATETIME_LOCAL = "datetime-local"
    COLOR = "color"


# Selectors
class ServiceFieldSelectorAction(BaseModel):
    optionsInSidebar: Optional[bool] = None


class ServiceFieldSelectorAddon(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None


class ServiceFieldSelectorArea(BaseModel):
    entity: Optional[
        Union[List[ServiceFieldSelectorEntityFilter], ServiceFieldSelectorEntityFilter]
    ] = None
    device: Optional[
        Union[List[ServiceFieldSelectorDeviceFilter], ServiceFieldSelectorDeviceFilter]
    ] = None
    multiple: Optional[bool] = None


class ServiceFieldSelectorAreasDisplay(BaseModel):
    pass


class ServiceFieldSelectorAttribute(BaseModel):
    entity_id: Optional[Union[List[str], str]] = None
    hide_attributes: Optional[List[str]] = None


class ServiceFieldSelectorAssistPipeline(BaseModel):
    include_last_used: Optional[bool] = None


class ServiceFieldSelectorBackground(BaseModel):
    original: Optional[bool] = None
    crop: Optional[CropOptions] = None


class ServiceFieldSelectorBackupLocation(BaseModel):
    pass


class ServiceFieldSelectorBoolean(BaseModel):
    pass


class ServiceFieldSelectorButtonToggle(BaseModel):
    options: List[Union[str, ServiceFieldSelectorSelectOption]]
    translation_key: Optional[str] = None
    sort: Optional[bool] = None


class ServiceFieldSelectorColorRGB(BaseModel):
    pass


class ServiceFieldSelectorColorTemp(BaseModel):
    unit: Optional[str] = None
    min: Optional[Union[int, float]] = None
    max: Optional[Union[int, float]] = None
    min_mireds: Optional[Union[int, float]] = None
    max_mireds: Optional[Union[int, float]] = None


class ServiceFieldSelectorCondition(BaseModel):
    optionsInSidebar: Optional[bool] = None


class ServiceFieldSelectorConfigEntry(BaseModel):
    integration: Optional[str] = None


class ServiceFieldSelectorConstant(BaseModel):
    label: Optional[str] = None
    value: Union[str, int, float, bool]
    translation_key: Optional[str] = None


class ServiceFieldSelectorConversationAgent(BaseModel):
    language: Optional[str] = None  # filtering by language not supported


class ServiceFieldSelectorCountry(BaseModel):
    countries: List[str]
    no_sort: Optional[bool] = None


class ServiceFieldSelectorDate(BaseModel):
    pass


class ServiceFieldSelectorDateTime(BaseModel):
    pass


class ServiceFieldSelectorDevice(BaseModel):
    entity: Optional[
        Union[List[ServiceFieldSelectorEntityFilter], ServiceFieldSelectorEntityFilter]
    ] = None
    filter: Optional[
        Union[List[ServiceFieldSelectorDeviceFilter], ServiceFieldSelectorDeviceFilter]
    ] = None
    multiple: Optional[bool] = None


class ServiceFieldSelectorDeviceLegacy(ServiceFieldSelectorDevice):
    integration: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None


class ServiceFieldSelectorDuration(BaseModel):
    enable_day: Optional[bool] = None
    enable_millisecond: Optional[bool] = None


class ServiceFieldSelectorEntity(BaseModel):
    multiple: Optional[bool] = None
    include_entities: Optional[List[str]] = None
    exclude_entities: Optional[List[str]] = None
    filter: Optional[
        Union[List[ServiceFieldSelectorEntityFilter], ServiceFieldSelectorEntityFilter]
    ] = None
    reorder: Optional[bool] = None


class ServiceFieldSelectorEntityLegacy(ServiceFieldSelectorEntity):
    integration: Optional[str] = None
    domain: Optional[Union[List[str], str]] = None
    device_class: Optional[Union[List[str], str]] = None


class ServiceFieldSelectorFloor(BaseModel):
    entity: Optional[
        Union[List[ServiceFieldSelectorEntityFilter], ServiceFieldSelectorEntityFilter]
    ] = None
    device: Optional[
        Union[List[ServiceFieldSelectorDeviceFilter], ServiceFieldSelectorDeviceFilter]
    ] = None
    multiple: Optional[bool] = None


class ServiceFieldSelectorFile(BaseModel):
    accept: str


class ServiceFieldSelectorIcon(BaseModel):
    placeholder: Optional[str] = None
    fallbackPath: Optional[str] = None


class ServiceFieldSelectorImage(BaseModel):
    original: Optional[bool] = None
    crop: Optional[CropOptions] = None


class ServiceFieldSelectorLabel(BaseModel):
    multiple: Optional[bool] = None


class ServiceFieldSelectorLanguage(BaseModel):
    languages: Optional[List[str]] = None
    native_name: Optional[bool] = None
    no_sort: Optional[bool] = None


class ServiceFieldSelectorLocation(BaseModel):
    radius: Optional[bool] = None
    radius_readonly: Optional[bool] = None
    icon: Optional[str] = None


class ServiceFieldSelectorMedia(BaseModel):
    accept: Optional[List[str]] = None
    multiple: bool = False


class ServiceFieldSelectorNavigation(BaseModel):
    pass


class ServiceFieldSelectorNumber(BaseModel):
    min: Optional[Union[int, float]] = None
    max: Optional[Union[int, float]] = None
    step: Optional[Union[Union[int, float], str]] = None
    unit_of_measurement: Optional[str] = None
    mode: Optional[ServiceFieldSelectorNumberMode] = None
    slider_ticks: Optional[bool] = None
    translation_key: Optional[str] = None


class ServiceFieldSelectorObjectField(BaseModel):
    selector: ServiceFieldSelector
    label: Optional[str] = None
    required: Optional[bool] = None


class ServiceFieldSelectorObject(BaseModel):
    label_field: Optional[str] = None
    description_field: Optional[str] = None
    translation_key: Optional[str] = None
    fields: Optional[Dict[str, ServiceFieldSelectorObjectField]] = None
    multiple: Optional[bool] = None


class ServiceFieldSelectorQRCode(BaseModel):
    data: str
    scale: Optional[Union[int, float]] = None
    error_correction_level: Optional[ServiceFieldSelectorQRCodeErrorCorrectionLevel] = (
        None
    )
    center_image: Optional[str] = None


class ServiceFieldSelectorSelectOption(BaseModel):
    label: str
    value: Any
    description: Optional[str] = None
    image: Optional[Union[str, SelectBoxOptionImage]] = None
    disable: Optional[bool] = None


class ServiceFieldSelectorSelect(BaseModel):
    multiple: Optional[bool] = None
    custom_value: Optional[bool] = None
    mode: Optional[ServiceFieldSelectorSelectMode] = None
    options: List[Union[str, ServiceFieldSelectorSelectOption]]
    translation_key: Optional[str] = None
    sort: Optional[bool] = None
    reorder: Optional[bool] = None
    box_max_columns: Optional[int] = None


class ServiceFieldSelectorSelector(BaseModel):
    pass


class ServiceFieldSelectorStateOption(BaseModel):
    label: str
    value: Any


class ServiceFieldSelectorState(BaseModel):
    extra_options: Optional[List[ServiceFieldSelectorStateOption]] = None
    entity_id: Optional[Union[str, List[str]]] = None
    attribute: Optional[str] = None
    hide_states: Optional[List[str]] = None
    multiple: Optional[bool] = None


class ServiceFieldSelectorStatistic(BaseModel):
    device_class: Optional[str] = None
    multiple: Optional[bool] = None


class ServiceFieldSelectorTarget(BaseModel):
    entity: Optional[
        Union[List[ServiceFieldSelectorEntityFilter], ServiceFieldSelectorEntityFilter]
    ] = None
    device: Optional[
        Union[List[ServiceFieldSelectorDeviceFilter], ServiceFieldSelectorDeviceFilter]
    ] = None


class ServiceFieldSelectorTemplate(BaseModel):
    pass


class ServiceFieldSelectorSTT(BaseModel):
    language: Optional[str] = None


class ServiceFieldSelectorText(BaseModel):
    multiline: Optional[bool] = None
    type: Optional[ServiceFieldSelectorTextType] = None
    prefix: Optional[str] = None
    suffix: Optional[str] = None
    autocomplete: Optional[str] = None
    multiple: Optional[bool] = None


class ServiceFieldSelectorTheme(BaseModel):
    include_default: Optional[bool] = None


class ServiceFieldSelectorTime(BaseModel):
    no_second: Optional[bool] = None


class ServiceFieldSelectorTrigger(BaseModel):
    pass


class ServiceFieldSelectorTTS(BaseModel):
    language: Optional[str] = None


class ServiceFieldSelectorTTSVoice(BaseModel):
    engineId: Optional[str] = None
    language: Optional[str] = None


class ServiceFieldSelectorUIAction(BaseModel):
    pass


class ServiceFieldSelectorUIColor(BaseModel):
    default_color: Optional[str] = None
    include_none: Optional[bool] = None
    include_state: Optional[bool] = None


class ServiceFieldSelectorUIStateContext(BaseModel):
    entity_id: Optional[str] = None
    allow_name: Optional[bool] = None


# fields.file.ServiceField.selector.media.multiple
#   Extra inputs are not permitted [type=extra_forbidden, input_value=False, input_type=bool]
#     For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
# fields.file.ServiceFieldCollection.fields
#   Field required [type=missing, input_value={'required': True, 'selec...'], 'multiple': False}}}, input_type=dict]
#     For further information visit https://errors.pydantic.dev/2.12/v/missing
# fields.file.ServiceFieldCollection.required
#   Extra inputs are not permitted [type=extra_forbidden, input_value=True, input_type=bool]
#     For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
# fields.file.ServiceFieldCollection.selector
#   Extra inputs are not permitted [type=extra_forbidden, input_value={'media': {'accept': ['im...*'], 'multiple': False}}, input_type=dict]
#     For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden

# fields.media.ServiceField.selector.media.multiple
#   Extra inputs are not permitted [type=extra_forbidden, input_value=False, input_type=bool]
#     For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden

# fields.media.ServiceFieldCollection.fields
#   Field required [type=missing, input_value={'required': True, 'selec...ontent_type": "music"}'}, input_type=dict]
#     For further information visit https://errors.pydantic.dev/2.12/v/missing
# fields.media.ServiceFieldCollection.required
#   Extra inputs are not permitted [type=extra_forbidden, input_value=True, input_type=bool]
#     For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
# fields.media.ServiceFieldCollection.selector
#   Extra inputs are not permitted [type=extra_forbidden, input_value={'media': {'multiple': False}}, input_type=dict]
#     For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
# fields.media.ServiceFieldCollection.example
#   Extra inputs are not permitted [type=extra_forbidden, input_value='{"media_content_id": "ht...content_type": "music"}', input_type=str]
#     For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden

# fields.media.ServiceField.selector.media.multiple
# Extra inputs are not permitted [type=extra_forbidden, input_value=False, input_type=bool]
#   For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
# fields.media.ServiceFieldCollection.fields
# Field required [type=missing, input_value={'required': True, 'selec...ontent_type": "music"}'}, input_type=dict]
#   For further information visit https://errors.pydantic.dev/2.12/v/missing
# fields.media.ServiceFieldCollection.required
# Extra inputs are not permitted [type=extra_forbidden, input_value=True, input_type=bool]
#   For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
# fields.media.ServiceFieldCollection.selector
# Extra inputs are not permitted [type=extra_forbidden, input_value={'media': {'multiple': False}}, input_type=dict]
#   For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
# fields.media.ServiceFieldCollection.example
# Extra inputs are not permitted [type=extra_forbidden, input_value='{"media_content_id": "ht...content_type": "music"}', input_type=str]
#   For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden```

class ServiceFieldSelector(BaseModel):
    action: Optional[ServiceFieldSelectorAction] = None
    addon: Optional[ServiceFieldSelectorAddon] = None
    area: Optional[ServiceFieldSelectorArea] = None
    areas_display: Optional[ServiceFieldSelectorAreasDisplay] = None
    attribute: Optional[ServiceFieldSelectorAttribute] = None
    assist_pipeline: Optional[ServiceFieldSelectorAssistPipeline] = None
    backup_location: Optional[ServiceFieldSelectorBackupLocation] = None
    background: Optional[ServiceFieldSelectorBackground] = None
    boolean: Optional[ServiceFieldSelectorBoolean] = None
    button_toggle: Optional[ServiceFieldSelectorButtonToggle] = None
    color_rgb: Optional[ServiceFieldSelectorColorRGB] = None
    color_temp: Optional[ServiceFieldSelectorColorTemp] = None
    condition: Optional[ServiceFieldSelectorCondition] = None
    config_entry: Optional[ServiceFieldSelectorConfigEntry] = None
    constant: Optional[ServiceFieldSelectorConstant] = None
    conversation_agent: Optional[ServiceFieldSelectorConversationAgent] = None
    country: Optional[ServiceFieldSelectorCountry] = None
    date: Optional[ServiceFieldSelectorDate] = None
    datetime: Optional[ServiceFieldSelectorDateTime] = None
    device: Optional[
        Union[ServiceFieldSelectorDevice, ServiceFieldSelectorDeviceLegacy]
    ] = None
    duration: Optional[ServiceFieldSelectorDuration] = None
    entity: Optional[
        Union[ServiceFieldSelectorEntity, ServiceFieldSelectorEntityLegacy]
    ] = None
    floor: Optional[ServiceFieldSelectorFloor] = None
    file: Optional[ServiceFieldSelectorFile] = None
    icon: Optional[ServiceFieldSelectorIcon] = None
    image: Optional[ServiceFieldSelectorImage] = None
    label: Optional[ServiceFieldSelectorLabel] = None
    language: Optional[ServiceFieldSelectorLanguage] = None
    location: Optional[ServiceFieldSelectorLocation] = None
    media: Optional[ServiceFieldSelectorMedia] = None
    navigation: Optional[ServiceFieldSelectorNavigation] = None
    number: Optional[ServiceFieldSelectorNumber] = None
    object: Optional[ServiceFieldSelectorObject] = None
    qr_code: Optional[ServiceFieldSelectorQRCode] = None
    select: Optional[ServiceFieldSelectorSelect] = None
    selector: Optional[ServiceFieldSelectorSelector] = None
    state: Optional[ServiceFieldSelectorState] = None
    statistic: Optional[ServiceFieldSelectorStatistic] = None
    target: Optional[ServiceFieldSelectorTarget] = None
    template: Optional[ServiceFieldSelectorTemplate] = None
    stt: Optional[ServiceFieldSelectorSTT] = None
    text: Optional[ServiceFieldSelectorText] = None
    theme: Optional[ServiceFieldSelectorTheme] = None
    time: Optional[ServiceFieldSelectorTime] = None
    trigger: Optional[ServiceFieldSelectorTrigger] = None
    tts: Optional[ServiceFieldSelectorTTS] = None
    tts_voice: Optional[ServiceFieldSelectorTTSVoice] = None
    ui_action: Optional[ServiceFieldSelectorUIAction] = None
    ui_color: Optional[ServiceFieldSelectorUIColor] = None
    ui_state_content: Optional[ServiceFieldSelectorUIStateContext] = None


# Service bases
class ServiceFieldFilter(BaseModel):
    supported_features: Optional[Union[List[int], int]] = (
        None  # Bitset (any needs to be supported [or all within specified list])
    )
    attribute: Optional[Dict[str, Union[List[str], str]]] = None


class ServiceField(BaseModel):
    """Model for service parameters/fields."""

    description: Optional[str] = None
    example: Optional[JSONType] = None
    default: Optional[JSONType] = None
    name: Optional[str] = None
    required: Optional[bool] = None
    advanced: Optional[bool] = None
    selector: Optional[ServiceFieldSelector] = None
    filter: Optional[ServiceFieldFilter] = None


class ServiceFieldCollection(BaseModel):
    collapsed: Optional[bool] = None
    fields: Dict[str, ServiceField]


class ServiceResponse(BaseModel):
    optional: Optional[bool] = None


class Service(BaseModel):
    """Model representing services from homeassistant"""

    service_id: str
    domain: Domain = Field(exclude=True, repr=False)
    name: Optional[str] = None
    description: Optional[str] = None
    fields: Optional[Dict[str, Union[ServiceField, ServiceFieldCollection]]] = None
    target: Optional[ServiceFieldSelectorTarget] = None
    response: Optional[ServiceResponse] = None

    def trigger(self, **service_data) -> Union[
        Tuple[State, ...],
        Tuple[Tuple[State, ...], dict[str, JSONType]],
        dict[str, JSONType],
        None,
    ]:
        """Triggers the service associated with this object."""
        try:
            return self.domain._client.trigger_service_with_response(
                self.domain.domain_id,
                self.service_id,
                **service_data,
            )
        except RequestError:
            return self.domain._client.trigger_service(
                self.domain.domain_id,
                self.service_id,
                **service_data,
            )

    async def async_trigger(
        self, **service_data
    ) -> Union[Tuple[State, ...], Tuple[Tuple[State, ...], dict[str, JSONType]]]:
        """Triggers the service associated with this object."""
        from homeassistant_api import WebsocketClient  # prevent circular import

        if isinstance(self.domain._client, WebsocketClient):
            raise NotImplementedError(
                "WebsocketClient does not support async/await syntax."
            )
        try:
            return await self.domain._client.async_trigger_service_with_response(
                self.domain.domain_id,
                self.service_id,
                **service_data,
            )
        except RequestError:
            return await self.domain._client.async_trigger_service(
                self.domain.domain_id,
                self.service_id,
                **service_data,
            )

    def __call__(self, **service_data) -> Union[
        Union[
            Tuple[State, ...],
            Tuple[Tuple[State, ...], dict[str, JSONType]],
            dict[str, JSONType],
            None,
        ],
        Coroutine[
            Any,
            Any,
            Union[Tuple[State, ...], Tuple[Tuple[State, ...], dict[str, JSONType]]],
        ],
    ]:
        """
        Triggers the service associated with this object.
        """
        assert (frame := inspect.currentframe()) is not None
        assert (parent_frame := frame.f_back) is not None
        try:
            if inspect.iscoroutinefunction(
                caller := gc.get_referrers(parent_frame.f_code)[0]
            ) or inspect.iscoroutine(caller):
                return self.async_trigger(**service_data)
        except IndexError:  # pragma: no cover
            pass
        return self.trigger(**service_data)
