"""Create normalized records without changing reported values or their provenance."""

import pint

from pkdb.domain.units import ureg
from pkdb.domain.vocabulary import MeasurementRule
from pkdb.schemas.study import ScientificRecord
from pkdb.schemas.validation import fail

SCALED_FIELDS = ("value", "mean", "median", "min", "max", "sd", "se")


def normalize_record[T: ScientificRecord](
    record: T,
    rule: MeasurementRule,
    *,
    molar_mass: float | None = None,
) -> T:
    normalized = record.model_copy(deep=True)
    normalized.key = f"{record.key}:normalized"
    normalized.origin = "normalized"
    normalized.derived_from = record.key
    if not record.unit:
        return normalized
    try:
        quantity = ureg(record.unit)
        substance_power = quantity.dimensionality.get("[substance]", 0)
        if substance_power and molar_mass is not None:
            quantity = quantity * ureg.Quantity(molar_mass, "g/mol") ** substance_power
        targets = {str(ureg(unit).dimensionality): unit for unit in rule.units}
        target = targets.get(str(quantity.dimensionality))
        if target is None:
            fail(
                "unit_dimension",
                f"No normalized unit for {record.unit} in {rule.name}",
                record.source,
            )
        factor = quantity.to(target).magnitude
        for field in SCALED_FIELDS:
            value = getattr(normalized.statistics, field)
            if value is not None:
                setattr(normalized.statistics, field, float(value * factor))
        normalized.unit = target
    except (pint.PintError, ValueError, TypeError) as error:
        from pkdb.schemas.validation import StudyValidationError

        if isinstance(error, StudyValidationError):
            raise
        fail("invalid_unit", str(error), record.source)
    return normalized
