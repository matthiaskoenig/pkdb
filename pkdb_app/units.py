"""
Definition of units and handling of units conversion.
"""
from collections import namedtuple


# TODO: lookup units package and proper units handling (units conversion, default units, ...)

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
    'yr': 'year',
    'week': 'week',
    'day': 'day',
    'h': 'hour',
    'min': 'minute',
    's': 'second',
}
add_names(TIME_UNITS)

UNITS = {
    # base units
    '-': 'dimensionless',
    '%': 'percent',
    'cm': 'centimeter',
    'm': 'meter',
    'kg': 'kilogram',
    "mg": 'milligram',
    "mmHg": None,
    "µmol": None,

    # reverse time units
    '1/week': None,
    '1/day': None,
    '1/h': None,
    '1/min': None,
    '1/s': None,

    # misc units
    "mg/kg": None,
    "mg/day": None,
    'kg/m^2': None,
    'IU/I': None,
    "l/h": None,

    # concentration
    "µg/ml": None,
    'mg/dl': None,
    "mg/l": None,
    "µmol/l": None,
    "nmol/l": None,
    'g/dl': None,
    "ng/ml": None,

    # AUC
    "mg*h/l": None,
    "µg*h/ml": None,   # -> mg*h/l
    "µg/ml*h": None,   # -> mg*h/l
    "mg*min/l": None,  # -> mg*h/l
    "µg*min/ml": None,
    "µmol*h/l": None,  # -> mg*h/l (with molar weight)
    "µmol/l*h": None,  # -> mg*h/l (with molar weight)
    "µg/ml*h/kg": None,  # -> mg*h/l/kg

    # Volume of distribution (vd)
    "l": None,
    'l/kg': None,
    'ml/kg': None,  # -> l/kg

    # clearance
    "ml/min": None,
    "ml/h": None,       # -> ml/min
    "l/h/kg": None,
    "ml/h/kg": None,    # -> l/h/kg
    "ml/min/kg": None,  # -> l/h/kg
    "ml/min/1.73m^2": None,

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
    """
    def __init__(self, source, target, multiplier):
        self.source = source
        self.target = target
        self.multiplier = multiplier


UNIT_CONVERSIONS = [
    # Concentrations
    UnitConversion('mg/dl', target='µg/ml', multiplier="?"),
    UnitConversion('mg/l', target='µg/ml', multiplier=1.0),
    UnitConversion('g/dl', target='µg/dl', multiplier=1.0E6),
    UnitConversion('ng/ml', target='µg/ml', multiplier=1.0E-3),
    # AUC
    UnitConversion('µg*h/ml', target='mg*h/l', multiplier=1.0E-3),
    UnitConversion('µg/ml*h', target='mg*h/l', multiplier=1.0E-3),
    UnitConversion('mg*min/l', target='mg*h/l', multiplier=60),
    UnitConversion('µg/ml*h/kg', target='mg*h/l/kg', multiplier=1.0E-3),

    # Vd
    UnitConversion('ml/kg', target='l/kg', multiplier=1.0E-3),

    # clearance
    UnitConversion('ml/h/kg', target='l/h/kg', multiplier=1.0E-3),
    UnitConversion('ml/kg/h', target='l/h/kg', multiplier=1.0E-3),
    UnitConversion('ml/h/kg', target='l/h/kg', multiplier=1.0E-3),
    UnitConversion('ml/min/kg', target='l/h/kg', multiplier=1.0E-3/60),
    UnitConversion('ml/kg/min', target='l/h/kg', multiplier=1.0E-3/60),
    UnitConversion('ml/min', target='ml/h', multiplier=1.0/60),

    # "µmol/l": None,  # -> µg/ml (with molar weight)
    # "nmol/l": None,  # -> µg/ml (with molar weight)
    # "µmol*h/l": None,  # -> mg*h/l (with molar weight)
    # "µmol/l*h": None,  # -> mg*h/l (with molar weight)
]
UNIT_CONVERSIONS_DICT = {f'{item.source}->{item.target}': item for item in UNIT_CONVERSIONS}


class NormalizableUnit(object):
    """ Extended unit class, which allows the normalization of the given unit.

    It provides:
    - allowed choices
    - respective normalized units
    - conversion factors for the normalization
    """
    def __init__(self, from_to_dict):
        self.from_to_dict = from_to_dict
        self.validate()

    def validate(self):
        """ Checks that the normalizable unit definition is correct.

        :return:
        """
        for source, target in self.from_to_dict.items():
            # check that in allowed units
            if source not in UNITS:
                raise ValueError(f'source unit <{source}> not in UNITS: {self.from_to_dict}')

            if (target is not None) and (target not in UNITS):
                raise ValueError(f'target unit <{target}> not in UNITS: {self.from_to_dict}')

            # check that unit conversion is defined
            conversion = UNIT_CONVERSIONS_DICT.get(f'{source}->{target}: {self.from_to_dict}')
            if not conversion:
                raise ValueError(f'conversion <[{source}] -> [{target}]> is not defined: {self.from_to_dict}')


