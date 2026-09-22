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


def convert_value(value: float, source_unit: str, target_unit: str) -> float:
    """Convert a scalar with the shared scientific registry."""
    return float(ureg.Quantity(value, source_unit).to(target_unit).magnitude)
