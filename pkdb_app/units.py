"""
Definition of units and handling of units conversion.
"""
from collections import namedtuple

UnitType = namedtuple("UnitType", ["name"])

# TODO: lookup units package and proper units handling (units conversion, default units, ...)

UNIT_TIME = [
    UnitType('yr'),
    UnitType('week'),
    UnitType('day'),
    UnitType('h'),
    UnitType('min'),
    UnitType('s'),
]
TIME_UNITS_CHOICES = [(utype.name, utype.name) for utype in UNIT_TIME]

UNIT_DATA = UNIT_TIME + [
    # base units
    UnitType('-'),
    UnitType('%'),  # dimensionless * 100
    UnitType('cm'),
    UnitType('m'),
    UnitType('kg'),
    UnitType("mg"),
    UnitType("mmHg"),
    UnitType("µmol"),

    # reverse time units
    UnitType('1/week'),
    UnitType('1/day'),
    UnitType('1/h'),
    UnitType('1/min'),
    UnitType('1/s'),

    # misc units
    UnitType("mg/kg"),
    UnitType("mg/day"),
    UnitType('kg/m^2'),
    UnitType('IU/I'),
    UnitType("l/h"),

    # concentration
    UnitType("µg/ml"),
    UnitType('mg/dl'),  # -> µg/ml
    UnitType("mg/l"),    # -> µg/ml
    UnitType("µmol/l"),  # -> µg/ml (with molar weight)
    UnitType("nmol/l"),  # -> µg/ml (with molar weight)
    UnitType('g/dl'),    # -> µg/dl
    UnitType("ng/ml"),   # -> µg/ml

    # AUC
    UnitType("mg*h/l"),
    UnitType("µg*h/ml"),   # -> mg*h/l
    UnitType("µg/ml*h"),   # -> mg*h/l
    UnitType("mg*min/l"),  # -> mg*h/l
    UnitType("µg*min/ml"),
    UnitType("µmol*h/l"),  # -> mg*h/l (with molar weight)
    UnitType("µmol/l*h"),  # -> mg*h/l (with molar weight)
    UnitType("µg/ml*h/kg"),  # -> mg*h/l/kg

    # Volume of distribution (vd)
    UnitType("l"),
    UnitType('l/kg'),
    UnitType('ml/kg'),  # -> l/kg

    # clearance
    UnitType("ml/min"),
    UnitType("ml/h"),       # -> ml/min
    UnitType("l/h/kg"),
    UnitType("ml/h/kg"),    # -> l/h/kg
    UnitType("ml/min/kg"),  # -> l/h/kg
    UnitType("ml/min/1.73m^2"),
]

UNITS_CHOICES = [(utype.name, utype.name) for utype in UNIT_DATA]


class NormalizableUnit(object):
    """ Extended unit class, which allows the normalization of the given unit.

    It provides:
    - allowed choices
    - respective normalized units
    - conversion factors for the normalization
    """
    pass
