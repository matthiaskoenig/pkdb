"""Strict JSON reading and canonical JSON writing for study folders."""

import json
import math


class JsonFileError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise JsonFileError("duplicate_key", f"Duplicate key {key!r}")
        result[key] = value
    return result


def _constant(name: str):
    raise JsonFileError("invalid_json", f"{name} is not valid JSON")


def _float(text: str) -> float:
    value = float(text)
    if not math.isfinite(value):
        raise JsonFileError("invalid_json", f"The number {text} is out of range")
    return value


def load_json(data: bytes) -> object:
    """Parse untrusted JSON; every problem becomes a JsonFileError."""
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise JsonFileError("invalid_encoding", "File is not UTF-8 encoded") from None
    try:
        return json.loads(
            text,
            object_pairs_hook=_object,
            parse_constant=_constant,
            parse_float=_float,
        )
    except JsonFileError:
        raise
    except json.JSONDecodeError as error:
        raise JsonFileError(
            "invalid_json",
            f"Invalid JSON at line {error.lineno}, column {error.colno}: {error.msg}",
        ) from None
    except RecursionError:
        raise JsonFileError("invalid_json", "JSON is nested too deeply") from None
    except ValueError as error:
        # For example an integer with more digits than Python converts.
        raise JsonFileError("invalid_json", f"Invalid JSON: {error}") from None


def dump_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
