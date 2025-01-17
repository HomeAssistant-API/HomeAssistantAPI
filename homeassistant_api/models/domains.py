"""File for Service and Domain data models"""

import gc
import inspect
from typing import TYPE_CHECKING, Any, Coroutine, Dict, Optional, Tuple, Union, cast

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


class ServiceField(BaseModel):
    """Model for service parameters/fields."""

    description: Optional[str] = None
    example: Any = None
    selector: Optional[Dict[str, Any]] = None
    name: Optional[str] = None
    required: Optional[bool] = None


class Service(BaseModel):
    """Model representing services from homeassistant"""

    service_id: str
    domain: Domain = Field(exclude=True, repr=False)
    name: Optional[str] = None
    description: Optional[str] = None
    fields: Optional[Dict[str, ServiceField]] = None

    def trigger(self, entity_id: Optional[str] = None, **service_data) -> Union[
        Tuple[State, ...],
        Tuple[Tuple[State, ...], Dict[str, Any]],
        dict[str, Any],
        None,
    ]:
        """Triggers the service associated with this object."""
        if entity_id is not None:
            service_data["entity_id"] = entity_id
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
