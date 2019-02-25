"""
To be easily extendable we do not hardcode information about characteristics in classes,
but define in some custom data structure which is referenced.


Model choices and more specifically possible categories of subject characteristics.

In the future the relationship between the characteristics could be implemented via
an ontology which represents the relationship between the differnent values.


units on CharacteristicType is an ordered iteratable, with the first unit being the default unit.

"""
from collections import namedtuple


from .units_old import NormalizableUnit
from .substances.substances import SUBSTANCES_DATA
from .units import ureg, NO_UNIT, ORGAN_WEIGHT_UNIT, height_units, weight_units, bmi_units, body_surface_area_units, \
    waist_circumference_units, lean_body_mass_units, percent_fat_units, obesity_index_units, age_unit_units, \
    blood_pressure_units, heart_rate_units, fasted_units, AMOUNT_PER_YEAR, abstinence_units, consumption_units

CURRENT_VERSION = [1.0]
VERSIONS = [1.0]


class CharacteristicType(object):
    def __init__(self, key, category, dtype, choices, n_units):
        self.key = key  # name of characteristica
        self.category = category
        self.dtype = dtype
        self.choices = choices
        self.n_units = n_units  # list of units to which are the normalized units. Important: Each should have a unique dimension.

    @property
    def n_units_p(self):
        """

        :return: list of norm units in the data format of pint
        """
        return [ureg(unit) for unit in self.n_units]

    @property
    def valid_dimensions(self):
        return [unit.dimensionality for unit in self.n_units_p]

    @property
    def dimension_to_n_unit(self):
        return {n_unit_p.dimensionality: n_unit_p for n_unit_p in self.n_units_p}

    def validate_unit(self, unit):
        return ureg(unit).dimensionality in self.valid_dimensions

    def validate_choice(self, choice):
        return choice in self.choices

    def normalize(self, quantity, unit):
        this_unit_p = ureg(unit)
        unit_dim = unit.dimensionality
        this_norm_unit_p = self.dimension_to_n_unit[unit_dim]
        result = (quantity * this_unit_p).to(this_norm_unit_p)
        return result





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
# EXCLUSION_CRITERIA = "exclusion"  # characteristica based on exclusion information
DEFAULT_CRITERIA = "default"
CHARACTERISTICA_TYPES = [DEFAULT_CRITERIA]
CHARACTERISTICA_CHOICES = [(t, t) for t in CHARACTERISTICA_TYPES]

# ---------------------------------------------------
# File formats
# ---------------------------------------------------
FileFormat = namedtuple("FileFormat", ["name", "delimiter"])

FORMAT_MAPPING = {"TSV": FileFormat("TSV", "\t"), "CSV": FileFormat("CSV", ",")}


# ---------------------------------------------------
# Study licence
# ---------------------------------------------------
OPEN = "open"
CLOSED = "closed"

STUDY_LICENCE_DATA = [
    OPEN,  # (open reference)
    CLOSED,
]

STUDY_LICENCE_CHOICES = [(t, t) for t in STUDY_LICENCE_DATA]

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
STUDY_PROTOCOL = "study protocol"
CYP2D6_PHENOTYPE = "CYP2D6 phenotype"


