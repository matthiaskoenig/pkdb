"""
To be easily extendable we do not hardcode information about characteristics in classes,
but define in some custom data structure which is referenced.


Model choices and more specifically possible categories of subject characteristics.

In the future the relationship between the characteristics could be implemented via
an ontology which represents the relationship between the differnent values.


units on CharacteristicType is an ordered iteratable, with the first unit being the default unit.

"""
from collections import namedtuple
from pint.errors import UndefinedUnitError
from .substances.substances import SUBSTANCES_DATA
from .units import ureg, DIMLESS, ORGAN_WEIGHT_UNIT, height_units, weight_units, bmi_units, body_surface_area_units, \
    waist_circumference_units, lean_body_mass_units, percent_fat_units, obesity_index_units, age_unit_units, \
    blood_pressure_units, heart_rate_units, fasted_units, AMOUNT_PER_YEAR, abstinence_units, consumption_units, \
    caffeine_amount_units, AMOUNT_PER_DAY, alcohol_abstinence_units, ALT_units, AST_units, \
    albumin_units, glucose_units, insulin_units, glucagon_units, fructosamine_units, \
    cholesterol_units, triglyceride_units, LDLC_units, LDLH_units, creatinine_clearance_units, \
    HbA1c_units, dosing_units, auc_units, ratio_units, aumc_units, clearance_units, concentration_units, \
    amount_units, vd_units, time_units, recovery_units, rate_units, disease_duration_units, restricted_dosing_units, \
    NOUNIT

CURRENT_VERSION = [1.0]
VERSIONS = [1.0]


class AbstractType(object):
    def __init__(self, key, n_units):
        self.key = key  # name
        self.n_units = n_units  # list of units to which are the normalized units. Important: Each should have a unique dimension.

    @property
    def n_p_units(self):
        """

        :return: list of norm units in the data format of pint

        """
        return [ureg(unit).u for unit in self.n_units]

    @property
    def valid_dimensions(self):
        return [unit.dimensionality for unit in self.n_p_units]

    @property
    def valid_dimensions_str(self):
        return [str(unit.dimensionality) for unit in self.n_p_units]

    @property
    def dimension_to_n_unit(self):
            return {str(n_unit_p.dimensionality): n_unit_p for n_unit_p in self.n_p_units}

    def p_unit(self, unit):
        try:
            return ureg(unit)
        except (UndefinedUnitError, AttributeError):
            if unit == "%":
                raise ValueError(f"unit: [{unit}] has to written as 'percent'")

            raise ValueError(f"unit [{unit}] is not defined in unit registry or not allowed.")

    def is_valid_unit(self, unit):
        if len(self.n_units) != 0 :
            if unit:
                return any([self.p_unit(unit).check(dim) for dim in self.valid_dimensions])
            else:
                unit_not_required2 = NOUNIT in self.n_units
                return unit_not_required2

        else:
            if unit:
                return False
            else:
                return True

    def validate_unit(self, unit):
        if not self.is_valid_unit(unit):
            msg = f"[{unit}] with dimension [{self.unit_dimension(unit)}] is not allowed. " \
                  f"For units in the category [{self.key}]"
            raise ValueError({"unit": msg,"allowed dimensions":self.valid_dimensions_str, "norm_units":self.n_units})

    def is_valid_time_unit(self, time_unit):
        return self.p_unit(time_unit).dimensionality == '[time]'

    def validate_time_unit(self, unit):
        if not self.is_valid_time_unit(unit):
            msg = f"[{unit}] with dimension [{self.unit_dimension(unit)}] is not allowed for the time units. "
            raise ValueError({"time_unit": msg})

    def norm_unit(self, unit):
        try:
            return self.dimension_to_n_unit[str(self.unit_dimension(unit))]
        except KeyError:
            raise ValueError(f"Dimension [{self.unit_dimension(unit)}] is not allowed for pktype [{self.key}]. Dimension was calculated from unit :[{unit}]")

    def unit_dimension(self, unit):
        return self.p_unit(unit).dimensionality

    def is_norm_unit(self,unit):
        return ureg(unit) in self.n_p_units

    def normalize(self, magnitude, unit):
        this_unit_p = self.p_unit(unit)
        this_norm_unit_p = self.norm_unit(unit)
        result = (magnitude * this_unit_p).to(this_norm_unit_p)
        return result


