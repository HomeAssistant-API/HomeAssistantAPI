"""File for Service and Domain data models"""

import gc
import inspect
from typing import TYPE_CHECKING, Any, Coroutine, Dict, Optional, Tuple, Union, cast, List

from pydantic import Field

from homeassistant_api.errors import RequestError

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
        cls, json: Dict[str, Any], client: Union["Client", "WebsocketClient"]
    ) -> "Domain":
        """Constructs Domain and Service models from json data."""
        if "domain" not in json or "services" not in json:
            raise ValueError("Missing services or domain attribute in json argument.")
        domain = cls(domain_id=cast(str, json.get("domain")), _client=client)
        services = json.get("services")
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

''' TODO: Shall we use that?
class ServiceFieldSelectorText(BaseModel):
    multiple: Optional[bool] = None # Submitted as List[str] if multiple

class ServiceFieldSelectorNumber(BaseModel):
    mode: Optional[str] = None
    step: Optional[str | float | int] = None
    min: Optional[float | int] = None
    max: Optional[float | int] = None
    unit_of_measurement: Optional[str] = None
    unit: Optional[str] = None

class ServiceFieldSelectorEntity(BaseModel):
    multiple: Optional[bool] = None # Submitted as List[str] if multiple
    integration: Optional[str] = None
    domain: Optional[str] = None
  
class ServiceFieldSelectorDevice(BaseModel):
    multiple: Optional[bool] = None # Submitted as List[str] if multiple
    integration: Optional[str] = None
    domain: Optional[str] = None

class ServiceFieldSelectorSelect(BaseModel):
    options: List[str]
    translation_key: Optional[str] = None
    multiple: Optional[bool] = None # Submitted as List[str] if multiple

class ServiceFieldSelectorBoolean(BaseModel):
    pass

class ServiceFieldSelectorTheme(BaseModel):
    include_default: Optional[bool] = None

class ServiceFieldSelectorConstant(BaseModel):
    label: str
    value: bool

class ServiceFieldSelectorObject(BaseModel):
    pass

class ServiceFieldSelector(BaseModel):
    text: Optional[ServiceFieldSelectorText] = None
    config_entry: Optional[ServiceFieldSelectorText] = None # Treat like text
    conversation_agent: Optional[ServiceFieldSelectorText] = None # Treat like text
    number: Optional[ServiceFieldSelectorNumber] = None
    duration: Optional[ServiceFieldSelectorText] = None # Treat like text
    entity: Optional[ServiceFieldSelectorEntity] = None
    select: Optional[ServiceFieldSelectorSelect] = None
    boolean: Optional[ServiceFieldSelectorBoolean] = None
    theme: Optional[ServiceFieldSelectorTheme] = None
    color_temp: Optional[ServiceFieldSelectorNumber] = None
    datetime: Optional[ServiceFieldSelectorText] = None # Treat like text
    time: Optional[ServiceFieldSelectorText] = None # Treat like text
    date: Optional[ServiceFieldSelectorText] = None # Treat like text
    statistic: Optional[ServiceFieldSelectorEntity] = None # Treat like entities
    object: Optional[ServiceFieldSelectorObject] = None
    template: Optional[ServiceFieldSelectorText] = None # Treat like text
    color_rgb: Optional[ServiceFieldSelectorObject] = None # Treat like object
    device: Optional[ServiceFieldSelectorDevice] = None # Treat like entity
    icon: Optional[ServiceFieldSelectorText] = None # Treat like text
    constant: Optional[ServiceFieldSelectorConstant] = None
'''

class ServiceFieldFilter(BaseModel):
    supported_features: Optional[List[int] | int] = None # Bitset (any needs to be supported)
    attribute: Optional[Dict[str, List[str] | str]] = None

class ServiceField(BaseModel):
    """Model for service parameters/fields."""

    description: Optional[str] = None
    example: Optional[Any] = None # Afaik its one of the following: str | int | float | bool | List[str] | Dict
    default: Optional[Any] = None
    name: Optional[str] = None
    required: Optional[bool] = None
    advanced: Optional[bool] = None
    selector: Optional[Dict[str, Any]] = None # TODO: I believe it would be beneficial to parse it the way I do
    filter: Optional[ServiceFieldFilter] = None

class ServiceFieldCollection(BaseModel):
    collapsed: Optional[bool] = None
    fields: Dict[str, ServiceField]

class ServiceTargetDevice(BaseModel):
    pass # Not really sure what it's used for - it's only in one place (reload config entries)

class ServiceTargetEntity(BaseModel):
    domain: Optional[List[str]] = None
    supported_features: Optional[List[int] | int] = None # Bitset flags
    integration: Optional[str] = None
    # `area_id``, `device_id``, `entity_id`, `label_id` can be passed as a target

class ServiceTarget(BaseModel):
    device: Optional[ServiceTargetDevice] = None # Not currently used for anything? (The only action which has it also has `entity` target)
    entity: Optional[ServiceTargetEntity] = None

class ServiceResponse(BaseModel):
    optional: Optional[bool] = None

class Service(BaseModel):
    """Model representing services from homeassistant"""

    service_id: str
    domain: Domain = Field(exclude=True, repr=False)
    name: Optional[str] = None
    description: Optional[str] = None
    fields: Optional[Dict[str, ServiceField | ServiceFieldCollection]] = None
    target: Optional[ServiceTarget] = None
    response: Optional[ServiceResponse] = None

    def trigger(self, entity_id: Optional[str] = None, **service_data) -> Union[
        Tuple[State, ...],
        Tuple[Tuple[State, ...], Dict[str, Any]],
        dict[str, Any],
        None,
    ]:
        """Triggers the service associated with this object."""
        if entity_id is not None:
            service_data["entity_id"] = entity_id # TODO: I believe the function should not enforce the target to be `entity_id` as it can be one of the following: `area_id``, `device_id``, `entity_id`, `label_id`
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
        self, entity_id: Optional[str] = None, **service_data
    ) -> Union[Tuple[State, ...], Tuple[Tuple[State, ...], Dict[str, Any]]]:
        """Triggers the service associated with this object."""
        if entity_id is not None:
            service_data["entity_id"] = entity_id

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

    def __call__(self, entity_id: Optional[str] = None, **service_data) -> Union[
        Union[
            Tuple[State, ...],
            Tuple[Tuple[State, ...], Dict[str, Any]],
            dict[str, Any],
            None,
        ],
        Coroutine[
            Any, Any, Union[Tuple[State, ...], Tuple[Tuple[State, ...], Dict[str, Any]]]
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
                return self.async_trigger(entity_id=entity_id, **service_data)
        except IndexError:  # pragma: no cover
            pass
        return self.trigger(entity_id=entity_id, **service_data)
