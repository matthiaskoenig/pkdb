"""Strict JSON reading and canonical JSON writing for study folders."""

import json
import math
import re

MAX_DEPTH = 64
"""Deepest array/object nesting accepted; independent of the interpreter's stack size."""

# The only characters the depth scan cares about; everything else is skipped in C.
_SCAN_CHARS = re.compile(r'["\\\[\]{}]')


class JsonFileError(ValueError):
    """A JSON file that cannot be read; `code` is the issue code."""

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


def _check_depth(text: str) -> None:
    """Raise if arrays and objects nest deeper than MAX_DEPTH, in one linear pass.

    Brackets inside JSON strings do not count. Malformed text is left for `json.loads` to reject.
    """
    depth = 0
    in_string = False
    escaped_index = -1
    for match in _SCAN_CHARS.finditer(text):
        index = match.start()
        if index == escaped_index:
            continue
        char = match.group()
        if in_string:
            if char == "\\":
                escaped_index = index + 1
            elif char == '"':
                in_string = False
        elif char == '"':
            in_string = True
        elif char in "[{":
            depth += 1
            if depth > MAX_DEPTH:
                raise JsonFileError(
                    "invalid_json", f"JSON is nested deeper than {MAX_DEPTH} levels"
                )
        elif char in "]}":
            depth -= 1


def load_json(data: bytes) -> object:
    """Parse untrusted JSON; every problem becomes a JsonFileError."""
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise JsonFileError("invalid_encoding", "File is not UTF-8 encoded") from None
    _check_depth(text)
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
    """Canonical JSON text: indented by two spaces, non-ASCII kept, with a final newline.

    NaN and infinity raise `ValueError`.
    """
    return json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