class CharacteristicType(AbstractType):
    def __init__(self, key, category, dtype, choices, n_units):
        super().__init__(key, n_units)

        self.category = category
        self.dtype = dtype
        self.choices = choices

    def is_valid_choice(self, choice):
        return choice in self.choices

    def validate_choice(self, choice):
        if choice:
            if (self.dtype == CATEGORIAL_TYPE) or (self.dtype == BOOLEAN_TYPE):
                if not self.is_valid_choice:
                    msg = f"{choice} is not part of {self.choices} for {self.key}"
                    raise ValueError({"choice": msg})
            else:
                msg = f"for category: <{self.category}> no choices are allowed. If you are trying to insert a numerical value, use keword value, mean or median"
                raise ValueError({"choice": msg})


class PharmacokineticsType(AbstractType):
    def __init__(self, key, description, n_units):
        super().__init__(key, n_units)
        self.description = description


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

        # check that allowed category
        if category not in allowed_category_dict:
            msg = f"category <{category}> is not supported for {category_class}"
            raise ValueError({"category": msg})

        # get the allowed definition
        model_categorical = allowed_category_dict[category]

        # validate_choice
        choice = data.get("choice", None)
        model_categorical.validate_choice(choice)

        # validate unit
        unit = data.get("unit", None)
        model_categorical.validate_unit(unit)

    return data


def validate_pktypes(data):
    pktype = data.get("pktype", None)

    if pktype:
        # check that allowed pktypes
        if pktype not in PK_DATA_DICT:
            msg = f"pktype <{pktype}> is not supported for pktype"
            raise ValueError({"pktype": msg})

        # get the allowed definition
        model_pktype = PK_DATA_DICT[pktype]
        # check unit
        unit = data.get("unit", None)
        model_pktype.validate_unit(unit)

        time_unit = data.get("time_unit", None)
        if time_unit:
            model_pktype.validate_time_unit(time_unit)


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
STRING_TYPE = "string"
YES = "Y"
NO = "N"
MIX = "Mixed"
NAN = "NaN"
BOOLEAN_CHOICES = [YES, NO, MIX, NAN]
TIME_NORM_UNIT = "hr"

# ---------------------------------------------------
# CharacteristicTypes
# ---------------------------------------------------
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
    "diabetes",
    "gluconeogenesis",
    "glycolysis",
    "hypoglycemia",
    "insulin secretion",
    "intravenous glucose tolerance test"
    "oral glucose tolerance test",
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
DOSING = "dosing"
LIFESTYLE = "lifestyle"
BIOCHEMICAL_DATA = "biochemical data"
HEMATOLOGY_DATA = "hematology data"
GENETIC_VARIANTS = "genetic variants"
STUDY_PROTOCOL = "study protocol"
CYP2D6_PHENOTYPE = "CYP2D6 phenotype"


