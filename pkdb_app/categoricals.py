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

CharacteristicType = namedtuple("CharacteristicType", ["key", "category", "dtype", "choices", "units"])
PharmacokineticsType = namedtuple("PharmacokineticsType", ["key", "description", "units"])


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
BOOLEAN_CHOICES = [YES, NO, MIX, NAN]


# ---------------------------------------------------
# Interventions
# ---------------------------------------------------
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


# ---------------------------------------------------
# CharacteristicTypes
# ---------------------------------------------------

INCLUSION_CRITERIA = "inclusion"
EXCLUSION_CRITERIA = "exclusion"
GROUP_CRITERIA = "group"
CHARACTERISTICA_TYPES = [INCLUSION_CRITERIA, EXCLUSION_CRITERIA, GROUP_CRITERIA]
CHARACTERISTICA_CHOICES = [(t, t) for t in CHARACTERISTICA_TYPES]


# ---------------------------------------------------
# File formats
# ---------------------------------------------------
FileFormat = namedtuple("FileFormat", ["name", "delimiter"])

FORMAT_MAPPING = {"TSV": FileFormat("TSV", '\t'),
                  "CSV": FileFormat("CSV", ",")}

# ---------------------------------------------------
# Study design
# ---------------------------------------------------
STUDY_DESIGN_DATA = [
    "single group",     # (interventional study)
    "parallel group",   # (interventional study)
    "crossover",        # (interventional study)
    "cohort",           # (oberservational study)
    "case control",     # (oberservational study)
]
STUDY_DESIGN_CHOICES = [(t, t) for t in STUDY_DESIGN_DATA]


# ---------------------------------------------------
# Keywords
# ---------------------------------------------------
KEYWORDS_DATA = [
    "glycolysis",
    "gluconeogenesis",
    "oxidative phosphorylation",
]
KEYWORDS_DATA_CHOICES = [(t, t) for t in KEYWORDS_DATA]

# ---------------------------------------------------
# Characteristics
# ---------------------------------------------------
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


dimensionless_norm_unit = NormalizableUnit({
    "-": None,
})

organweight_norm_unit = NormalizableUnit({
    "kg": "g",
    "g": None,
})
amountyear_unit = NormalizableUnit({
    "yr": None,
})
amountperday_unit = NormalizableUnit({
    "1/day": None,
})


