"""Create normalized records without changing reported values or provenance."""

import math
from functools import lru_cache

import pint

from pkdb.domain.units import ureg
from pkdb.domain.vocabulary import MeasurementRule
from pkdb.schemas.study import ScientificRecord
from pkdb.schemas.validation import fail

SCALED_FIELDS = ("value", "mean", "median", "min", "max", "sd", "se")


class UnitDimensionError(ValueError):
    pass


@lru_cache(maxsize=8192)
def conversion(
    source: str, targets: tuple[str, ...], molar_mass: float | None
) -> tuple[float, str]:
    """Compile repeated unit conversions once; inputs include all vocabulary policy."""
    quantity = ureg(source)
    substance_power = quantity.dimensionality.get("[substance]", 0)
    if substance_power and molar_mass is not None:
        quantity = quantity * ureg.Quantity(molar_mass, "g/mol") ** substance_power
    by_dimension = {str(ureg(unit).dimensionality): unit for unit in targets}
    target = by_dimension.get(str(quantity.dimensionality))
    if target is None:
        raise UnitDimensionError(f"No normalized unit for {source}")
    target_quantity = ureg(target)
    if not substance_power and quantity == ureg.Quantity(1, target_quantity.units):
        return 1.0, source
    factor = float(quantity.to(target_quantity.units).magnitude)
    # Converted values use the unscaled unit; already normalized spellings stay intact.
    return factor, str(target_quantity.units)


def normalize_record[T: ScientificRecord](
    record: T, rule: MeasurementRule, *, molar_mass: float | None = None
) -> T:
    normalized = record.model_copy(deep=True)
    normalized.key = f"{record.key}:normalized"
    normalized.origin = "normalized"
    normalized.derived_from = record.key
    if not record.unit:
        return normalized
    try:
        factor, target = conversion(record.unit, rule.units, molar_mass)
    except UnitDimensionError as error:
        fail("unit_dimension", f"{error} in {rule.name}", record.source)
    except (pint.PintError, ValueError, TypeError) as error:
        fail("invalid_unit", str(error), record.source)
    for field in SCALED_FIELDS:
        value = getattr(normalized.statistics, field)
        if value is not None:
            converted = float(value * factor)
            if not math.isfinite(converted):
                fail(
                    "normalization_overflow",
                    "Normalized value is not finite",
                    record.source,
                )
            setattr(normalized.statistics, field, converted)
    normalized.unit = target
    return normalized