CHARACTERISTIC_DATA = [
    # -------------- Species --------------
    CharacteristicType("species", SPECIES,    CATEGORIAL_TYPE, ["homo sapiens"], []),
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
    CharacteristicType("disease duration", LIFESTYLE, NUMERIC_TYPE, None, disease_duration_units),

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
                       n_units=abstinence_units),
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
        ["asleep", "awake"],
        [],
    ),

    CharacteristicType(
        "circadian",
        LIFESTYLE,
        CATEGORIAL_TYPE,
        ["daytime", "nighttime"],
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
        caffeine_amount_units,
    ),
    CharacteristicType(
        "caffeine amount (beverages)", LIFESTYLE, NUMERIC_TYPE, None, [AMOUNT_PER_DAY]
    ),
    # -------------- Smoking --------------
    CharacteristicType(
        "smoking", LIFESTYLE, BOOLEAN_TYPE, BOOLEAN_CHOICES, []
    ),
    CharacteristicType(
        "smoking amount (cigarettes)", LIFESTYLE, NUMERIC_TYPE, None, [AMOUNT_PER_DAY]
    ),
    CharacteristicType(
        "smoking amount (packyears)", LIFESTYLE, NUMERIC_TYPE, None, ["yr"]
    ),
    CharacteristicType(
        "smoking duration (years)", LIFESTYLE, NUMERIC_TYPE, None, ["yr"]
    ),
    # -------------- Alcohol --------------
    CharacteristicType(
        "alcohol", LIFESTYLE, BOOLEAN_TYPE, BOOLEAN_CHOICES, []
    ),
    CharacteristicType(
        "alcohol amount", LIFESTYLE, NUMERIC_TYPE, None, [DIMLESS]
    ),
    CharacteristicType(
        "alcohol abstinence",
        STUDY_PROTOCOL,
        BOOLEAN_TYPE,
        BOOLEAN_CHOICES,
        alcohol_abstinence_units,
    ),
    # -------------- Biochemical data --------------
    CharacteristicType(
        "ALT", BIOCHEMICAL_DATA, NUMERIC_TYPE, None, ALT_units
    ),
    CharacteristicType(
        "AST", BIOCHEMICAL_DATA, NUMERIC_TYPE, None, AST_units
    ),
    CharacteristicType(
        "albumin", BIOCHEMICAL_DATA, NUMERIC_TYPE, None, albumin_units,
    ),
    CharacteristicType(
        "glucose", BIOCHEMICAL_DATA, NUMERIC_TYPE, None, glucose_units,
    ),
    CharacteristicType(
        "fructosamine", BIOCHEMICAL_DATA, NUMERIC_TYPE, None, fructosamine_units,
    ),
    CharacteristicType(
        "insulin", BIOCHEMICAL_DATA, NUMERIC_TYPE, None, insulin_units,
    ),
    CharacteristicType(
        "glucagon", BIOCHEMICAL_DATA, NUMERIC_TYPE, None, glucagon_units,
    ),
    CharacteristicType(
        "cholesterol", BIOCHEMICAL_DATA, NUMERIC_TYPE, None, cholesterol_units,
    ),
    CharacteristicType(
        "triglyceride", BIOCHEMICAL_DATA, NUMERIC_TYPE, None, triglyceride_units,
    ),
    CharacteristicType(
        "LDL-C", BIOCHEMICAL_DATA, NUMERIC_TYPE, None, LDLC_units,
    ),
    CharacteristicType(
        "LDL-H", BIOCHEMICAL_DATA, NUMERIC_TYPE, None, LDLH_units,
    ),
    CharacteristicType(
        "HbA1c", BIOCHEMICAL_DATA, NUMERIC_TYPE, None, HbA1c_units,
    ),
    CharacteristicType(
        "creatinine_clearance", BIOCHEMICAL_DATA, NUMERIC_TYPE, None, creatinine_clearance_units,
    ),

    # --------------Genetic variants --------------
    CharacteristicType(
        "genetics",
        GENETIC_VARIANTS,
        CATEGORIAL_TYPE,
        ["CYP2D6 duplication", "CYP2D6 wild type", "CYP2D6 poor metabolizer"],
        [],
    ),
    CharacteristicType(
        "phenotype",
        CYP2D6_PHENOTYPE,
        CATEGORIAL_TYPE,
        ["PM","IM","EM","UM"],
        [],
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
        [],
    ),
    CharacteristicType(
        "metabolic ratio",
         CYP2D6_PHENOTYPE,
         NUMERIC_TYPE,
        None,
        [DIMLESS],
    ),

]

