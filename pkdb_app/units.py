"""
Definition of units and handling of units conversion.
"""
# TODO: lookup units package and proper units handling (units conversion, default units, ...)
import numpy as np

def add_names(d):
    """ If no value exists adds the key as value.
    Defines the names automatically

    :param d:
    :return:
    """
    for key in d:
        if not d[key]:
            d[key] = key


# ----------------------------------------
# Unit definitions
# ----------------------------------------
TIME_UNITS = {
    "yr": "year",
    "week": "week",
    "day": "day",
    "h": "hour",
    "min": "minute",
    "s": "second",
}
add_names(TIME_UNITS)

UNITS = {
    # base units
    "-": "dimensionless",
    "%": "percent",
    "mega": None,
    "kilo": None,
     "milli": None,
     "micro": None,
    "cm": "centimeter",
    "m": "meter",
    "kg": "kilogram",
    "mg": "milligram",
    "g": "gram",
    "mmHg": None,
    "mmol": None,
    "µmol": None,
    "nmol": None,
    "m^2": None,

    # reverse time units
    "1/week": None,
    "1/day": None,
    "1/h": None,
    "1/min": None,
    "1/s": None,
    # misc units
    "g/kg": None,
    "mg/kg": None,
    "pmol/kg": None,
    "mg/70kg": None,
    "mU/kg": None,
    "U/kg": None,
    "mg/day": None,
    "kg/m^2": None,
    "IU/I": None,


    # concentration
    "µg/l": None,
    "µg/ml": None,
    "µg/dl": None,
    "mg/dl": None,
    "mg/100ml": None,
    "mg/l": None,
    "ng/l": None,
    "g/dl": None,
    "ng/ml": None,
    "pg/ml": None,
    "mmol/l": None,
    "nmol/ml": None,
    "µmol/l": None,
    "nmol/l": None,
    "pmol/l": None,
    "pmol/ml": None,
    "fmol/l": None,
    "µU/ml": None,
    "ng/g": None,  # per g plasma

    # AUC
    "h*mg/l":None,
    "h*µg/l": None,
    "h*µg/ml": None,
    "mg*h/l": None,
    "mg/l*h": None,

    "ng*h/ml": None,
    "ng*min/ml": None,
    "µg*h/ml": None,  # -> mg*h/l

    "µg/ml*h": None,  # -> mg*h/l
    "mg*min/l": None,  # -> mg*h/l
    "mg/l*min": None,  # -> mg*h/l
    "µg*min/ml": None,
    "µmol*h/l": None,  # -> mg*h/l (with molar weight)
    "µmol/l*h": None,  # -> mg*h/l (with molar weight)
    "pmol*h/ml": None,
    "pmol/ml*h": None,
    "h*pmol/ml": None,
    "nmol*h/l": None,
    "nmol/l*h":None,
    "µg/ml*h/kg": None,  # -> mg*h/l/kg
    "mg*h/l/kg": None,

    "µU/ml*min": None,

    #AUMC
    # AUC
    "mg*h^2/l": None,
    "mg/l*h^2": None,
    "ng*h^2/ml": None,
    "ng*min^2/ml": None,
    "µg*h^2/ml": None,  # -> mg*h/l
    "µg/ml*h^2": None,  # -> mg*h/l
    "mg*min^2/l": None,  # -> mg*h/l
    "mg/l*min^2": None,  # -> mg*h/l
    "µg*min^2/ml": None,
    "µmol*h^2/l": None,  # -> mg*h/l (with molar weight)
    "µmol/l*h^2": None,  # -> mg*h/l (with molar weight)
    "pmol*h^2/ml": None,
    "pmol/ml*h^2": None,
    "nmol*h^2/l": None,
    "µg/ml*h^2/kg": None,  # -> mg*h/l/kg
    "mg*h^2/l/kg": None,
    "µU/ml*min^2": None,


    # Volume of distribution (vd)
    "l": None,
    "ml": None,
    "l/kg": None,
    "ml/kg": None,  # -> l/kg

    # clearance
    "ml/min": None,
    "ml/h": None,  # -> ml/min
    "l/h": None,
    "l/h/kg": None,
    "l/h*kg": None,
    "ml/h/kg": None,  # -> l/h/kg
    "ml/kg/min": None,
    "ml/min/kg": None,  # -> l/h/kg
    "ml/min/1.73m^2": None,

    # rate
    "mg/min": None,
    "mg/kg/min": None,
    "mg/min/kg": None,
    "µmol/min": None,
    "µmol/kg/min": None,
    "µmol/min/kg": None,  # -> µmol/kg/min
    "pmol/min": None,
    "pmol/kg/min": None,
    "pmol/min/kg": None,
    "mU/min": None,
    "mU/min/kg": None,
    "mU/kg/min": None,

    # misc
    "cups/day": None,
    "g/day": None,

}
UNITS.update(TIME_UNITS)
add_names(UNITS)