# TODO: define the units for the characteristic types
CHARACTERISTIC_DATA = [
    # -------------- Species --------------
    CharacteristicType('species', SPECIES, CATEGORIAL_TYPE, ["homo sapiens"],
                       dimensionless_norm_unit),

    # -------------- Anthropometry --------------
    CharacteristicType('height', ANTHROPOMETRY, NUMERIC_TYPE, None,
                       NormalizableUnit({"cm": "m", "m": None})),
    CharacteristicType('weight', ANTHROPOMETRY, NUMERIC_TYPE, None,
                       NormalizableUnit({"kg": None})),
    CharacteristicType('bmi', ANTHROPOMETRY, NUMERIC_TYPE, None,
                       NormalizableUnit({"kg/m^2": None})),
    CharacteristicType('waist circumference', ANTHROPOMETRY, NUMERIC_TYPE, None,
                       NormalizableUnit({"cm": None})),
    CharacteristicType('lean body mass', ANTHROPOMETRY, NUMERIC_TYPE, None,
                       NormalizableUnit({"kg": None})),
    CharacteristicType('percent fat', ANTHROPOMETRY, NUMERIC_TYPE, None,
                       NormalizableUnit({"%": None})),

    # -------------- Demography --------------
    CharacteristicType('age', DEMOGRAPHICS, NUMERIC_TYPE, None,
                       NormalizableUnit({"yr": None})),
    CharacteristicType('sex', DEMOGRAPHICS, CATEGORIAL_TYPE, ["M", "F", MIX, NAN],
                       dimensionless_norm_unit),
    CharacteristicType('ethnicity', DEMOGRAPHICS, CATEGORIAL_TYPE, [
                            NAN,
                            "african",
                            "afroamerican",
                            "asian",
                            "caucasian",
                       ],
                       dimensionless_norm_unit),

    # -------------- Physiology --------------
    CharacteristicType('blood pressure', PHYSIOLOGY, NUMERIC_TYPE, None,
                       NormalizableUnit({"mmHg": None})),
    CharacteristicType('heart rate', PHYSIOLOGY, NUMERIC_TYPE, None,
                       NormalizableUnit({"1/s": None})),

    # -------------- Organ weights --------------
    CharacteristicType('liver weight', ANTHROPOMETRY, NUMERIC_TYPE, None,
                       organweight_norm_unit),
    CharacteristicType('kidney weight', ANTHROPOMETRY, NUMERIC_TYPE, None,
                       organweight_norm_unit),

    # -------------- Patient status --------------
    CharacteristicType('overnight fast', PATIENT_STATUS, BOOLEAN_TYPE, BOOLEAN_CHOICES,
                       dimensionless_norm_unit),
    CharacteristicType('fasted', PATIENT_STATUS, NUMERIC_TYPE, None,
                       NormalizableUnit({"h": None})),
    CharacteristicType('healthy', PATIENT_STATUS, BOOLEAN_TYPE, BOOLEAN_CHOICES,
                       dimensionless_norm_unit),
    CharacteristicType('disease', PATIENT_STATUS, CATEGORIAL_TYPE, [
                            NAN,
                            "cirrhosis",
                            "plasmodium falciparum",
                            "alcoholic liver cirrhosis",
                            "cirrhotic liver disease",
                            "PBC",
                            "miscellaneous liver disease",
                            "schizophrenia"
                        ],
                        dimensionless_norm_unit),

    # -------------- Medication --------------
    CharacteristicType('medication', MEDICATION, BOOLEAN_TYPE, BOOLEAN_CHOICES,
                       dimensionless_norm_unit),
    CharacteristicType('medication type', MEDICATION, CATEGORIAL_TYPE, [
                            "aspirin",
                            "carbon monoxide"
                            "clozapine",
                            "ibuprofen",
                            "paracetamol",
                        ],
                        dimensionless_norm_unit),
    CharacteristicType('medication amount', MEDICATION, NUMERIC_TYPE, None,
                       dimensionless_norm_unit),

    CharacteristicType('oral contraceptives', MEDICATION, BOOLEAN_TYPE, BOOLEAN_CHOICES,
                       dimensionless_norm_unit),

    CharacteristicType('abstinence', 'study protocol', CATEGORIAL_TYPE,
                       SUBSTANCES_DATA + [
                            "alcohol",
                            "smoking",
                            "grapefruit juice"
                       ],
                       NormalizableUnit({"yr": None, "week": None, "day": None, "h": None})),

    # -------------- Caffeine --------------
    CharacteristicType('caffeine', LIFESTYLE, BOOLEAN_TYPE, BOOLEAN_CHOICES,
                       dimensionless_norm_unit),
    CharacteristicType('caffeine amount', LIFESTYLE, NUMERIC_TYPE, None,
                       NormalizableUnit({'mg/day': None})),
    CharacteristicType('caffeine amount (beverages)', LIFESTYLE, NUMERIC_TYPE, None,
                       amountperday_unit),

    # -------------- Smoking --------------
    CharacteristicType('smoking', LIFESTYLE, BOOLEAN_TYPE, BOOLEAN_CHOICES,
                       dimensionless_norm_unit),
    CharacteristicType('smoking amount (cigarettes)', LIFESTYLE, NUMERIC_TYPE, None,
                       amountperday_unit),
    CharacteristicType('smoking amount (packyears)', LIFESTYLE, NUMERIC_TYPE, None,
                       amountyear_unit),
    CharacteristicType('smoking duration (years)', LIFESTYLE, NUMERIC_TYPE, None,
                       amountyear_unit),

    # -------------- Alcohol --------------
    CharacteristicType('alcohol', LIFESTYLE, BOOLEAN_TYPE, BOOLEAN_CHOICES,
                       dimensionless_norm_unit),
    CharacteristicType('alcohol amount', LIFESTYLE, NUMERIC_TYPE, None,
                       dimensionless_norm_unit),
    CharacteristicType('alcohol abstinence', 'study protocol', BOOLEAN_TYPE, BOOLEAN_CHOICES,
                       dimensionless_norm_unit),

    # -------------- Biochemical data --------------
    CharacteristicType('ALT', BIOCHEMICAL_DATA, NUMERIC_TYPE, None,
                       NormalizableUnit({'IU/I': None})),
    CharacteristicType('AST', BIOCHEMICAL_DATA, NUMERIC_TYPE, None,
                       NormalizableUnit({'IU/I': None})),
    CharacteristicType('albumin', BIOCHEMICAL_DATA, NUMERIC_TYPE, None,
                       NormalizableUnit({"g/dl": None})),

    # --------------Genetic variants --------------
    CharacteristicType('genetics', GENETIC_VARIANTS, CATEGORIAL_TYPE, [
                        "CYP2D6 duplication",
                        "CYP2D6 wild type",
                        "CYP2D6 poor metabolizer"
                        ],
                       dimensionless_norm_unit),
]


