"""
To be easily extendable we do not hardcode information about characteristics in classes,
but define in some custom data structure which is referenced.


Model choices and more specifically possible categories of subject characteristics.

In the future the relationship between the characteristics could be implemented via
an ontology which represents the relationship between the differnent values.


units on CharacteristicType is an ordered iteratable, with the first unit being the default unit.

"""
from collections import namedtuple
from pkdb_app.units import NormalizableUnit

from pkdb_app.substances import SUBSTANCES_DATA

CURRENT_VERSION = [1.0]
VERSIONS = [1.0, ]

CharacteristicType = namedtuple("CharacteristicType", ["value", "category", "dtype", "choices", "units"])
PharmacokineticsType = namedtuple("PharmacokineticsType", ["value", "units", "description"])


def create_choices(collection):
    """ Creates choices from given list of items.
    In case of dictionaries the keys are used to create choices.

    :param collection: iterable collection from which choices are created.
    :return: list of choice tuples
    """
    choices = []
    for item in collection:
        key = item
        if not isinstance(item, str):
            # get_key interface must be provided by item
            key = item.key
        choices.append((key, key))
    return choices


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
    "tablet",
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

FORMAT_MAPPING = {"TSV": FileFormat("TSV", '\t'),
                  "CSV": FileFormat("CSV", ",")}

STUDY_DESIGN_DATA = [
    "single group",     # (interventional study)
    "parallel group",   # (interventional study)
    "crossover",        # (interventional study)
    "cohort",           # (oberservational study)
    "case control",     # (oberservational study)
]
STUDY_DESIGN_CHOICES = [(t, t) for t in STUDY_DESIGN_DATA]



KEYWORDS_DATA = [
    "glycolysis",
    "gluconeogenesis",
    "oxidative phosphorylation",
]
KEYWORDS_DATA_CHOICES = [(t, t) for t in KEYWORDS_DATA]


# TODO: define the units for the characteristic types
CHARACTERISTIC_DATA = [
    # -------------- Species --------------
    CharacteristicType('species', SPECIES, CATEGORIAL_TYPE, ["homo sapiens"], ["-"]),

    # -------------- Anthropometry --------------
    CharacteristicType('height', ANTHROPOMETRY, NUMERIC_TYPE, None, ["cm", 'm']),
    CharacteristicType('weight', ANTHROPOMETRY, NUMERIC_TYPE, None, ["kg"]),
    CharacteristicType('bmi', ANTHROPOMETRY, NUMERIC_TYPE, None, ["kg/m^2"]),
    CharacteristicType('waist circumference', ANTHROPOMETRY, NUMERIC_TYPE, None, ["cm"]),
    CharacteristicType('lean body mass', ANTHROPOMETRY, NUMERIC_TYPE, None, ["kg"]),
    CharacteristicType('percent fat', ANTHROPOMETRY, NUMERIC_TYPE, None, ["%"]),

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
    CharacteristicType('medication type', MEDICATION, CATEGORIAL_TYPE, ["ibuprofen", "paracetamol", "aspirin", "clozapine", "carbon monoxide"], ["-"]),
    CharacteristicType('medication amount', MEDICATION, NUMERIC_TYPE, None, ["-"]),

    CharacteristicType('oral contraceptives', MEDICATION, BOOLEAN_TYPE, BOOLEAN_CHOICES, ["-"]),
    # CharacteristicType('oral contraceptives amount', MEDICATION, NUMERIC_TYPE, None, ["-"]),

    CharacteristicType('abstinence', 'study protocol', CATEGORIAL_TYPE, SUBSTANCES_DATA+["alcohol", "smoking", "grapefruit juice"],
                       ["year", "week", "day", "h"]),

    # -------------- Caffeine --------------
    CharacteristicType('caffeine', LIFESTYLE, BOOLEAN_TYPE, BOOLEAN_CHOICES, ["-"]),
    CharacteristicType('caffeine amount', LIFESTYLE, NUMERIC_TYPE, None, ["mg/day"]),
    CharacteristicType('caffeine amount (beverages)', LIFESTYLE, NUMERIC_TYPE, None, ["1/day"]),

    # -------------- Smoking --------------
    CharacteristicType('smoking', LIFESTYLE, BOOLEAN_TYPE, BOOLEAN_CHOICES, ["-"]),
    CharacteristicType('smoking amount (cigarettes)', LIFESTYLE, NUMERIC_TYPE, None, ["1/day"]),
    CharacteristicType('smoking amount (packyears)', LIFESTYLE, NUMERIC_TYPE, None, ["yr"]),
    CharacteristicType('smoking duration (years)', LIFESTYLE, NUMERIC_TYPE, None, ["yr"]),

    # -------------- Alcohol --------------
    CharacteristicType('alcohol', LIFESTYLE, BOOLEAN_TYPE, BOOLEAN_CHOICES, ["-"]),
    CharacteristicType('alcohol amount', LIFESTYLE, NUMERIC_TYPE, None, ["-"]),
    CharacteristicType('alcohol abstinence', 'study protocol', BOOLEAN_TYPE, BOOLEAN_CHOICES, ["-"]),

    # -------------- Biochemical data --------------
    CharacteristicType('ALT', BIOCHEMICAL_DATA, NUMERIC_TYPE, None, ["IU/I"]),
    CharacteristicType('AST', BIOCHEMICAL_DATA, NUMERIC_TYPE, None, ["IU/I"]),
    CharacteristicType('albumin', BIOCHEMICAL_DATA, NUMERIC_TYPE, None, ["g/dl"]),


    # --------------Genetic variants --------------
    CharacteristicType('genetics', GENETIC_VARIANTS, CATEGORIAL_TYPE, ["CYP2D6 duplication", "CYP2D6 wild type",
                                                                       "CYP2D6 poor metabolizer"], ["-"]),
]