# ----------------------------------------
# Choices
# ----------------------------------------
UNITS_CHOICES = [(key, key) for key in UNITS]
TIME_UNITS_CHOICES = [(key, key) for key in TIME_UNITS]


# ----------------------------------------
# Conversions
# ----------------------------------------
class UnitConversion(object):
    """ Defines conversion between two units with conversion factor.
        Some conversions require molecular weights

        Multiplier is applied as
            target = source * multiplier

    """

    def __init__(self, source, target, multiplier):
        self.source = source
        self.target = target
        self.multiplier = multiplier

    def apply_conversion(self, value):
        """ Apply the unit conversion to a given unit. """
        return np.multiply(value, self.multiplier)


# Supported unit conversions
UNIT_CONVERSIONS = [
    #Time
    UnitConversion("kg", target="g", multiplier=1000.0),
    UnitConversion("g", target="kg", multiplier=1/1000.0),

    UnitConversion("cm", target="m", multiplier=1E-2),
    UnitConversion("ml", target="l", multiplier=1E-3),
    UnitConversion("min", target="h", multiplier=1.0 / 60),
    UnitConversion("1/min", target="1/h", multiplier=60.0),
    # Concentrations
    UnitConversion("mg/dl", target="µg/ml", multiplier=10),
    UnitConversion("µg/l", target="µg/ml", multiplier=0.001),
    UnitConversion("µg/dl", target="µg/ml", multiplier=0.01),

    UnitConversion("mg/l", target="µg/ml", multiplier=1.0),
    UnitConversion("g/dl", target="µg/ml", multiplier=10000.0),
    UnitConversion("ng/ml", target="µg/ml", multiplier=1.0E-3),
    UnitConversion("ng/l", target="µg/ml", multiplier=1.0),

    # AUC
    UnitConversion("h*mg/l", target="mg*h/l", multiplier=1.0),

    UnitConversion("h*µg/ml", target="mg*h/l", multiplier=1.0),

    UnitConversion("µg*h/ml", target="mg*h/l", multiplier=1.0),

    UnitConversion("mg/l*h", target="mg*h/l", multiplier=1.0),

    UnitConversion("µg*min/ml", target="mg*h/l", multiplier=1.0/60),
    UnitConversion("ng*min/ml", target="mg*h/l", multiplier=1.0 /(60*1000.0)),
    UnitConversion("ng*h/ml", target="mg*h/l", multiplier=1000.0),
    UnitConversion("µg/ml*h", target="mg*h/l", multiplier=1.0),

    UnitConversion("h*µg/l", target="mg*h/l", multiplier=1.0E-3),
    UnitConversion("µg*h/l", target="mg*h/l", multiplier=1.0E-3),

    UnitConversion("mg*min/l", target="mg*h/l", multiplier=1.0/60),
    UnitConversion("mg/l*min", target="mg*h/l", multiplier=1.0/60),
    UnitConversion("µg/ml*h/kg", target="mg*h/l/kg", multiplier=1.0),

    UnitConversion("µmol/l*h", target="µmol*h/l", multiplier=1.0),
    UnitConversion("nmol/l*h", target="µmol*h/l", multiplier=1.0E-3),
    UnitConversion("nmol*h/l", target="µmol*h/l", multiplier=1.0E-3),

    # AUMC
    UnitConversion("µg*h^2/ml", target="mg*h^2/l", multiplier=1.0),
    UnitConversion("mg/l*h^2", target="mg*h^2/l", multiplier=1.0),

    UnitConversion("µg*min^2/ml", target="mg*h^2/l", multiplier=1.0/(60**2)),
    UnitConversion("ng*min^2/ml", target="mg*h^2/l", multiplier=1.0 /((60**2)*1000.0)),
    UnitConversion("ng*h^2/ml", target="mg*h^2/l", multiplier=1000.0),
    UnitConversion("µg/ml*h^2", target="mg*h^2/l", multiplier=1.0),
    UnitConversion("mg*min^2/l", target="mg*h^2/l", multiplier=1.0/(60**2)),
    UnitConversion("mg/l*min^2", target="mg*h^2/l", multiplier=1.0/(60**2)),
    UnitConversion("µg/ml*h^2/kg", target="mg*h^2/l/kg", multiplier=1.0),

    UnitConversion("µmol/l*h^2", target="µmol*h^2/l", multiplier=1.0),
    UnitConversion("nmol/l*h^2", target="µmol*h^2/l", multiplier=1.0E-3),
    UnitConversion("nmol*h^2/l", target="µmol*h^2/l", multiplier=1.0E-3),


    # Vd
    UnitConversion("ml/kg", target="l/kg", multiplier=1.0E-3),

    # clearance
    UnitConversion("ml/h/kg", target="l/h/kg", multiplier=1.0E-3),
    UnitConversion("l/h*kg", target="l/h/kg", multiplier=1.0E-3),
    UnitConversion("ml/kg/h", target="l/h/kg", multiplier=1.0E-3),
    UnitConversion("ml/min/kg", target="l/h/kg", multiplier=1.0E-3 * 60),
    UnitConversion("ml/kg/min", target="l/h/kg", multiplier=1.0E-3 * 60),
    UnitConversion("ml/min", target="l/h", multiplier=1.0E-3 * 60),
    UnitConversion("ml/h", target="l/h", multiplier=1.0E-3),

    # ratio
    UnitConversion("%", target="-", multiplier=1.0 / 100.0),
    # "µmol/l": None,  # -> µg/ml (with molar weight)
    # "nmol/l": None,  # -> µg/ml (with molar weight)
    # "µmol*h/l": None,  # -> mg*h/l (with molar weight)
    # "µmol/l*h": None,  # -> mg*h/l (with molar weight)

    # rate
    UnitConversion("µmol/min/kg", target="µmol/kg/min", multiplier=1.0),

    # misc
    UnitConversion("mg/70kg", target="mg/kg", multiplier=70.0),

]
UNIT_CONVERSIONS_DICT = {
    f"[{item.source}] -> [{item.target}]": item for item in UNIT_CONVERSIONS
}


