"""
To be easily extendable we do not hardcode information about characteristics in classes,
but define in some custom data structure which is referenced.


Model choices and more specifically possible categories of subject characteristics.

In the future the relationship between the characteristics could be implemented via
an ontology which represents the relationship between the differnent values.


units on CharacteristicType is an ordered iteratable, with the first unit being the default unit.

"""
CURRENT_VERSION = [1.0]
VERSIONS = [1.0,]
#considering: to maintain serializers of serval versions of the json file. The version would be read from the json file and the respective
#serializer would be selected.

# TODO: How to handle the genetic information? Genetic variants?

from collections import namedtuple
def create_choices(list):
    return [(utype, utype) for utype in list]


CharacteristicType = namedtuple("CharacteristicType", ["value", "category", "dtype", "choices", "units"])
UnitType = namedtuple("UnitType", ["name"])

# TODO: lookup units package and proper units handling (units conversion, default units, ...)
UNIT_TIME = [
    UnitType('sec'),
    UnitType('min'),
    UnitType('h'),
    UnitType('days'),
]
TIME_UNITS_CHOICES = [(utype.name, utype.name) for utype in UNIT_TIME]


UNIT_DATA = UNIT_TIME + [
    UnitType('-'),
    UnitType('cm'),
    UnitType('m'),
    UnitType('kg'),
    UnitType('yr'),
    UnitType('week'),
    UnitType('day'),
    UnitType('kg/m^2'),
    UnitType('1/day'),
    UnitType('1/h'),
    UnitType('IU/I'),
    UnitType('mg/dl'),
    UnitType('g/dl'),
    UnitType('l/kg'),
    UnitType("ml/min/kg"),
    UnitType("µg/ml*h"),
    UnitType("Âµg/ml"),
    UnitType("µg/ml"),
    UnitType("mg"),
    UnitType("mmHg"),
    UnitType("ml/min/1.73m^2"),
    UnitType("µg/ml*h/kg"),
    UnitType("l"),
    UnitType("µmol/l*h"),
    UnitType("ml/min"),
    UnitType("mg/l*min"),
    UnitType("ml/h/kg"),
    UnitType("mg/l"),
    UnitType("mg/l*h"),
    UnitType("mg/kg"),
    UnitType("mg/day")
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
MIX = "Mixed"
NAN = "NAN"
BOOLEAN_CHOICES = [YES, NO, MIX,NAN]

INTERVENTION_ROUTE = [
    "oral",
    "iv",
]
INTERVENTION_ROUTE_CHOICES = create_choices(INTERVENTION_ROUTE)
INTERVENTION_APPLICATION = [
    "single dose",
    "multiple dose",
    "continous injection",
]
INTERVENTION_APPLICATION_CHOICES = create_choices(INTERVENTION_APPLICATION)

INTERVENTION_FORM = [
    "tablete",
    "capsule",
    "2 100mg NO-DOZ tablets",
    "capsules",
    "2 capsules",
    NAN,

]
INTERVENTION_FORM_CHOICES = create_choices(INTERVENTION_FORM)

# categories
DEMOGRAPHICS = "demographics"  # age, sex, ethnicity
ANTHROPOMETRY = "anthropometry"  # height, weight, waist bmi
SPECIES = "species"
BIOCHEMICAL_DATA = "biochemical data"
HEMATOLOGY_DATA = "hematology data"


INCLUSION_CRITERIA = "inclusion"
EXCLUSION_CRITERIA = "exclusion"
GROUP_CRITERIA = "group"
CHARACTERISTICA_TYPES = [INCLUSION_CRITERIA, EXCLUSION_CRITERIA, GROUP_CRITERIA]
CHARACTERISTICA_CHOICES = [(t, t) for t in CHARACTERISTICA_TYPES]


FileFormat = namedtuple("FileFormat", ["name", "delimiter"])

FORMAT_MAPPING = {"TSV": FileFormat("TSV",'\t'),
                  "CSV": FileFormat("CSV",",")}

STUDY_DESIGN_DATA = [
    "single group",  # (interventional study)
    "parallel group",  #  (interventional study)
    "crossover",  # (interventional study)
    "cohort",  # (oberservational study)
    "case control",  # (oberservational study)
]
STUDY_DESIGN_CHOICES = [(t, t) for t in STUDY_DESIGN_DATA]

SUBSTANCES_DATA = [
    "ibuprofen",
    "paracetamol",
    "aspirin",
    "caffeine",
    "acetaminophen",
    "paraxanthine",
    "paraxanthine/caffeine",
    "theobromine",
    "theophylline",
    "chlorozoxazone",
    "lomefloxacin",
    "AAMU",
    "1U",
    "17X",
    "17U",
    "37X",
    "1X",
    "enoxacin",
    "ciprofloxacin",
    "pipemidic acid",
    "norfloxacin",
    "ofloxacin",
    "fluvoxamine",
    "alcohol",
    "codeine"
]
SUBSTANCES_DATA_CHOICES = [(t, t) for t in SUBSTANCES_DATA]




COMMON_DATA = [
    # Medication
    CharacteristicType('oral contraceptives', 'contraceptives', BOOLEAN_TYPE, BOOLEAN_CHOICES, ["-"]),
    CharacteristicType('oral contraceptives amount', 'contraceptives', NUMERIC_TYPE, None, ["-"]),

    CharacteristicType('medication', 'medication', BOOLEAN_TYPE, BOOLEAN_CHOICES, ["-"]),
    CharacteristicType('medication type', 'medication', CATEGORIAL_TYPE, ["ibuprofen", "paracetamol", "aspirin"], ["-"]),
    CharacteristicType('medication amount', 'medication', NUMERIC_TYPE, None, ["-"]),

    # Lifestyle
    CharacteristicType('caffeine', 'lifestyle', BOOLEAN_TYPE, BOOLEAN_CHOICES, ["-"]),
    CharacteristicType('caffeine amount', 'lifestyle', NUMERIC_TYPE, None, ["mg/day"]),
]

CHARACTERISTIC_DATA = COMMON_DATA + [
    # Antropmetrical information
    CharacteristicType('species', SPECIES, CATEGORIAL_TYPE, ["homo sapiens"], ["-"]),
    CharacteristicType('height', ANTHROPOMETRY, NUMERIC_TYPE, None, ["cm", 'm']),
    CharacteristicType('weight', ANTHROPOMETRY, NUMERIC_TYPE, None, ["kg"]),
    CharacteristicType('bmi', ANTHROPOMETRY, NUMERIC_TYPE, None, ["kg/m^2"]),
    CharacteristicType('waist circumference', ANTHROPOMETRY, NUMERIC_TYPE, None, ["cm"]),
    CharacteristicType('liver weight', ANTHROPOMETRY, NUMERIC_TYPE, None, ["g", "kg"]),
    CharacteristicType('kidney weight', ANTHROPOMETRY, NUMERIC_TYPE, None, ["g", "kg"]),

    CharacteristicType('age', DEMOGRAPHICS, NUMERIC_TYPE, None, ["yr"]),
    CharacteristicType('sex', DEMOGRAPHICS, CATEGORIAL_TYPE, ["M", "F", MIX, NAN], ["-"]),
    CharacteristicType('ethnicity', DEMOGRAPHICS, CATEGORIAL_TYPE, ["african", "afroamerican", "asian", "caucasian",NAN], ["-"]),


    # Disease (status)
    CharacteristicType('healthy', "health status", BOOLEAN_TYPE, BOOLEAN_CHOICES, ["-"]),
    CharacteristicType('disease', "disease", CATEGORIAL_TYPE, [NAN, "cirrhosis", "plasmodium falciparum","alcoholic liver cirrhosis","cirrhotic liver disease","PBC","miscellaneous liver disease","schizophrenia"], ["-"]),


    CharacteristicType('blood pressure', "health status", NUMERIC_TYPE, None, ["mmHg"]),

    # ------------
    # smoking
    # ------------
    CharacteristicType('smoking', 'lifestyle', BOOLEAN_TYPE, BOOLEAN_CHOICES, ["-"]),
    CharacteristicType('smoking amount (cigarettes)', 'lifestyle', NUMERIC_TYPE, None, ["1/day"]),
    CharacteristicType('smoking amount (packyears)', 'lifestyle', NUMERIC_TYPE, None, ["yr"]),
    CharacteristicType('smoking duration (years)', 'lifestyle', NUMERIC_TYPE, None, ["yr"]),


    CharacteristicType('alcohol', 'lifestyle', BOOLEAN_TYPE, BOOLEAN_CHOICES, ["-"]),
    CharacteristicType('alcohol amount', 'lifestyle', NUMERIC_TYPE, None, ["-"]),


    # Biochemical data
    CharacteristicType('ALT', BIOCHEMICAL_DATA, NUMERIC_TYPE, None, ["IU/I"]),
    CharacteristicType('AST', BIOCHEMICAL_DATA, NUMERIC_TYPE, None, ["IU/I"]),
    CharacteristicType('albumin', BIOCHEMICAL_DATA, NUMERIC_TYPE, None, ["g/dl"]),

    # Study protocol
    CharacteristicType('overnight fast', 'study protocol', BOOLEAN_TYPE, BOOLEAN_CHOICES, ["-"]),
    CharacteristicType('alcohol abstinence', 'study protocol', BOOLEAN_TYPE, BOOLEAN_CHOICES, ["-"]),
    CharacteristicType('abstinence', 'study protocol', CATEGORIAL_TYPE, SUBSTANCES_DATA+["alcohol", "medication", "grapefruit juice"],["-"]),

    # Medication

    # Genetics ???
    CharacteristicType('genetics', 'genetics', CATEGORIAL_TYPE, ["CYP2D6 duplication","CYP2D6 wild type", "CYP2D6 poor metabolizer"], ["-"]),

    # Requires storage of the variants and effects of clearance
]
PK_DATA = [
    "auc",
    "concentration",
    "clearance",
    "vd",
    "thalf",
    "tmax",
    "cmax",
    "amount",
    "kel",
    "kabs",
    "plasma_binding",
    "clearance_unbound",
    "ratio",
    "clearance_tbc",
    "caf_px_6h",
    "auc24h",
]
OUTPUT_TISSUE_DATA = [
    "saliva",
    "plasma",
    "urine",
    "urine (24h)",
]
OUTPUT_TISSUE_DATA_CHOICES = create_choices(OUTPUT_TISSUE_DATA)
PK_DATA_CHOICES = create_choices(PK_DATA)

# class, value, dtype (numeric, boolean, categorial), choices
INTERVENTION_DATA = [
    CharacteristicType('dosing', 'dosing', NUMERIC_TYPE, None, ["mg","mg/kg"]),
    CharacteristicType('smoking cessation', 'lifestyle', NUMERIC_TYPE, None, ["-"]),
    CharacteristicType('female cycle', 'cycle', STRING_TYPE, None, ["-"]),
]

def dict_and_choices(data):
    data_dict = {item.value: item for item in data}
    data_choices = [(ctype.value, ctype.value) for ctype in data]
    return data_dict, data_choices

CHARACTERISTIC_DTYPE = {item.value : item.dtype for item in CHARACTERISTIC_DATA}
CHARACTERISTIC_CATEGORIES = set([item.value for item in CHARACTERISTIC_DATA])
CHARACTERISTIC_CATEGORIES_UNDERSCORE = set([c.replace(' ', '_') for c in CHARACTERISTIC_CATEGORIES])
CHARACTERISTIC_DICT, CHARACTERISTIC_CHOICES = dict_and_choices(CHARACTERISTIC_DATA)
INTERVENTION_DICT, INTERVENTION_CHOICES = dict_and_choices(INTERVENTION_DATA)


'''
DATA_CHOICES = (
     (1, "Other"),
     (2, "Dynamic Individual"),
     (3, "Dynamic Group"),
     (4, "Static Individual"),
     (5, "Static Group"),
     )
'''



