"""Structured progress notifications independent of terminal rendering."""

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class ProgressEvent:
    """A measured stage transition or transport byte counter."""

    stage: str
    completed: int | None = None
    total: int | None = None


type ProgressCallback = Callable[[ProgressEvent], None]


def emit(callback: ProgressCallback | None, stage: str, **counts: int | None) -> None:
    """Notify an optional consumer without printing from library code."""
    if callback:
        callback(ProgressEvent(stage, **counts))
