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
VERSIONS = [1.0]

CharacteristicType = namedtuple(
    "CharacteristicType", ["key", "category", "dtype", "choices", "units"]
)
PharmacokineticsType = namedtuple(
    "PharmacokineticsType", ["key", "description", "units"]
)


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


def dict_and_choices(data):
    data_dict = {item.key: item for item in data}
    data_choices = [(ctype.key, ctype.key) for ctype in data]
    return data_dict, data_choices


BOOLEAN_TYPE = "boolean"
NUMERIC_TYPE = "numeric"
CATEGORIAL_TYPE = "categorial"
STRING_TYPE = "string"  # can be a free string, no limitations compared to categorial
YES = "Y"
NO = "N"
MIX = "Mixed"
NAN = "NaN"
BOOLEAN_CHOICES = [YES, NO, MIX, NAN]
TIME_NORM_UNIT = "h"

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

FORMAT_MAPPING = {"TSV": FileFormat("TSV", "\t"), "CSV": FileFormat("CSV", ",")}

# ---------------------------------------------------
# Study design
# ---------------------------------------------------
STUDY_DESIGN_DATA = [
    "single group",  # (interventional study)
    "parallel group",  # (interventional study)
    "crossover",  # (interventional study)
    "cohort",  # (oberservational study)
    "case control",  # (oberservational study)
]
STUDY_DESIGN_CHOICES = [(t, t) for t in STUDY_DESIGN_DATA]