class NormalizableUnit(dict):
    """ Extended unit class, which allows the normalization of the given unit.

    It provides:
    - allowed choices
    - respective normalized units
    in the form
    { allowed_unit: normalized_unit, ... , allowed_unit: normalized_unit=None }
    If normalized_unit=None, the unit is already normalized.

    The actual conversions can be performed using the UnitConversions.
    """

    def __init__(self, from_to_dict):
        super().__init__(from_to_dict)
        if not isinstance(from_to_dict, dict):
            raise ValueError(
                f"NormalizableUnit requires <dict>, not {type(from_to_dict)}: {from_to_dict}"
            )

        self.validate()

    def validate(self):
        """ Checks that the normalizable unit definition is correct.

        :return:
        """
        for source, target in self.items():
            # check that in allowed units
            if source not in UNITS:
                raise ValueError(f"source unit <{source}> not in UNITS: {self}")

            # check that conversion is supported
            if target is not None:
                if target not in UNITS:
                    raise ValueError(f"target unit <{target}> not in UNITS: {self}")

                # check that unit conversion is defined
                conversion_key = f"[{source}] -> [{target}]"
                conversion = UNIT_CONVERSIONS_DICT.get(conversion_key)
                if not conversion:
                    raise ValueError(
                        f"conversion <{conversion_key}> is not defined: {self}"
                    )

    def is_valid_unit(self, unit):
        # is the unit in the keys
        return unit in self

    def valid_units(self):
        return self.keys()