CHARACTERISTIC_DTYPE = {item.key: item.dtype for item in CHARACTERISTIC_DATA}
CHARACTERISTIC_CATEGORIES = set([item.key for item in CHARACTERISTIC_DATA])
CHARACTERISTIC_CATEGORIES_UNDERSCORE = set( [c.replace(" ", "_") for c in CHARACTERISTIC_CATEGORIES])
CHARACTERISTIC_DICT, CHARACTERISTIC_CHOICES = dict_and_choices(CHARACTERISTIC_DATA)


# ---------------------------------------------------
# Interventions
# ---------------------------------------------------
INTERVENTION_ROUTE = [
    "iv",  # intravenous
    "intramuscular",
    "oral",
    "rectal",
]
INTERVENTION_APPLICATION = [
    "constant infusion",
    "multiple dose",
    "single dose",
    "variable infusion",
]
INTERVENTION_FORM = [
    "capsule",
    "tablet",
    "solution",
    NAN
]
INTERVENTION_APPLICATION_CHOICES = create_choices(INTERVENTION_APPLICATION)
INTERVENTION_ROUTE_CHOICES = create_choices(INTERVENTION_ROUTE)
INTERVENTION_FORM_CHOICES = create_choices(INTERVENTION_FORM)


INTERVENTION_DATA = [
    CharacteristicType("dosing", DOSING, NUMERIC_TYPE,
                       None, dosing_units),

    CharacteristicType("qualitative_dosing", DOSING, NUMERIC_TYPE,
                       None, dosing_units + [NOUNIT]),  # dosing with missing value or time

    CharacteristicType("smoking cessation", LIFESTYLE, NUMERIC_TYPE,
                       None, [DIMLESS]),
    CHARACTERISTIC_DICT["medication type"],
    CHARACTERISTIC_DICT["metabolic challenge"],
    CHARACTERISTIC_DICT["abstinence"],
    CHARACTERISTIC_DICT["smoking"],
    CHARACTERISTIC_DICT["oral contraceptives"],
    CHARACTERISTIC_DICT["sleeping"],
    CHARACTERISTIC_DICT["circadian"],
]
INTERVENTION_DICT, INTERVENTION_CHOICES = dict_and_choices(INTERVENTION_DATA)

# ---------------------------------------------------
# Output
# ---------------------------------------------------
OUTPUT_TISSUE_DATA = [
    "plasma",
    "saliva",
    "serum",
    "spinal fluid",
    "urine",
    "saliva/plasma",  # this is not a good solution
    "breath"
]
OUTPUT_TISSUE_DATA_CHOICES = create_choices(OUTPUT_TISSUE_DATA)


# ---------------------------------------------------
# Pharmacokinetics data
# ---------------------------------------------------

