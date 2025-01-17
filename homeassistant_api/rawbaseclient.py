"""Module for parent RawWrapper class"""

from datetime import datetime
from posixpath import join
from typing import Any, Dict, Iterable, Optional, Tuple, Union

from .models import Entity


class RawBaseClient:
    """Builds, and makes requests to the API"""

    api_url: str
    token: str
    global_request_kwargs: Dict[str, Any]

    def __init__(
        self,
        api_url: str,
        token: str,
        *,
        global_request_kwargs: Optional[Dict[str, str]] = None,
    ) -> None:
        if global_request_kwargs is None:
            global_request_kwargs = {}
        self.api_url = api_url
        self.token = token
        self.global_request_kwargs = global_request_kwargs

        if not api_url.endswith("/"):
            self.api_url += "/"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.api_url!r})"

    def endpoint(self, *path: str) -> str:
        """Joins the api base url with a local path to an absolute url"""
        return join(self.api_url, *path)

    @property
    def _headers(self) -> Dict[str, str]:
        """Constructs the headers to send to the api for every request"""
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def prepare_headers(
        self,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, str]:
        """Prepares and verifies dictionary headers."""
        if headers is None:
            headers = {}
        if isinstance(headers, dict):
            headers.update(self._headers)
        else:
            raise ValueError(
                f"headers must be dict or dict subclass, not type {type(headers)!r}"
            )
        return headers

    @staticmethod
    def construct_params(params: Dict[str, Optional[str]]) -> str:
        """Custom method for constructing non-standard query strings"""
        return "&".join([k if v is None else f"{k}={v}" for k, v in params.items()])

    @staticmethod
    def prepare_get_entity_histories_params(
        entities: Optional[Tuple[Entity, ...]] = None,
        start_timestamp: Optional[datetime] = None,
        # Defaults to 1 day before. https://developers.home-assistant.io/docs/api/rest/
        end_timestamp: Optional[datetime] = None,
        significant_changes_only: bool = False,
    ) -> Tuple[Dict[str, Optional[str]], str]:
        """Pre-logic for `Client.get_entity_histories` and `Client.async_get_entity_histories`."""
        params: Dict[str, Optional[str]] = {}
        if entities is not None:
            params["filter_entity_id"] = ",".join([ent.entity_id for ent in entities])
        if end_timestamp is not None:
            params["end_time"] = (
                end_timestamp.isoformat()
            )  # Params are automatically URL encoded
        if significant_changes_only:
            params["significant_changes_only"] = None
        if start_timestamp is not None:
            url = join("history/period/", start_timestamp.isoformat())
        else:
            url = "history/period"
        return params, url

    @staticmethod
    def prepare_get_logbook_entry_params(
        filter_entities: Optional[Union[str, Iterable[str]]] = None,
        start_timestamp: Optional[
            Union[str, datetime]
        ] = None,  # Defaults to 1 day before
        end_timestamp: Optional[Union[str, datetime]] = None,
    ) -> Tuple[Dict[str, str], str]:
        """Prepares the query string and url path for retrieving logbook entries."""
        params: Dict[str, str] = {}
        if filter_entities is not None:
            params.update(
                {
                    "entity": (
                        filter_entities
                        if isinstance(filter_entities, str)
                        else ",".join(filter_entities)
                    )
                }
            )
        if end_timestamp is not None:
            if isinstance(end_timestamp, datetime):
                end_timestamp = end_timestamp.isoformat()
                # Parameters are already URL encoded automatically.
            params.update(end_time=end_timestamp)
        if start_timestamp is not None:
            if isinstance(start_timestamp, datetime):
                url = join("logbook/", start_timestamp.isoformat())
        else:
            url = "logbook"
        return params, url