# ---------------------------------------------------
# Pharmacokinetics data
# ---------------------------------------------------
auc_norm_unit =  NormalizableUnit({
    "mg*h/l": None,
    "µg*h/ml": "mg*h/l",
    "µg/ml*h": "mg*h/l",
    "mg*min/l": "mg*h/l",
    "µg*min/ml": None,
    "µmol*h/l": None,
    "µmol/l*h": None,
    "µg/ml*h/kg": "mg*h/l/kg",
})
amount_norm_unit = NormalizableUnit({
    "mg": None,
    "mmol": None,
})
concentration_norm_unit = NormalizableUnit({
    "µg/ml": None,
    'mg/dl': None,
    "mg/l": None,
    'g/dl': None,
    "ng/ml": None,
    "µmol/l": None,
    "nmol/l": None,
    "mmol/l": None,
})
ratio_norm_unit = NormalizableUnit({
    "-": None,
    '%': '-',
})
clearance_norm_unit = NormalizableUnit({
    "ml/min": None,
    "ml/h": None,  # -> ml/min
    "l/h/kg": None,
    "ml/h/kg": None,  # -> l/h/kg
    "ml/min/kg": None,  # -> l/h/kg
    "ml/min/1.73m^2": None,
})
vd_norm_unit = NormalizableUnit({
    "l": None,
    "ml": 'l',
    'l/kg': None,
    'ml/kg': 'l/kg',
})
time_norm_unit = NormalizableUnit({
    "h": None,
    "min": 'h',
})
rate_norm_unit = NormalizableUnit({
    "1/min": "1/h",
    "1/h": None,
})


PK_DATA = [
    PharmacokineticsType("auc_inf",
                         "Area under the curve (AUC), extrapolated until infinity.",
                         auc_norm_unit),

    PharmacokineticsType("auc_end",
                         "Area under the curve (AUC), until last time point. Time period is required for calculation.",
                         auc_norm_unit),

    PharmacokineticsType("amount",
                         "Amount of given substance.",
                         amount_norm_unit),

    PharmacokineticsType("cum_amount",
                         "Cummulative amount of given substance. Time period is required for calculation.",
                         amount_norm_unit),

    PharmacokineticsType("concentration",
                         "Concentration of given substance.",
                         concentration_norm_unit),

    PharmacokineticsType("ratio",
                         "Ratio between substances.",
                         ratio_norm_unit),

    PharmacokineticsType("clearance",
                         "Clearance of given substance.",
                         clearance_norm_unit),

    PharmacokineticsType("clearance_renal",
                         "Renal clearance of given substance.",
                         clearance_norm_unit),

    PharmacokineticsType("clearance_unbound",
                         "Clearance of unbound substance.",
                         clearance_norm_unit),

    PharmacokineticsType("vd",
                         "Volume of distribution.",
                         vd_norm_unit),

    PharmacokineticsType("thalf",
                         "Half-life for given substance.",
                         time_norm_unit),

    PharmacokineticsType("tmax",
                         "Time of maximum for given substance.",
                         time_norm_unit),

    PharmacokineticsType("cmax",
                         "Maximum concentration for given substance.",
                         concentration_norm_unit),

    PharmacokineticsType("kel",
                         "Elimination rate for given substance.",
                         rate_norm_unit),

    PharmacokineticsType("kabs",
                         "Absorption rate for given substance.",
                         rate_norm_unit),

    PharmacokineticsType("fraction_absorbed",
                         "Fraction absorbed of given substance.",
                         ratio_norm_unit),

    PharmacokineticsType("plasma_binding",
                         "Fraction absorbed of given substance.",
                         ratio_norm_unit),

    PharmacokineticsType("revovery",
                         "Fraction recovered of given substance.",
                         ratio_norm_unit),
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
    data_dict = {item.key: item for item in data}
    data_choices = [(ctype.key, ctype.key) for ctype in data]
    return data_dict, data_choices

CHARACTERISTIC_DTYPE = {item.key : item.dtype for item in CHARACTERISTIC_DATA}
CHARACTERISTIC_CATEGORIES = set([item.key for item in CHARACTERISTIC_DATA])
CHARACTERISTIC_CATEGORIES_UNDERSCORE = set([c.replace(' ', '_') for c in CHARACTERISTIC_CATEGORIES])
CHARACTERISTIC_DICT, CHARACTERISTIC_CHOICES = dict_and_choices(CHARACTERISTIC_DATA)
INTERVENTION_DICT, INTERVENTION_CHOICES = dict_and_choices(INTERVENTION_DATA)


if __name__ == "__main__":
    pass