# TODO: define the units for the pk data
PK_DATA = [

    # Area under the curve, extrapolated until infinity
    PharmacokineticsType("auc_inf", 
                         NormalizableUnit({"mg*h/l": None, }, 
                                          ""))


    "mg*h/l": None,
              "µg*h/ml": "mg*h/l"
"µg/ml*h": None,  # -> mg*h/l
"mg*min/l": None,  # -> mg*h/l
"µg*min/ml": None,
"µmol*h/l": None,  # -> mg*h/l (with molar weight)
"µmol/l*h": None,  # -> mg*h/l (with molar weight)
"µg/ml*h/kg": None,  # -> mg*h/l/kg
    
    
    
    
    "auc_end",  # Area under the curve, until end time point (time has to be given as time attribute)

    "amount",
    "cum_amount",  # cumulative amount
    "concentration",
    "ratio",

    "clearance",
    "clearance_renal",
    "clearance_unbound",
    "vd",  # Volume of distribution
    "thalf",  # half-life
    "tmax",  # time of maximum
    "cmax",  # maximum concentration

    "kel",  # elimination rate (often beta)
    "kabs",  # absorption rate
    "fraction_absorbed",  # "often also absolute bioavailability
    "plasma_binding",

    "recovery",
]
PK_DATA_CHOICES = create_choices(PK_DATA)


OUTPUT_TISSUE_DATA = [
    "saliva",
    "plasma",
    "urine",
]

OUTPUT_TISSUE_DATA_CHOICES = create_choices(OUTPUT_TISSUE_DATA)



# TODO: define the units for the interventions
# class, value, dtype (numeric, boolean, categorial), choices
INTERVENTION_DATA = [
    CharacteristicType('dosing', 'dosing', NUMERIC_TYPE, None, ["mg", "mg/kg"]),
    CharacteristicType('smoking cessation', LIFESTYLE, NUMERIC_TYPE, None, ["-"]),
    CharacteristicType('oral contraceptives', MEDICATION, BOOLEAN_TYPE, BOOLEAN_CHOICES, ["-"]),
    CharacteristicType('smoking', 'lifestyle', BOOLEAN_TYPE, BOOLEAN_CHOICES, ["-"]),
    CharacteristicType('abstinence', 'study protocol', CATEGORIAL_TYPE, SUBSTANCES_DATA + ["alcohol", "smoking", "grapefruit juice"],
                   ["year", "week", "day", "h"]),
    CharacteristicType('medication type', MEDICATION, CATEGORIAL_TYPE, ["ibuprofen", "paracetamol", "aspirin", "clozapine", "carbon monoxide"], ["-"]),
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
