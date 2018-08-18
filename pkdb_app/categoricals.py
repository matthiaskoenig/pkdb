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
    UnitType('yr'),
    UnitType('week'),
    UnitType('day'),
    UnitType('h'),
    UnitType('min'),
    UnitType('s'),
]
TIME_UNITS_CHOICES = [(utype.name, utype.name) for utype in UNIT_TIME]

UNIT_DATA = UNIT_TIME + [
    UnitType('-'),
    UnitType('cm'),
    UnitType('m'),
    UnitType('kg'),

    UnitType('1/week'),
    UnitType('1/day'),
    UnitType('1/h'),
    UnitType('1/min'),
    UnitType('1/s'),

    UnitType('kg/m^2'),


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
    UnitType("mg*h/l"),
    UnitType("l/h"),
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
NAN = "NaN"
BOOLEAN_CHOICES = [YES, NO, MIX,NAN]

INTERVENTION_ROUTE = [
    "oral",
    "iv",
]
INTERVENTION_ROUTE_CHOICES = create_choices(INTERVENTION_ROUTE)
INTERVENTION_APPLICATION = [
    "single dose",
    "multiple dose",
    "continuous injection",
]
INTERVENTION_APPLICATION_CHOICES = create_choices(INTERVENTION_APPLICATION)

INTERVENTION_FORM = [
    "tablete",
    "capsule",
    "solution",
    NAN,
]
INTERVENTION_FORM_CHOICES = create_choices(INTERVENTION_FORM)

# categories
SPECIES = "species"
DEMOGRAPHICS = "demographics"
ANTHROPOMETRY = "anthropometry"
PHYSIOLOGY = "physiology"
PATIENT_STATUS = "patient status"
MEDICATION = "medication"
LIFESTYLE = "lifestyle"
BIOCHEMICAL_DATA = "biochemical data"
HEMATOLOGY_DATA = "hematology data"
GENETIC_VARIANTS = "genetic variants"


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
    # acetaminophen
    "acetaminophen",

    # caffeine
    "caffeine",
    "paraxanthine",
    "theobromine",
    "theophylline",
    "AAMU",
    "1U",
    "17X",
    "17U",
    "37X",
    "1X",
    "methylxanthine",
    "paraxanthine/caffeine",
    "caffeine/paraxanthine",
    "theobromine/caffeine",
    "theophylline/caffeine",
    "1X/caffeine",
    "1X/paraxanthine",
    "1X/theophylline",

    # quinolones
    "quinolone",
    "pipemidic acid",
    "norfloxacin",
    "enoxacin",
    "ciprofloxacin",
    "ofloxacin",

    # oral contraceptives
    "levonorgestrel",
    "gestodene",
    "EE2",

    # codeine
    "codeine",

    # misc
    "tizanidine",

    "ibuprofen",
    "aspirin",
    "enoxacin",
    "ciprofloxacin",
    "pipemidic acid",
    "norfloxacin",
    "ofloxacin",
    "fluvoxamine",
    "ethanol",
    "chlorozoxazone",
    "lomefloxacin",]
SUBSTANCES_DATA_CHOICES = [(t, t) for t in SUBSTANCES_DATA]


