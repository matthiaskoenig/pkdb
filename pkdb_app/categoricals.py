"""
To be easily extendable we do not hardcode information about characteristics in classes,
but define in some custom data structure which is referenced.


Model choices and more specifically possible categories of subject characteristics.

In the future the relationship between the characteristics could be implemented via
an ontology which represents the relationship between the differnent values.
"""

# TODO: How to handle the genetic information? Genetic variants?

from collections import namedtuple
CharacteristicType = namedtuple("CharacteristicType", ["value", "class", "dtype", "choices"])
UnitType = namedtuple("UnitType", ["name"])

# TODO: lookup units package and proper units handling (units conversion, default units, ...)
UNIT_DATA = [
    UnitType('-'),
    UnitType('cm'), UnitType('m'),
    UnitType('kg'),
    UnitType('y'),
    UnitType('kg/m^2'),
]
UNITS_CHOICES = [(utype.name, utype.name) for utype in UNIT_DATA]



# class, value, dtype (numeric, boolean, categorial), choices
# dates?
# How to store NA? Is this necessary?
#   numeric: NA, None
#   boolean: NA, None
#   categorial: NA, None

CHARACTERISTIC_DATA = [
    CharacteristicType('height', 'BodyParameter', 'numeric', None),
    CharacteristicType('body weight', 'BodyParameter', 'numeric', None),
    CharacteristicType('age', 'BodyParameter', 'numeric', None),
    CharacteristicType('sex', 'BodyParameter', 'categorial', ["M", "F"]),
    CharacteristicType('bmi', 'BodyParameter', 'numeric', None),
    CharacteristicType('waist circumference', 'BodyParameter', 'numeric', None),

    CharacteristicType('ethnicity', 'Ethnicity', 'categorial', ["african", "afroamerican", "asian", "caucasian"]),

    # exists as yes/no or as amount
    CharacteristicType('healthy', "Health status", "boolean", None),
    CharacteristicType('disease', "Disease", "categorial", ["cirrhosis"]),

    CharacteristicType('smoking', 'Lifestyle', 'boolean', ["Y", "N"]),
    CharacteristicType('smoking_amount', 'Lifestyle', 'numeric', None),
    CharacteristicType('alcohol', 'Lifestyle', 'boolean', ["Y", "N"]),
    CharacteristicType('alcohol_amount', 'Lifestyle', 'numeric', None),

    CharacteristicType('oral contraceptives', 'Contraceptives', 'boolean', ["Y", "N"]),

    CharacteristicType('medication', 'Medication', 'categorial', ["ibuprofen", "paracetamol", "aspirin"]),  # ? dosing
    CharacteristicType('species', 'Species', 'categorial', ["Homo sapiens"]),
]

CHARACTERISTIC_DICT = {item.value: item for item in CHARACTERISTIC_DATA}
CHARACTERISTIC_CHOICES = [(ctype.value, ctype.value) for ctype in CHARACTERISTIC_DATA]


'''
DATA_CHOICES = (
     (1, "Other"),
     (2, "Dynamic Individual"),
     (3, "Dynamic Group"),
     (4, "Static Single"),
     (5, "Static Multiple"),
     )
'''