PK_DATA = [
    PharmacokineticsType(
        "auc_inf",
        "Area under the curve (AUC), extrapolated until infinity.",
        auc_units,
    ),
    PharmacokineticsType(
        "auc_end",
        "Area under the curve (AUC), until last time point. "
        "Time period is required for calculation.",
        auc_units,
    ),
    PharmacokineticsType(
        "auc_relative",
        "Relative area under the curve (AUC), AUC of a substance relative "
        "to other measured metabolites",
        ratio_units,
    ),
    PharmacokineticsType(
        "aumc_inf",
        "Area under first moment curve (AUMC), extrapolated until infinity.",
        aumc_units,
    ),
    PharmacokineticsType(
        "amount", "Amount of substance.", amount_units
    ),
    PharmacokineticsType(
        "cum_amount",
        "Cumulative amount of substance. Time period is required for "
        "calculation.",
        amount_units,
    ),
    PharmacokineticsType(
        "concentration",
        "Concentration of substance.", concentration_units
    ),
    PharmacokineticsType(
        "concentration_unbound",
        "Concentration of unbound substance.", concentration_units
    ),
    PharmacokineticsType(
        "ratio", "Ratio between substances.", ratio_units
    ),
    PharmacokineticsType(
        "clearance", "Total/apparent clearance of given substance. "
                     "If the clearance is based on the unbound substance use "
                     "clearance_unbound. If the clearance refers to renal "
                     "clearance use clearance_renal.", clearance_units
    ),
    PharmacokineticsType(
        "clearance_unbound", "Clearance of unbound substance.", clearance_units
    ),
    PharmacokineticsType(
        "clearance_partial", "Partial clearance of substance. It can occure if "
                             "several path are present. The pathway is encoded "
                             "by the substance", clearance_units
    ),
    PharmacokineticsType(
        "clearance_intrinsic", "Intrinsic clearance of substance.", clearance_units
    ),
    PharmacokineticsType(
        "clearance_renal", "Renal clearance of given substance.", clearance_units
    ),
    PharmacokineticsType(
        "vd", "Volume of distribution. "
        "If the volume of distribution is calculated with the unbound "
              "substance use vd_unbound.", vd_units
    ),
    PharmacokineticsType(
        "vd_unbound", "Volume of distribution for unbound substance.", vd_units
    ),
    PharmacokineticsType(
        "thalf", "Elimination half-life for substance.", time_units
    ),
    PharmacokineticsType(
        "tmax", "Time of maximum for substance.", time_units),
    PharmacokineticsType(
        "oro-cecal transit time",
        "The transit time was taken as the time when breath hydrogen "
        "excretion increased to above twice the baseline value.", time_units),
    PharmacokineticsType(
        "mrt",
        "Mean residence time (MRT). MRT = AUMC/AUC",
        time_units,
    ),
    PharmacokineticsType(
        "cmax", "Maximum concentration for given substance.",
        concentration_units
    ),
    PharmacokineticsType(
        "kel", "Elimination rate for given substance.", rate_units
    ),
    PharmacokineticsType(
        "kabs", "Absorption rate for given substance.", rate_units
    ),
    PharmacokineticsType(
        "thalf_absorption", "Absorption half-life substance.", time_units
    ),
    PharmacokineticsType(
        "fraction_absorbed",
        "Fraction absorbed of given substance (bioavailability).", ratio_units
    ),
    PharmacokineticsType(
        "plasma_binding",
        "Plasma binding of given substance (see also fraction unbound).",
        ratio_units
    ),
    PharmacokineticsType(
        "fraction_unbound",
        "Unbound fraction of given substance (see also plasma_binding).",
        ratio_units
    ),
    PharmacokineticsType(
        "recovery", "Fraction recovered of given substance.", recovery_units
    ),
    PharmacokineticsType(
        "egp", "endogenous glucose production (rate)", rate_units
    ),
    PharmacokineticsType(
        "ra", "rate appearance (rate)", rate_units
    ),
    PharmacokineticsType(
        "rd", "rate disappearance (rate)", rate_units
    ),
    PharmacokineticsType(
        "rate_cycling", "rate cycling (rate)", rate_units
    ),
    PharmacokineticsType(
        "rate_secretion", "rate secretion (rate)", rate_units
    ),
    PharmacokineticsType(
        "rate_renal", "rate renal (rate)", rate_units
    ),
    PharmacokineticsType(
        "Matsuda index", "Matsuda index", [DIMLESS]
    ),
    PharmacokineticsType(
        "QUICKI", "quantitative insulin sensitivity check index", [DIMLESS]
    ),
    PharmacokineticsType(
        "HOMA-IR",
        "homeostatic model assessment for insulin resistance", [DIMLESS]
    ),
    PharmacokineticsType(
        "Insulinogenic index", "Insulinogenic index", [DIMLESS]
    ),
    PharmacokineticsType(
        "Oral disposition index", "Oral disposition index", [DIMLESS]
    ),
]
PK_DATA_DICT, PK_DATA_CHOICES = dict_and_choices(PK_DATA)


DOSING_RESTRICTED = PharmacokineticsType(
    "restricted dosing",
    "subset of dosing which can be used to calculate pharmacokinetics "
    "parameter", restricted_dosing_units
)
