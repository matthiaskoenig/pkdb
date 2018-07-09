"""
To be easily extendable we do not hardcode information about characteristics in classes,
but define in some custom data structure which is referenced.


Model choices and more specifically possible categories of subject characteristics.

In the future the relationship between the characteristics could be implemented via
an ontology which represents the relationship between the differnent values.
"""

# TODO: How to handle the genetic information? Genetic variants?

from collections import namedtuple
CharacteristicType = namedtuple("CharacteristicType", ["value", "category", "dtype", "choices"])
UnitType = namedtuple("UnitType", ["name"])

# TODO: lookup units package and proper units handling (units conversion, default units, ...)
UNIT_DATA = [
    UnitType('-'),
    UnitType('cm'), UnitType('m'),
    UnitType('kg'),
    UnitType('yr'),
    UnitType('kg/m^2'),
    UnitType('1/day'),
]
UNITS_CHOICES = [(utype.name, utype.name) for utype in UNIT_DATA]


# class, value, dtype (numeric, boolean, categorial), choices
# dates?
# How to store NA? Is this necessary?
#   numeric: NA, None
#   boolean: NA, None
#   categorial: NA, None

BOOLEAN_TYPE = 'boolean'
NUMERIC_TYPE = 'numeric'
CATEGORIAL_TYPE = 'categorial'
YES = "Y"
NO = 'N'
BOOLEAN_CHOICES = [YES, NO]


COMMON_DATA = [
    # Medication
    CharacteristicType('oral_contraceptives', 'Contraceptives', BOOLEAN_TYPE, BOOLEAN_CHOICES),
    CharacteristicType('oral_contraceptives_amount', 'Contraceptives', NUMERIC_TYPE, None),
    CharacteristicType('medication', 'Medication', CATEGORIAL_TYPE, ["ibuprofen", "paracetamol", "aspirin"]),  # ? dosing

    # Lifestyle
    CharacteristicType('caffeine', 'Lifestyle', BOOLEAN_TYPE, BOOLEAN_CHOICES),
    CharacteristicType('caffeine_amount', 'Lifestyle', NUMERIC_TYPE, None),
]

CHARACTERISTIC_DATA = COMMON_DATA+ [
    # Antropmetrical information
    CharacteristicType('species', 'Species', CATEGORIAL_TYPE, ["Homo sapiens"]),
    CharacteristicType('height', 'BodyParameter', NUMERIC_TYPE, None),
    CharacteristicType('body_weight', 'BodyParameter', NUMERIC_TYPE, None),
    CharacteristicType('age', 'BodyParameter', NUMERIC_TYPE, None),
    CharacteristicType('sex', 'BodyParameter', CATEGORIAL_TYPE, ["M", "F"]),
    CharacteristicType('bmi', 'BodyParameter', NUMERIC_TYPE, None),
    CharacteristicType('waist_circumference', 'BodyParameter', NUMERIC_TYPE, None),
    CharacteristicType('ethnicity', 'Ethnicity', CATEGORIAL_TYPE, ["african", "afroamerican", "asian", "caucasian"]),

    # Disease (status)
    CharacteristicType('healthy', "Health status", BOOLEAN_TYPE, BOOLEAN_CHOICES),
    CharacteristicType('disease', "Disease", CATEGORIAL_TYPE, ["cirrhosis"]),


    # Lifestyle
    CharacteristicType('smoking', 'Lifestyle', BOOLEAN_TYPE, BOOLEAN_CHOICES),
    CharacteristicType('smoking_amount', 'Lifestyle', NUMERIC_TYPE, None),
    CharacteristicType('alcohol', 'Lifestyle', BOOLEAN_TYPE, BOOLEAN_CHOICES),
    CharacteristicType('alcohol_amount', 'Lifestyle', NUMERIC_TYPE, None),


    # Study protocol
    CharacteristicType('overnight_fast', 'Study protocol', BOOLEAN_TYPE, BOOLEAN_CHOICES),
    CharacteristicType('alcohol_abstinence', 'Study protocol', BOOLEAN_TYPE, BOOLEAN_CHOICES),

    # Medication

    # Genetics ???
    # Requires storage of the variants and effects of clearance
]

PK_DATA = [
]

# class, value, dtype (numeric, boolean, categorial), choices
PROTOCOL_DATA = [

    CharacteristicType('dosing', 'Dosing', NUMERIC_TYPE, None),



]

def dict_and_choices(data):
    data_dict = {item.value: item for item in data}
    data_choices = [(ctype.value, ctype.value) for ctype in data]
    return data_dict, data_choices

CHARACTERISTIC_DTYPE = {item.value : item.dtype for item in CHARACTERISTIC_DATA}
CHARACTERISTIC_CATEGORIES = set([item.value for item in CHARACTERISTIC_DATA])
CHARACTERISTIC_DICT, CHARACTERISTIC_CHOICES = dict_and_choices(CHARACTERISTIC_DATA)
PROTOCOL_DICT, PROTOCOL_CHOICES = dict_and_choices(PROTOCOL_DATA)


'''
DATA_CHOICES = (
     (1, "Other"),
     (2, "Dynamic Individual"),
     (3, "Dynamic Group"),
     (4, "Static Single"),
     (5, "Static Multiple"),
     )
'''

'''
class Dosing:
    substance
    route
    form
    dose
    dose_unit
    dose_bodyweight
    times

class Pharmacokinetics (CharacteristicValue):
    group (intervention)
    dosing
    substance
    source
    entry
'''




