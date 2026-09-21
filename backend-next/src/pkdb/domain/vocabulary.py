"""Versioned immutable reference data; loading never performs network lookups."""

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

    def measurement_map(self) -> dict[str, MeasurementRule]:
        return {rule.name: rule for rule in self.measurements}

    def substance_map(self) -> dict[str, SubstanceDefinition]:
        return {substance.name: substance for substance in self.substances}