# ---------------------------------------------------
# Keywords
# ---------------------------------------------------
KEYWORDS_DATA = [
    "glycolysis",
    "gluconeogenesis",
    "oxidative phosphorylation",
    "hypoglycemia",
    "insulin secretion",
    "diabetes",
    "oral glucose tolerance test",
    "intravenous glucose tolerance test"

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
DOSING = "dosing"
LIFESTYLE = "lifestyle"
BIOCHEMICAL_DATA = "biochemical data"
HEMATOLOGY_DATA = "hematology data"
GENETIC_VARIANTS = "genetic variants"
PHENOTYPE = "phenotype"


dimensionless_norm_unit = NormalizableUnit({"-": None})

organweight_norm_unit = NormalizableUnit({"kg": "g", "g": None})
amountyear_unit = NormalizableUnit({"yr": None})
amountperday_unit = NormalizableUnit({"1/day": None})


# TODO: define the units for the characteristic types
CHARACTERISTIC_DATA = [
    # -------------- Species --------------
    CharacteristicType(
        "species", SPECIES, CATEGORIAL_TYPE, ["homo sapiens"], dimensionless_norm_unit
    ),
    # -------------- Anthropometry --------------
    CharacteristicType(
        "height",
        ANTHROPOMETRY,
        NUMERIC_TYPE,
        None,
        NormalizableUnit({"cm": "m", "m": None}),
    ),
    CharacteristicType(
        "weight", ANTHROPOMETRY, NUMERIC_TYPE, None, NormalizableUnit({"kg": None, "g": "kg"})
    ),
    CharacteristicType(
        "bmi", ANTHROPOMETRY, NUMERIC_TYPE, None, NormalizableUnit({"kg/m^2": None})
    ),
    CharacteristicType(
        "body surface area", ANTHROPOMETRY, NUMERIC_TYPE, None, NormalizableUnit({"m^2": None})
    ),
    CharacteristicType(
        "waist circumference",
        ANTHROPOMETRY,
        NUMERIC_TYPE,
        None,
        NormalizableUnit({"cm": None}),
    ),
    CharacteristicType(
        "lean body mass",  # fat free mass (FFM)
        ANTHROPOMETRY,
        NUMERIC_TYPE,
        None,
        NormalizableUnit({"kg": None}),
    ),
    CharacteristicType(
        "percent fat",  # percent body fat
        ANTHROPOMETRY, NUMERIC_TYPE, None, NormalizableUnit({"%": None})
    ),
    CharacteristicType(
        "obesity index",  # percent of normal body weight
        ANTHROPOMETRY, NUMERIC_TYPE, None, NormalizableUnit({"%": None})
    ),
    CharacteristicType(
        "obese",
        ANTHROPOMETRY,
        BOOLEAN_TYPE,
        BOOLEAN_CHOICES,
        dimensionless_norm_unit,
    ),
    # -------------- Demography --------------
    CharacteristicType(
        "age", DEMOGRAPHICS, NUMERIC_TYPE, None, NormalizableUnit({"yr": None})
    ),
    CharacteristicType(
        "sex",
        DEMOGRAPHICS,
        CATEGORIAL_TYPE,
        ["M", "F", MIX, NAN],
        dimensionless_norm_unit,
    ),
    CharacteristicType(
        "ethnicity",
        DEMOGRAPHICS,
        CATEGORIAL_TYPE,
        [NAN, "african", "afroamerican", "asian", "caucasian", "korean","hispanic", "japanese","chinese"],
        dimensionless_norm_unit,
    ),
    # -------------- Physiology --------------
    CharacteristicType(
        "blood pressure",
        PHYSIOLOGY,
        NUMERIC_TYPE,
        None,
        NormalizableUnit({"mmHg": None}),
    ),
    CharacteristicType(
        "heart rate", PHYSIOLOGY, NUMERIC_TYPE, None, NormalizableUnit({"1/s": None})
    ),
    # -------------- Organ weights --------------
    CharacteristicType(
        "liver weight", ANTHROPOMETRY, NUMERIC_TYPE, None, organweight_norm_unit
    ),
    CharacteristicType(
        "kidney weight", ANTHROPOMETRY, NUMERIC_TYPE, None, organweight_norm_unit
    ),
    CharacteristicType(
        # muscle mass
        "muscle weight", ANTHROPOMETRY, NUMERIC_TYPE, None, organweight_norm_unit
    ),
    CharacteristicType(
        "fat weight", ANTHROPOMETRY, NUMERIC_TYPE, None, organweight_norm_unit
    ),

    # -------------- Patient status --------------
    CharacteristicType(
        "overnight fast",
        PATIENT_STATUS,
        BOOLEAN_TYPE,
        BOOLEAN_CHOICES,
        dimensionless_norm_unit,
    ),
    CharacteristicType(
        "fasted", PATIENT_STATUS, NUMERIC_TYPE, None, NormalizableUnit({"h": None})
    ),
    CharacteristicType(
        "healthy",
        PATIENT_STATUS,
        BOOLEAN_TYPE,
        BOOLEAN_CHOICES,
        dimensionless_norm_unit,
    ),
    CharacteristicType(
        "disease",
        PATIENT_STATUS,
        CATEGORIAL_TYPE,
        [
            NAN,
            "cirrhosis",
            "plasmodium falciparum",
            "alcoholic liver cirrhosis",
            "cirrhotic liver disease",
            "non-cirrhotic liver disease",
            "chronic viral hepatitis",
            "PBC",
            "miscellaneous liver disease",
            "schizophrenia",
            "impaired glucose tolerance",
            "diabetes melitus type 2",
            "diabetes melitus type 1",
            "end-stage renal disease",
            "chronic viral hepatitis",
            "sickle cell"
        ],
        dimensionless_norm_unit,
    ),
    CharacteristicType(
        "disease duration", LIFESTYLE, NUMERIC_TYPE, None, amountyear_unit
    ),

    # -------------- Medication --------------
    CharacteristicType(
        "medication", MEDICATION, BOOLEAN_TYPE, BOOLEAN_CHOICES, dimensionless_norm_unit
    ),
    CharacteristicType(
        "medication type",
        MEDICATION,
        CATEGORIAL_TYPE,
        ["diet", "metformin", "insulin", "metformin+glipizide", "aspirin", "carbon monoxide", "clozapine", "ibuprofen", "hydrochlorthiazide","amiloride","chlordiazepoxide","paracetamol","salbutamol","diltiazem","hemodialysis","enalapril","beclometasone","spinal anaesthesia", "CCM"],
        dimensionless_norm_unit,
    ),
    CharacteristicType(
        "medication amount", MEDICATION, NUMERIC_TYPE, None, dimensionless_norm_unit
    ),
    CharacteristicType(
        "oral contraceptives",
        MEDICATION,
        BOOLEAN_TYPE,
        BOOLEAN_CHOICES,
        dimensionless_norm_unit,
    ),
    CharacteristicType(
        "abstinence",
        "study protocol",
        CATEGORIAL_TYPE,
        SUBSTANCES_DATA + ["alcohol", "smoking", "grapefruit juice", "medication", "drug", "kola nuts", "coffee","tee"],
        NormalizableUnit({"-": None, "yr": None, "week": None, "day": None, "h": None}),
    ),
    CharacteristicType(
        "consumption",
        "study protocol",
        CATEGORIAL_TYPE,
        SUBSTANCES_DATA + ["alcohol", "smoking", "grapefruit juice", "medication", "drug", "kola nuts", "coffee","tee"],
        NormalizableUnit({"-": None, "g/day": None, "mg/day": None, "cups/day": None}),
    ),


    # -------------- Nutrition -----------------

    CharacteristicType(
        "metabolic challenge",
        MEDICATION,
        CATEGORIAL_TYPE,
        ["mixed-meal",
         "oral glucose tolerance test",
         "intravenous glucose tolerance test",
         "hypoglycemic clamp",
         "hyperinsulinemic euglycemic clamp",
         "isoglycemic glucose infusion",
         "protein solution",
         "lipid-glucose-protein drink"
         ],
        dimensionless_norm_unit,
    ),

    # -------------- sleeping & circadian rhythm -----------------

    CharacteristicType(
        "sleeping",
        LIFESTYLE,
        CATEGORIAL_TYPE,
        ["asleep",
         "awake"
        ],
        dimensionless_norm_unit,
    ),

    CharacteristicType(
        "circadian",
        LIFESTYLE,
        CATEGORIAL_TYPE,
        ["daytime",
         "nighttime"
        ],
        dimensionless_norm_unit,
    ),


    # -------------- Caffeine --------------
    CharacteristicType(
        "caffeine", LIFESTYLE, BOOLEAN_TYPE, BOOLEAN_CHOICES, dimensionless_norm_unit
    ),
    CharacteristicType(
        "caffeine amount",
        LIFESTYLE,
        NUMERIC_TYPE,
        None,
        NormalizableUnit({"mg/day": None}),
    ),
    CharacteristicType(
        "caffeine amount (beverages)", LIFESTYLE, NUMERIC_TYPE, None, amountperday_unit
    ),
    # -------------- Smoking --------------
    CharacteristicType(
        "smoking", LIFESTYLE, BOOLEAN_TYPE, BOOLEAN_CHOICES, dimensionless_norm_unit
    ),
    CharacteristicType(
        "smoking amount (cigarettes)", LIFESTYLE, NUMERIC_TYPE, None, amountperday_unit
    ),
    CharacteristicType(
        "smoking amount (packyears)", LIFESTYLE, NUMERIC_TYPE, None, amountyear_unit
    ),
    CharacteristicType(
        "smoking duration (years)", LIFESTYLE, NUMERIC_TYPE, None, amountyear_unit
    ),
    # -------------- Alcohol --------------
    CharacteristicType(
        "alcohol", LIFESTYLE, BOOLEAN_TYPE, BOOLEAN_CHOICES, dimensionless_norm_unit
    ),
    CharacteristicType(
        "alcohol amount", LIFESTYLE, NUMERIC_TYPE, None, dimensionless_norm_unit
    ),
    CharacteristicType(
        "alcohol abstinence",
        "study protocol",
        BOOLEAN_TYPE,
        BOOLEAN_CHOICES,
        NormalizableUnit({"-": None, "yr": None, "week": None, "day": None, "h": None}),
    ),
    # -------------- Biochemical data --------------
    CharacteristicType(
        "ALT", BIOCHEMICAL_DATA, NUMERIC_TYPE, None, NormalizableUnit({"IU/I": None})
    ),
    CharacteristicType(
        "AST", BIOCHEMICAL_DATA, NUMERIC_TYPE, None, NormalizableUnit({"IU/I": None})
    ),
    CharacteristicType(
        "albumin", BIOCHEMICAL_DATA, NUMERIC_TYPE, None, NormalizableUnit({"g/dl": None}),
    ),
    CharacteristicType(
        "glucose", BIOCHEMICAL_DATA, NUMERIC_TYPE, None, NormalizableUnit({"mg/dl": None, "mmol/l": None}),
    ),
    CharacteristicType(
        "insulin", BIOCHEMICAL_DATA, NUMERIC_TYPE, None, NormalizableUnit({"µU/ml": None, "pmol/l": None}),
    ),
    CharacteristicType(
        "glucagon", BIOCHEMICAL_DATA, NUMERIC_TYPE, None, NormalizableUnit({"pmol/l": None}),
    ),
    CharacteristicType(
        "cholesterol", BIOCHEMICAL_DATA, NUMERIC_TYPE, None, NormalizableUnit({"mmol/l": None}),
    ),
    CharacteristicType(
        "triglyceride", BIOCHEMICAL_DATA, NUMERIC_TYPE, None, NormalizableUnit({"mmol/l": None}),
    ),
    CharacteristicType(
        "LDL-C", BIOCHEMICAL_DATA, NUMERIC_TYPE, None, NormalizableUnit({"mmol/l": None}),
    ),
    CharacteristicType(
        "LDL-H", BIOCHEMICAL_DATA, NUMERIC_TYPE, None, NormalizableUnit({"mmol/l": None}),
    ),
    CharacteristicType(
        "HbA1c", BIOCHEMICAL_DATA, NUMERIC_TYPE, None, NormalizableUnit({"%": None}),
    ),

    # --------------Genetic variants --------------
    CharacteristicType(
        "genetics",
        GENETIC_VARIANTS,
        CATEGORIAL_TYPE,
        ["CYP2D6 duplication", "CYP2D6 wild type", "CYP2D6 poor metabolizer"],
        dimensionless_norm_unit,
    ),
    CharacteristicType(
        "phenotype",
        PHENOTYPE,
        CATEGORIAL_TYPE,
        ["PM","IM","EM","UM"],
        dimensionless_norm_unit,
    ),
CharacteristicType(
        "CYP2D6 genotype",
        GENETIC_VARIANTS,
        CATEGORIAL_TYPE,
        ["*1/*1",
         "*7/*41",
         "*x/*4",
         "*4/*4",
         "*3/*4",
         "*1x2/*1",
         "*1/*41",
         "*4/*41",
         "*1/*4",
         "*10/*10",
         "*1/*10",
         "*other/*other",
         "*other/*17",
         "*other/*29",
         "*other/*41",
         "*17/*17",
         "*29/*29",
         "*5/*5",
         ],
        dimensionless_norm_unit,
    ),
    CharacteristicType(
        "metabolic ratio",
         PHENOTYPE,
         NUMERIC_TYPE,
        None,
        dimensionless_norm_unit,
    ),

]


CHARACTERISTIC_DTYPE = {item.key: item.dtype for item in CHARACTERISTIC_DATA}
CHARACTERISTIC_CATEGORIES = set([item.key for item in CHARACTERISTIC_DATA])
CHARACTERISTIC_CATEGORIES_UNDERSCORE = set(
    [c.replace(" ", "_") for c in CHARACTERISTIC_CATEGORIES]
)
CHARACTERISTIC_DICT, CHARACTERISTIC_CHOICES = dict_and_choices(CHARACTERISTIC_DATA)


# ---------------------------------------------------
# Interventions
# ---------------------------------------------------
INTERVENTION_ROUTE = ["oral", "iv","intramuscular"]
INTERVENTION_ROUTE_CHOICES = create_choices(INTERVENTION_ROUTE)
INTERVENTION_APPLICATION = ["single dose", "multiple dose", "continuous injection", "variable infusion", "constant infusion"]
INTERVENTION_APPLICATION_CHOICES = create_choices(INTERVENTION_APPLICATION)

INTERVENTION_FORM = ["tablet", "capsule", "solution", NAN]
INTERVENTION_FORM_CHOICES = create_choices(INTERVENTION_FORM)

INTERVENTION_DATA = [
    CharacteristicType(
        "dosing",
        DOSING,
        NUMERIC_TYPE,
        None,
        NormalizableUnit({"g": None, "mg": None, "mg/kg": None, "g/kg": None, "mU/kg": None, "pmol/kg": None, "pmol/kg/min": None,
                          "mg/day": None, "mg/70kg": "mg/kg", "nmol": None}),
    ),
    CharacteristicType(
        "smoking cessation", LIFESTYLE, NUMERIC_TYPE, None, dimensionless_norm_unit
    ),
    CHARACTERISTIC_DICT["medication type"],
    CHARACTERISTIC_DICT["metabolic challenge"],
    CHARACTERISTIC_DICT["abstinence"],
    CHARACTERISTIC_DICT["smoking"],
    CHARACTERISTIC_DICT["oral contraceptives"],
    CHARACTERISTIC_DICT["sleeping"],
    CHARACTERISTIC_DICT["circadian"],
]
INTERVENTION_DICT, INTERVENTION_CHOICES = dict_and_choices(INTERVENTION_DATA)


def validate_categorials(data, category_class):
    """ Function which validates given categorial data against categorial defintion and allowed values.

    :param data:
    :param model_name:
    :return:
    """
    category = data.get("category", None)
    if category:
        if category_class == "characteristica":
            allowed_category_dict = CHARACTERISTIC_DICT
        elif category_class == "intervention":
            allowed_category_dict = INTERVENTION_DICT
        else:
            raise ValueError(f"category_class not supported: {category_class}")

        choice = data.get("choice", None)
        unit = data.get("unit", None)

        # check that allowed category
        if category not in allowed_category_dict:
            msg = f"category <{category}> is not supported for {category_class}"
            raise ValueError({"category": msg})

        # get the allowed definition
        model_categorical = allowed_category_dict[category]
        if choice:
            if (model_categorical.dtype == CATEGORIAL_TYPE) or (
                model_categorical.dtype == BOOLEAN_TYPE
            ):
                if choice not in model_categorical.choices:
                    msg = f"{choice} is not part of {model_categorical.choices} for {model_categorical.key}"
                    raise ValueError({"choice": msg})
            else:
                msg = f"for category: <{category}> no choices are allowed. If you are trying to insert a numerical value, use keword value, mean or median"
                raise ValueError({"choice": msg})

        # check unit
        if unit is None:
            unit = "-"  # handle no unit as dimensionless
        if not model_categorical.units.is_valid_unit(unit):
                msg = f"[{unit}] is not in the allowed units. For {model_categorical.key} allowed units are {model_categorical.units.keys()}"
                raise ValueError({"unit": msg})

    return data


# ---------------------------------------------------
# Output
# ---------------------------------------------------
OUTPUT_TISSUE_DATA = ["saliva", "plasma", "serum", "urine", "spinal fluid","saliva/plasma","breath"]

OUTPUT_TISSUE_DATA_CHOICES = create_choices(OUTPUT_TISSUE_DATA)


# ---------------------------------------------------
# Pharmacokinetics data
# ---------------------------------------------------
auc_norm_unit = NormalizableUnit(
    {
        "mg*h/l": None,
        "mg/l*h": "mg*h/l",
        "µg*h/ml": "mg*h/l",
        "h*µg/ml":"mg*h/l",
        "h*µg/l":"mg*h/l",
        "µg/ml*h": "mg*h/l",
        "ng*min/ml": "mg*h/l",
        "mg*min/l": "mg*h/l",
        "mg/l*min": "mg*h/l",
        "ng*h/ml": "mg*h/l",
        "µg*min/ml": "mg*h/l",
        "µmol*h/l": None,
        "µmol/l*h": "µmol*h/l",
        "pmol/ml*h": None,
        "h*pmol/ml": None,
        "nmol*h/l": "µmol*h/l",
        "µg/ml*h/kg": "mg*h/l/kg",
        "µU/ml*min": None,
    }
)
aumc_norm_unit = NormalizableUnit(
    {
        "mg*h^2/l": None,
        "mg/l*h^2": "mg*h^2/l",
        "µg*h^2/ml": "mg*h^2/l",
        "µg/ml*h^2": "mg*h^2/l",
        "ng*min^2/ml": "mg*h^2/l",
        "mg*min^2/l": "mg*h^2/l",
        "mg/l*min^2": "mg*h^2/l",
        "ng*h^2/ml": "mg*h^2/l",
        "µg*min^2/ml": "mg*h^2/l",
        "µmol*h^2/l": None,
        "µmol/l*h^2": "µmol*h^2/l",
        "pmol/ml*h^2": None,
        "nmol*h^2/l": "µmol*h^2/l",
        "µg/ml*h^2/kg": "mg*h^2/l/kg",
        "µU/ml*min^2": None,
    }
)
amount_norm_unit = NormalizableUnit({"mg": None, "µmol": None, "mmol": None})
concentration_norm_unit = NormalizableUnit(
    {
        "mg/100ml": None,
        "µg/ml": None,
        "µg/l": "µg/ml",
        "µg/dl": "µg/ml",
        "mg/dl": "µg/ml",
        "mg/l": "µg/ml",
        "ng/l": "µg/ml",
        "pg/ml": None,
        "g/dl": "µg/ml",
        "ng/ml": "µg/ml",
        "mmol/l": None,
        "µmol/l": None,
        "nmol/l": None,
        "nmol/ml": None,
        "pmol/l": None,
        "pmol/ml": None,
        "fmol/l": None,
        "µU/ml": None,

        "ng/g": None, # per g plasma
    }
)
norm_units =  {
    "-": None,
    "%": "-",
    "mega": None,
    "kilo": None,
    "milli": None,
    "micro": None,
     }
ratio_norm_unit = NormalizableUnit(norm_units)
recovery_norm_unit = NormalizableUnit(
    {
        **norm_units,
        "µmol": None,
     }
   )
clearance_norm_unit = NormalizableUnit(
    {
        "ml/min": "l/h",
        "ml/h": "l/h",  # -> ml/min
        "l/h": None,
        "l/h/kg": None,
        "ml/h/kg": "l/h/kg",  # -> l/h/kg
        "ml/kg/min": None,
        "ml/min/kg": "l/h/kg",  # -> l/h/kg
        "ml/min/1.73m^2": None,
        "µmol/l*h": "µmol*h/l",
    }
)

vd_norm_unit = NormalizableUnit({"l": None, "ml": "l", "l/kg": None, "ml/kg": "l/kg"})
time_norm_unit = NormalizableUnit({"h": None, "min": "h"})
rate_norm_unit = NormalizableUnit({
    "1/min": "1/h",
    "1/h": None,
    "pmol/min": None,
    "pmol/kg/min": None,
    "µmol/min/kg": "µmol/kg/min",
    "µmol/kg/min": None,
    "mU/min": None,
    "mg/min": None,
    "mg/kg/min": None,
})


PK_DATA = [
    PharmacokineticsType(
        "auc_inf",
        "Area under the curve (AUC), extrapolated until infinity.",
        auc_norm_unit,
    ),
    PharmacokineticsType(
        "auc_end",
        "Area under the curve (AUC), until last time point. Time period is required for calculation.",
        auc_norm_unit,
    ),
    PharmacokineticsType(
        "auc_relative",
        "Relative area under the curve (AUC), AUC of a substance relative to other measured metabolites",
        ratio_norm_unit,
    ),
    PharmacokineticsType(
        "aumc_inf",
        "Area under first moment curve (AUMC), extrapolated until infinity.",
        aumc_norm_unit,
    ),
    PharmacokineticsType("amount", "Amount of given substance.", amount_norm_unit),
    PharmacokineticsType(
        "cum_amount",
        "Cummulative amount of given substance. Time period is required for calculation.",
        amount_norm_unit,
    ),
    PharmacokineticsType(
        "concentration", "Concentration of given substance.", concentration_norm_unit
    ),
PharmacokineticsType(
        "concentration_unbound", "Concentration of unbound substance.", concentration_norm_unit
    ),
    PharmacokineticsType("ratio", "Ratio between substances.", ratio_norm_unit),
    PharmacokineticsType(
        "clearance", "Total/apparent clearance of given substance. "
                     "If the clearance is based on the unbound substance use clearance_unbount. "
                     "If the clearance refers to renal clearance use clearance_renal.", clearance_norm_unit
    ),
    PharmacokineticsType(
        "clearance_unbound", "Clearance of unbound substance.", clearance_norm_unit
    ),
    PharmacokineticsType(
        "clearance_intrinsic", "Intrinsic clearance of substance.", clearance_norm_unit
    ),
    PharmacokineticsType(
        "clearance_renal", "Renal clearance of given substance.", clearance_norm_unit
    ),
    PharmacokineticsType(
        "vd", "Volume of distribution. "
              "If the volume of distribution is calculated with the unbound substance use vd_unbound.", vd_norm_unit
    ),
    PharmacokineticsType(
        "vd_unbound", "Volume of distribution for unbound substance.", vd_norm_unit
    ),
    PharmacokineticsType("thalf", "Half-life for given substance.", time_norm_unit),
    PharmacokineticsType(
        "tmax", "Time of maximum for given substance.", time_norm_unit
    ),
    PharmacokineticsType(
        "oro-cecal transit time", "The transit time was taken as the time when breath hydrogen excretionincreased to above twice the baseline value.", time_norm_unit
    ),
    PharmacokineticsType(
        "mrt",
        "Mean residence time (MRT). MRT = AUMC/AUC",
        time_norm_unit,
    ),
    PharmacokineticsType(
        "cmax", "Maximum concentration for given substance.", concentration_norm_unit
    ),
    PharmacokineticsType(
        "kel", "Elimination rate for given substance.", rate_norm_unit
    ),
    PharmacokineticsType(
        "kabs", "Absorption rate for given substance.", rate_norm_unit
    ),
    PharmacokineticsType(
        "fraction_absorbed", "Fraction absorbed of given substance.", ratio_norm_unit
    ),
    PharmacokineticsType(
        "plasma_binding", "Plasma binding of given substance (see also fraction unbound).", ratio_norm_unit
    ),
    PharmacokineticsType(
        "fraction_unbound", "Unbound fraction of given substance (see also plasma_binding).", ratio_norm_unit
    ),
    PharmacokineticsType(
        "recovery", "Fraction recovered of given substance.", recovery_norm_unit
    ),
    PharmacokineticsType(
        "egp", "endogenous glucose production (rate)", rate_norm_unit
    ),
    PharmacokineticsType(
        "ra", "rate appearance (rate)", rate_norm_unit
    ),
    PharmacokineticsType(
        "rd", "rate disappearance (rate)", rate_norm_unit
    ),
    PharmacokineticsType(
        "rate_cycling", "rate cycling (rate)", rate_norm_unit
    ),
    PharmacokineticsType(
        "rate_secretion", "rate secretion (rate)", rate_norm_unit
    ),

    PharmacokineticsType(
        "Matsuda index", "Matsuda index", NormalizableUnit({"-": None})
    ),
    PharmacokineticsType(
        "QUICKI", "quantitative insulin sensitivity check index", NormalizableUnit({"-": None})
    ),
    PharmacokineticsType(
        "HOMA-IR", "homeostatic model assessment for insulin resistance", NormalizableUnit({"-": None})
    ),
    PharmacokineticsType(
        "Insulinogenic index", "Insulinogenic index", NormalizableUnit({"-": None})
    ),
    PharmacokineticsType(
        "Oral disposition index", "Oral disposition index", NormalizableUnit({"-": None})
    ),
]
PK_DATA_DICT, PK_DATA_CHOICES = dict_and_choices(PK_DATA)



if __name__ == "__main__":
    """ 
    Just run this module to have simple check if all units are working and definitions are correct.
    """

    unit = NormalizableUnit({"1/min": "1/h", "1/h": None})
    print("valid 1/min:", unit.is_valid_unit("1/min"))
    print("valid mg:", unit.is_valid_unit("mg"))