CHARACTERISTIC_DATA = [
    # -------------- Species --------------
    CharacteristicType("species",SPECIES,    CATEGORIAL_TYPE, ["homo sapiens"], [NO_UNIT]),
    # -------------- Anthropometry --------------
    CharacteristicType("height",                ANTHROPOMETRY, NUMERIC_TYPE, None, height_units),
    CharacteristicType("weight",                ANTHROPOMETRY, NUMERIC_TYPE, None, weight_units),
    CharacteristicType("bmi",                   ANTHROPOMETRY, NUMERIC_TYPE, None, bmi_units),
    CharacteristicType("body surface area",     ANTHROPOMETRY, NUMERIC_TYPE, None, body_surface_area_units),
    CharacteristicType("waist circumference",   ANTHROPOMETRY, NUMERIC_TYPE, None, waist_circumference_units),
    CharacteristicType("lean body mass",        ANTHROPOMETRY, NUMERIC_TYPE, None, lean_body_mass_units),  # fat free mass (FFM)
    CharacteristicType("percent fat",           ANTHROPOMETRY, NUMERIC_TYPE, None, percent_fat_units),     # percent body fat
    CharacteristicType("obesity index",         ANTHROPOMETRY, NUMERIC_TYPE, None, obesity_index_units),   # percent of normal body weight
    CharacteristicType("obese",                 ANTHROPOMETRY, BOOLEAN_TYPE, BOOLEAN_CHOICES, []),
    # -------------- Demography --------------
    CharacteristicType("age",       DEMOGRAPHICS, NUMERIC_TYPE,    None,                 age_unit_units),
    CharacteristicType("sex",       DEMOGRAPHICS, CATEGORIAL_TYPE, ["M", "F", MIX, NAN], []),
    CharacteristicType("ethnicity", DEMOGRAPHICS,   CATEGORIAL_TYPE,
        [NAN, "african", "afroamerican", "asian", "caucasian", "korean","hispanic", "japanese","chinese"],
        []),
    # -------------- Physiology --------------
    CharacteristicType("blood pressure", PHYSIOLOGY, NUMERIC_TYPE, None, blood_pressure_units),
    CharacteristicType("heart rate",     PHYSIOLOGY, NUMERIC_TYPE, None, heart_rate_units),
    # -------------- Organ weights --------------
    CharacteristicType("liver weight", ANTHROPOMETRY, NUMERIC_TYPE, None, [ORGAN_WEIGHT_UNIT]),
    CharacteristicType("kidney weight", ANTHROPOMETRY, NUMERIC_TYPE, None, [ORGAN_WEIGHT_UNIT]),
    CharacteristicType("muscle weight", ANTHROPOMETRY, NUMERIC_TYPE, None, [ORGAN_WEIGHT_UNIT]), # muscle mass
    CharacteristicType("fat weight", ANTHROPOMETRY, NUMERIC_TYPE, None, [ORGAN_WEIGHT_UNIT]),

    # -------------- Patient status --------------
    CharacteristicType("overnight fast",PATIENT_STATUS, BOOLEAN_TYPE,BOOLEAN_CHOICES,[]),
    CharacteristicType("fasted",        PATIENT_STATUS, NUMERIC_TYPE, None, fasted_units ),
    CharacteristicType("healthy",       PATIENT_STATUS, BOOLEAN_TYPE, BOOLEAN_CHOICES, [] ),
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
        [],
    ),
    CharacteristicType("disease duration", LIFESTYLE, NUMERIC_TYPE, None, [AMOUNT_PER_YEAR]),

    # -------------- Medication --------------
    CharacteristicType("medication", MEDICATION, BOOLEAN_TYPE, BOOLEAN_CHOICES, []),
    CharacteristicType("medication type", MEDICATION, CATEGORIAL_TYPE,
        ["diet", "metformin", "insulin", "metformin+glipizide", "aspirin", "carbon monoxide", "clozapine", "ibuprofen",
         "hydrochlorthiazide","amiloride","chlordiazepoxide","paracetamol","salbutamol","diltiazem","hemodialysis",
         "enalapril","beclometasone","spinal anaesthesia", "CCM"],
        [],
    ),
    CharacteristicType("medication amount", MEDICATION, NUMERIC_TYPE, None, []),
    CharacteristicType("oral contraceptives",MEDICATION,BOOLEAN_TYPE,BOOLEAN_CHOICES, []),
    CharacteristicType("abstinence",    STUDY_PROTOCOL,   CATEGORIAL_TYPE,
        [substance.name for substance in SUBSTANCES_DATA] +
                       ["alcohol", "smoking", "grapefruit juice", "medication", "drug", "kola nuts", "coffee","tee"],
                       abstinence_units,
    ),
    CharacteristicType(
        "consumption",
        STUDY_PROTOCOL,
        CATEGORIAL_TYPE,
        [substance.name for substance in SUBSTANCES_DATA] + ["alcohol", "smoking", "grapefruit juice", "medication", "drug", "kola nuts", "coffee","tee"],
        consumption_units,
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
        [],
    ),

    # -------------- sleeping & circadian rhythm -----------------

    CharacteristicType(
        "sleeping",
        LIFESTYLE,
        CATEGORIAL_TYPE,
        ["asleep",
         "awake"
        ],
        [],
    ),

    CharacteristicType(
        "circadian",
        LIFESTYLE,
        CATEGORIAL_TYPE,
        ["daytime",
         "nighttime"
        ],
        [],
    ),


    # -------------- Caffeine --------------
    CharacteristicType(
        "caffeine", LIFESTYLE, BOOLEAN_TYPE, BOOLEAN_CHOICES, []
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
        STUDY_PROTOCOL,
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
        CYP2D6_PHENOTYPE,
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
         CYP2D6_PHENOTYPE,
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
        "nmol/l*h": "µmol*h/l",
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
        "l/h*kg":"l/h/kg",
        "ml/h/kg": "l/h/kg",  # -> l/h/kg
        "ml/kg/min": "l/h/kg",
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
    "µg/min": None,
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
        "clearance_partial", "Partial clearance of substance. It can occure if several path are present. The pathway is encoded by the substance", clearance_norm_unit
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
        "rate_renal", "rate renal (rate)", rate_norm_unit
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
