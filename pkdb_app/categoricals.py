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

COMMON_DATA = [
    # Medication
    CharacteristicType('oral contraceptives', 'Contraceptives', 'boolean', ["Y", "N"]),
    CharacteristicType('medication', 'Medication', 'categorial', ["ibuprofen", "paracetamol", "aspirin"]),  # ? dosing

    # Lifestyle
    CharacteristicType('caffeine', 'Lifestyle', 'boolean', ["Y", "N"]),
    CharacteristicType('caffeine_amount', 'Lifestyle', 'numeric', None),
]

CHARACTERISTIC_DATA = COMMON_DATA+ [
    # Antropmetrical information
    CharacteristicType('species', 'Species', 'categorial', ["Homo sapiens"]),
    CharacteristicType('height', 'BodyParameter', 'numeric', None),
    CharacteristicType('body weight', 'BodyParameter', 'numeric', None),
    CharacteristicType('age', 'BodyParameter', 'numeric', None),
    CharacteristicType('sex', 'BodyParameter', 'categorial', ["M", "F"]),
    CharacteristicType('bmi', 'BodyParameter', 'numeric', None),
    CharacteristicType('waist circumference', 'BodyParameter', 'numeric', None),
    CharacteristicType('ethnicity', 'Ethnicity', 'categorial', ["african", "afroamerican", "asian", "caucasian"]),

    # Disease (status)
    CharacteristicType('healthy', "Health status", "boolean", None),
    CharacteristicType('disease', "Disease", "categorial", ["cirrhosis"]),


    # Lifestyle
    CharacteristicType('smoking', 'Lifestyle', 'boolean', ["Y", "N"]),
    CharacteristicType('smoking_amount', 'Lifestyle', 'numeric', None),
    CharacteristicType('alcohol', 'Lifestyle', 'boolean', ["Y", "N"]),
    CharacteristicType('alcohol_amount', 'Lifestyle', 'numeric', None),


    # Study protocol
    CharacteristicType('overnight fast', 'Study protocol', 'boolean', ["Y", "N"]),
    CharacteristicType('alcohol_abstinence', 'Study protocol', 'boolean', ["Y", "N"]),

    # Medication

    # Genetics ???
    # Requires storage of the variants and effects of clearance
]

PK_DATA = [
]

# class, value, dtype (numeric, boolean, categorial), choices
INTERVENTION_DATA = COMMON_DATA + [
]

def dict_and_choices(data):
    data_dict = {item.value: item for item in data}
    data_choices = [(ctype.value, ctype.value) for ctype in data]
    return data_dict, data_choices

CHARACTERISTIC_CATEGORIES = set([item.value for item in CHARACTERISTIC_DATA])
CHARACTERISTIC_DICT, CHARACTERISTIC_CHOICES = dict_and_choices(CHARACTERISTIC_DATA)
INTERVENTION_DICT, INTERVENTION_CHOICES = dict_and_choices(INTERVENTION_DATA)


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




