"""Versioned immutable reference data; loading never performs network lookups."""

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class MeasurementRule(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    name: str
    sid: str | None = None
    dtype: Literal[
        "numeric",
        "categorical",
        "boolean",
        "numeric_categorical",
        "abstract",
        "undefined",
    ] = "numeric"
    units: tuple[str, ...] = ()
    choices: tuple[str, ...] = ()
    can_negative: bool = False
    time_required: bool = False
    deprecated: bool = False


class SubstanceDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    name: str
    sid: str
    mass: float | None = Field(default=None, gt=0)
    formula: str | None = None
    charge: int | None = None


class Vocabulary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    version: str
    measurements: tuple[MeasurementRule, ...]
    substances: tuple[SubstanceDefinition, ...] = ()
    tissues: tuple[str, ...] = ()
    methods: tuple[str, ...] = ()
    routes: tuple[str, ...] = ()
    forms: tuple[str, ...] = ()
    applications: tuple[str, ...] = ()
    calculation_types: tuple[str, ...] = ()

    @classmethod
    def load(cls, path) -> Vocabulary:
        """Load and verify an offline vocabulary lock file."""
        from pkdb.cache import load_vocabulary

        return load_vocabulary(path)

    def save(self, path) -> None:
        """Write a portable, integrity-checked vocabulary lock file."""
        from pathlib import Path

        from pkdb.cache import atomic_json, vocabulary_envelope

        atomic_json(Path(path), vocabulary_envelope(self))

    @classmethod
    def bundled(cls) -> Vocabulary:
        from pkdb.cache import bundled_vocabulary

        return bundled_vocabulary()

    def measurement_map(self) -> dict[str, MeasurementRule]:
        return {rule.name: rule for rule in self.measurements}

    def substance_map(self) -> dict[str, SubstanceDefinition]:
        return {substance.name: substance for substance in self.substances}


def vocabulary_hash(vocabulary: Vocabulary) -> str:
    """Content identity shared by offline validation and the server protocol."""
    payload = json.dumps(
        vocabulary.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
