"""Unit definitions."""

import pint

# Units (keep synchronized with pkdb.units)
ureg = pint.UnitRegistry()
ureg.define("cups = count")
ureg.define("beverages = count")
ureg.define("none = count")
ureg.define("percent = 0.01*count")
ureg.define("IU = [activity_amount]")
ureg.define("NO_UNIT = [no_unit]")
ureg.define("arbitrary_unit = [arbitrary_unit]")


DIMENSIONLESS = "dimensionless"
NO_UNIT = "NO_UNIT"
AUC_UNITS = [
    "g/l*hr",  # auc of concentration [g/l]
    "g/l/kg*hr",  # auc of concentration [g/l] per bodyweight
    "mol/l*hr",  # auc of concentration [mole]
    "IU/l*hr",  # auc of amount enzyme activity [activity_amount]
]
AUC_DIV_UNITS = ["hr/l", "hr/l/kg"]
AUMC_UNITS = [
    "g*hr^2/l",  # area under the first moment curve of substance in mass
    "mol*hr^2/l",  # area under the first moment curve of substance in mole
    "g*hr^2/l/kg",  # area under the first moment curve per bodyweight
]
AMOUNT_UNITS = ["g", "mol"]
CONCENTRATION_UNITS = [
    "g/l",
    "mol/l",
    "IU/l",  # concentration of amount enzyme activity [activity_amount]
]
CONCENTRATION_PER_DOSE_UNITS = [
    "1/l",
    "mol/l/g",
    "IU/l/g",
]


RATIO_UNITS = [
    DIMENSIONLESS,
]
CLEARANCE_UNITS = [
    "l/hr",
    "l/hr/kg",
    "µmol/l/hr",
    "ml/min/(1.73*m^2)",
    "ml*g/IU/hr",
    "ml*µg/µmol/hr",
    "ml/µmol/hr",
    "ml*g/IU/hr/kg",  # activity_amount
]
FLOW_UNITS = ["ml/hr"]
VD_UNITS = [
    "l",
    "l/kg",
    "l/(1.73*m^2)",
    "l*mg/µIU",
    "l*mg/mmol",
    "l/mmol",
    "l/IU",  # activity_amount
]
TIME_UNITS = [
    "hr",
]
RATE_UNITS = [
    "1/min",
    "mg/min",
    "mg/min/m^2",
    "µmol/min/kg",
    "µmol/min",
    "µIU/min",
    "µIU/min/kg",
]

DOSING_UNITS = [
    "g",
    "g/hr",
    "g/kg",
    "g/kg/hr",
    "g/hr/m^2",
    "g/(1.73*m^2)",
    "mol",
    "mol/hr",
    "mol/kg",
    "mol/kg/hr",
    "IU",
    "IU/kg",
    "IU/m^2",
    "IU/kg/hr",
    "IU/m^2/hr",
    "ml",
    "ml/hr",
    # FIXME: We proably need  different normalization strategy or we need an extra MeasurementType
    # Validation: All units need a unique dimension within 1 measurement type.
    # 'count', this has the same dimension as 'g/kg' (per bodyweight).
    # If we uncomment this 'g/kg' will be normalized to 'count'.
    # 'count/hr',  this has the same dimension as 'g/kg/hr' (per bodyweight).
    # If we uncomment this 'g/kg/hr' will be normalized to count.
    "Ci",
    "Ci/hr",
    "Bq",
    "Bq/hr",
]

RESTRICTED_DOSING_UNITS = [
    "g",
    "g/kg",
    "mol",
    "mol/kg",
]

PRESSURE_UNITS = ["mmHg"]
PRESSURE_AUC_UNITS = ["mmHg*hr"]

SVR_UNIT = "dynes/sec/(cm^-5)"
