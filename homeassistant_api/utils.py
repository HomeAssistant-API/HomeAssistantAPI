import os
import re
from typing import TYPE_CHECKING, Optional, Union  # noqa: F401

from typing_extensions import TypeAliasType

if TYPE_CHECKING or os.getenv("DOCUMENTATION_MODE") != "true":
    JSONType = TypeAliasType(
        "JSONType", "Optional[Union[int, float, str, bool, list[JSONType], dict[str, JSONType]]]"
    )
else:
    JSONType = type("JSONType", (object,), {})


def format_entity_id(entity_id: str) -> str:
    """Takes in a string and formats it into valid snake_case."""
    entity_id = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", entity_id)
    entity_id = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", entity_id)
    entity_id = entity_id.replace("-", "_")
    return entity_id.lower()


def prepare_entity_id(
    *,
    group_id: Optional[str] = None,
    slug: Optional[str] = None,
    entity_id: Optional[str] = None,
) -> str:
    """
    Combines optional :code:`group` and :code:`slug` into an :code:`entity_id` if provided.
    Favors :code:`entity_id` over :code:`group` or :code:`slug`.
    """
    if (group_id is None or slug is None) and entity_id is None:
        raise ValueError(
            "To use group or slug you need to pass both, not just one. "
            "Otherwise pass entity_id. "
            "Also make sure you are using keyword arguments."
        )
    if group_id is not None and slug is not None:
        entity_id = f"{group_id}.{slug}"
    assert entity_id is not None
    return format_entity_id(entity_id)
