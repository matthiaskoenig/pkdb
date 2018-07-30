"""
To be easily extendable we do not hardcode information about characteristics in classes,
but define in some custom data structure which is referenced.


Model choices and more specifically possible categories of subject characteristics.

In the future the relationship between the characteristics could be implemented via
an ontology which represents the relationship between the differnent values.


units on CharacteristicType is an ordered iteratable, with the first unit being the default unit.

"""

# TODO: How to handle the genetic information? Genetic variants?

from collections import namedtuple
CharacteristicType = namedtuple("CharacteristicType", ["value", "category", "dtype", "choices", "units"])
UnitType = namedtuple("UnitType", ["name"])

# TODO: lookup units package and proper units handling (units conversion, default units, ...)
UNIT_DATA = [
    UnitType('-'),
    UnitType('cm'),
    UnitType('m'),
    UnitType('kg'),
    UnitType('yr'),
    UnitType('kg/m^2'),
    UnitType('1/day'),
    UnitType('IU/I'),
    UnitType('mg/dl'),
    UnitType('g/dl')
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
STRING_TYPE = "string"  # can be a free string, no limitations compared to categorial
YES = "Y"
NO = 'N'
BOOLEAN_CHOICES = [YES, NO]

# categories
DEMOGRAPHICS = "Demographics"  # age, sex, ethnicity
ANTHROPOMETRY = "Anthropometry"  # height, weight, waist bmi
SPECIES = "Species"
BIOCHEMICAL_DATA = "Biochemical data"
HEMATOLOGY_DATA = "Hematology data"


INCLUSION_CRITERIA = "InclusionCriteria"
EXCLUSION_CRITERIA = "ExclusionCriteria"
GROUP_CRITERIA = "GroupCriteria"
CHARACTERISTIC_VALUE_TYPES = [INCLUSION_CRITERIA, EXCLUSION_CRITERIA, GROUP_CRITERIA]
CHARACTERISTIC_VALUE_CHOICES = [(t, t) for t in CHARACTERISTIC_VALUE_TYPES]


STUDY_DESIGN_DATA = [
    "single group (interventional study)",
    "parallel group (interventional study)",
    "crossover (interventional study)",
    "cohort (oberservational study)",
    "case control (oberservational study)",
]
STUDY_DESIGN_CHOICES = [(t, t) for t in STUDY_DESIGN_DATA]


COMMON_DATA = [
    # Medication
    CharacteristicType('oral_contraceptives', 'Contraceptives', BOOLEAN_TYPE, BOOLEAN_CHOICES, ["-"]),
    CharacteristicType('oral_contraceptives_amount', 'Contraceptives', NUMERIC_TYPE, None, ["-"]),
    CharacteristicType('medication', 'Medication', CATEGORIAL_TYPE, ["ibuprofen", "paracetamol", "aspirin"], ["-"]),  # ? dosing

    # Lifestyle
    CharacteristicType('caffeine', 'Lifestyle', BOOLEAN_TYPE, BOOLEAN_CHOICES, ["-"]),
    CharacteristicType('caffeine_amount', 'Lifestyle', NUMERIC_TYPE, None, ["-"]),
]

CHARACTERISTIC_DATA = COMMON_DATA + [
    # Antropmetrical information
    CharacteristicType('species', SPECIES, CATEGORIAL_TYPE, ["Homo sapiens"], ["-"]),
    CharacteristicType('height', ANTHROPOMETRY, NUMERIC_TYPE, None, ["cm", 'm']),
    CharacteristicType('weight', ANTHROPOMETRY, NUMERIC_TYPE, None, ["kg"]),
    CharacteristicType('bmi', ANTHROPOMETRY, NUMERIC_TYPE, None, ["kg/m^2"]),
    CharacteristicType('waist_circumference', ANTHROPOMETRY, NUMERIC_TYPE, None, ["cm"]),
    CharacteristicType('liver_weight', ANTHROPOMETRY, NUMERIC_TYPE, None, ["g", "kg"]),
    CharacteristicType('kidney_weight', ANTHROPOMETRY, NUMERIC_TYPE, None, ["g", "kg"]),

    CharacteristicType('age', DEMOGRAPHICS, NUMERIC_TYPE, None, ["yr"]),
    CharacteristicType('sex', DEMOGRAPHICS, CATEGORIAL_TYPE, ["M", "F"], ["-"]),
    CharacteristicType('ethnicity', DEMOGRAPHICS, CATEGORIAL_TYPE, ["African", "Afroamerican", "Asian", "Caucasian"], ["-"]),


    # Disease (status)
    CharacteristicType('healthy', "Health status", BOOLEAN_TYPE, BOOLEAN_CHOICES, ["-"]),
    CharacteristicType('disease', "Disease", CATEGORIAL_TYPE, ["cirrhosis"], ["-"]),


    # Lifestyle
    CharacteristicType('smoking', 'Lifestyle', BOOLEAN_TYPE, BOOLEAN_CHOICES, ["-"]),
    CharacteristicType('smoking_amount', 'Lifestyle', NUMERIC_TYPE, None, ["-"]),
    CharacteristicType('alcohol', 'Lifestyle', BOOLEAN_TYPE, BOOLEAN_CHOICES, ["-"]),
    CharacteristicType('alcohol_amount', 'Lifestyle', NUMERIC_TYPE, None, ["-"]),

    # Biochemical data
    CharacteristicType('ALT', BIOCHEMICAL_DATA, NUMERIC_TYPE, None, ["IU/I"]),
    CharacteristicType('AST', BIOCHEMICAL_DATA, NUMERIC_TYPE, None, ["IU/I"]),
    CharacteristicType('Albumin', BIOCHEMICAL_DATA, NUMERIC_TYPE, None, ["g/dl"]),

    # Study protocol
    CharacteristicType('overnight_fast', 'Study protocol', BOOLEAN_TYPE, BOOLEAN_CHOICES, ["-"]),
    CharacteristicType('alcohol_abstinence', 'Study protocol', BOOLEAN_TYPE, BOOLEAN_CHOICES, ["-"]),

    # Medication

    # Genetics ???
    # Requires storage of the variants and effects of clearance
]

PK_DATA = [
]

# class, value, dtype (numeric, boolean, categorial), choices
PROTOCOL_DATA = [
    CharacteristicType('dosing', 'Dosing', NUMERIC_TYPE, None, ["-"]),
    CharacteristicType('smoking_cessation', 'Lifestyle', NUMERIC_TYPE, None, ["-"]),
    CharacteristicType('female cycle', 'Cycle', STRING_TYPE, None, ["-"]),
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




