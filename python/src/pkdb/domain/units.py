"""The pint unit registry used to parse, validate and convert measurement units."""

import pint

ureg = pint.UnitRegistry()

# Units
ureg.define("cups = count")
ureg.define("beverages = count")
ureg.define("none = count")
ureg.define("percent = 0.01*count")
ureg.define("IU = [activity_amount]")
ureg.define("NO_UNIT = [no_unit]")
ureg.define("arbitrary_unit = [arbitrary_unit]")


def quantity(value: float, unit: str) -> pint.Quantity:
    """The quantity of `value` in the unit text `unit`.

    A unit text can hold a numeric factor, such as 1.73 in `l/(1.73*m^2)` (per
    1.73 m^2 body surface area) or `10^9/l`. Pint reads such a text only as an
    expression; `ureg.Unit(unit)` and `ureg.Quantity(value, unit)` refuse it
    with "Unit expression cannot have a scaling factor.".
    """
    return value * ureg.parse_expression(unit)


def convert_value(value: float, source_unit: str, target_unit: str) -> float:
    """Convert a scalar with the shared scientific registry."""
    return float(quantity(value, source_unit).to(target_unit).magnitude)
