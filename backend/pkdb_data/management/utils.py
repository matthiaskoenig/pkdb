"""Utilities for data management."""

import json
import logging
from collections.abc import Iterable
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def ordered(obj: Any) -> Any:
    """Order given object.

    Only lists and dictionaries are ordered. Other objects are returned unchanged.
    """
    if isinstance(obj, dict):
        return sorted((k, ordered(v)) for k, v in obj.items())
    if isinstance(obj, list):
        return sorted(ordered(x) for x in obj)
    return obj


def recursive_iter(obj: Any, keys: tuple = ()) -> Iterable[tuple[tuple, Any]]:
    """Create dictionary with key:object from nested JSON data structure."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from recursive_iter(v, (*keys, k))
    elif any(isinstance(obj, t) for t in (list, tuple)):
        for idx, item in enumerate(obj):
            yield from recursive_iter(item, (*keys, idx))

        if len(obj) == 0:
            yield keys, None

    else:
        yield keys, obj


def set_keys(d: dict, value: Any, *keys: Any) -> None:
    """Change keys in nested dictionary."""
    for key in keys[:-1]:
        d = d[key]
    d[keys[-1]] = value


def read_json(path: Path) -> Any:
    """Read JSON.

    :param path: returns OrderedDict of JSON content, None if parsing is failing
    :return:
    """
    with open(path) as f:
        try:
            json_data = json.loads(
                f.read(),
                object_pairs_hook=ordered_dict_no_duplicates,
            )
        except json.decoder.JSONDecodeError as err:
            logger.error("%s\nin %s", err, path)
            return None
        except ValueError as err:
            logger.error("%s\nin %s", err, path)
            return None

    return json_data


def ordered_dict_no_duplicates(ordered_pairs: list[tuple[Any, Any]]) -> dict:
    """Reject duplicate keys and keep order."""
    d = {}
    for k, v in ordered_pairs:
        if k in d:
            raise ValueError(f"duplicate key: {k!r}")
        d[k] = v
    return d