CHARACTERISTIC_DATA = [
    # -------------- Species --------------
    CharacteristicType('species', SPECIES, CATEGORIAL_TYPE, ["homo sapiens"], ["-"]),

    # -------------- Anthropometry --------------
    CharacteristicType('height', ANTHROPOMETRY, NUMERIC_TYPE, None, ["cm", 'm']),
    CharacteristicType('weight', ANTHROPOMETRY, NUMERIC_TYPE, None, ["kg"]),
    CharacteristicType('bmi', ANTHROPOMETRY, NUMERIC_TYPE, None, ["kg/m^2"]),
    CharacteristicType('waist circumference', ANTHROPOMETRY, NUMERIC_TYPE, None, ["cm"]),

    # -------------- Demography --------------
    CharacteristicType('age', DEMOGRAPHICS, NUMERIC_TYPE, None, ["yr"]),
    CharacteristicType('sex', DEMOGRAPHICS, CATEGORIAL_TYPE, ["M", "F", MIX, NAN], ["-"]),
    CharacteristicType('ethnicity', DEMOGRAPHICS, CATEGORIAL_TYPE, ["african", "afroamerican", "asian", "caucasian", NAN], ["-"]),

    # -------------- Physiology --------------
    CharacteristicType('blood pressure', PHYSIOLOGY, NUMERIC_TYPE, None, ["mmHg"]),
    CharacteristicType('heart rate', PHYSIOLOGY, NUMERIC_TYPE, None, ["1/s"]),

    # -------------- Organ weights --------------
    CharacteristicType('liver weight', ANTHROPOMETRY, NUMERIC_TYPE, None, ["g", "kg"]),
    CharacteristicType('kidney weight', ANTHROPOMETRY, NUMERIC_TYPE, None, ["g", "kg"]),

    # -------------- Patient status --------------
    CharacteristicType('overnight fast', PATIENT_STATUS, BOOLEAN_TYPE, BOOLEAN_CHOICES, ["-"]),
    CharacteristicType('fasted', PATIENT_STATUS, NUMERIC_TYPE, None, ["h"]),
    CharacteristicType('healthy', PATIENT_STATUS, BOOLEAN_TYPE, BOOLEAN_CHOICES, ["-"]),
    CharacteristicType('disease', PATIENT_STATUS, CATEGORIAL_TYPE, [NAN, "cirrhosis", "plasmodium falciparum",
                                                               "alcoholic liver cirrhosis", "cirrhotic liver disease", "PBC",
                                                               "miscellaneous liver disease", "schizophrenia"], ["-"]),

    # -------------- Medication --------------
    CharacteristicType('medication', MEDICATION, BOOLEAN_TYPE, BOOLEAN_CHOICES, ["-"]),
    CharacteristicType('medication type', MEDICATION, CATEGORIAL_TYPE, ["ibuprofen", "paracetamol", "aspirin"], ["-"]),
    CharacteristicType('medication amount', MEDICATION, NUMERIC_TYPE, None, ["-"]),

    CharacteristicType('oral contraceptives', MEDICATION, BOOLEAN_TYPE, BOOLEAN_CHOICES, ["-"]),
    # CharacteristicType('oral contraceptives amount', MEDICATION, NUMERIC_TYPE, None, ["-"]),

    CharacteristicType('abstinence', 'study protocol', CATEGORIAL_TYPE, SUBSTANCES_DATA+["alcohol", "grapefruit juice"],
                       ["year", "week", "day"]),

    # -------------- Caffeine --------------
    CharacteristicType('caffeine', 'lifestyle', BOOLEAN_TYPE, BOOLEAN_CHOICES, ["-"]),
    CharacteristicType('caffeine amount', 'lifestyle', NUMERIC_TYPE, None, ["mg/day"]),

    # -------------- Smoking --------------
    CharacteristicType('smoking', 'lifestyle', BOOLEAN_TYPE, BOOLEAN_CHOICES, ["-"]),
    CharacteristicType('smoking amount (cigarettes)', 'lifestyle', NUMERIC_TYPE, None, ["1/day"]),
    CharacteristicType('smoking amount (packyears)', 'lifestyle', NUMERIC_TYPE, None, ["yr"]),
    CharacteristicType('smoking duration (years)', 'lifestyle', NUMERIC_TYPE, None, ["yr"]),

    # -------------- Alcohol --------------
    CharacteristicType('alcohol', 'lifestyle', BOOLEAN_TYPE, BOOLEAN_CHOICES, ["-"]),
    CharacteristicType('alcohol amount', 'lifestyle', NUMERIC_TYPE, None, ["-"]),
    CharacteristicType('alcohol abstinence', 'study protocol', BOOLEAN_TYPE, BOOLEAN_CHOICES, ["-"]),

    # -------------- Biochemical data --------------
    CharacteristicType('ALT', BIOCHEMICAL_DATA, NUMERIC_TYPE, None, ["IU/I"]),
    CharacteristicType('AST', BIOCHEMICAL_DATA, NUMERIC_TYPE, None, ["IU/I"]),
    CharacteristicType('albumin', BIOCHEMICAL_DATA, NUMERIC_TYPE, None, ["g/dl"]),


    # --------------Genetic variants --------------
    CharacteristicType('genetics', GENETIC_VARIANTS, CATEGORIAL_TYPE, ["CYP2D6 duplication","CYP2D6 wild type", "CYP2D6 poor metabolizer"], ["-"]),

]

PK_DATA = [
    "auc_inf",  # Area under the curve, extrapolated until infinity
    "auc_end",  # Area under the curve, until end time point (time has to be given as time attribute)

    "amount",
    "concentration",
    "ratio",

    "clearance",
    "clearance_renal",
    "vd",  # Volume of distribution
    "thalf",  # halflife
    "tmax",  # time of maximum
    "cmax",  # maximum concentration

    "kel",  # elimination rate
    "kabs",  # absorption rate
    "plasma_binding",
]

OUTPUT_TISSUE_DATA = [
    "saliva",
    "plasma",
    "urine",
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

