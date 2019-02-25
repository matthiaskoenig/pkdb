from collections import namedtuple
import pint

ureg = pint.UnitRegistry()

# add units to pint registry
ureg.define('cups = count')
ureg.define('percent = 0.01*count')
ureg.define('U = 60*10**6*mol/second')

# dimensions to unit mapping
#DimToUnit = namedtuple("DimToUnit", ["dim", "norm_unit"])


class DimToUnit(object):
    def __init__(self, norm_unit):
        self.norm_unit = norm_unit
        self.norm_unit_p = ureg(norm_unit)
        self.dim = self.norm_unit_p.dimensionality



# frequently used used unit definitions
NO_UNIT = DimToUnit("dimensionless")
ORGAN_WEIGHT = DimToUnit("g")
AMOUNT_PER_YEAR = DimToUnit("count/yr")
AMOUNT_PER_DAY =  DimToUnit("count/day")

#-----------------------------------------------------------------------------------------------------------------------
# Pktype: allowed dimensions and norm units
#-----------------------------------------------------------------------------------------------------------------------

# auc dimensions to
_auc_dim_to_units = [
    DimToUnit("mg*hr/l"),     # auc of substance in mass
    DimToUnit("mg*hr/l/kg"),  # auc of substance in mass per bodyweight
    DimToUnit("µmol*hr/l"),   # auc of substance in mole
    DimToUnit("µU/hr/l"),     # auc of enzyme activity
]

# auc dimensions to
_aumc_dim_to_units = [
    DimToUnit('mg*hr^2/l'),  # area under the first moment curve of substance in mass
    DimToUnit('µmol*hr^2/l'),# area under the first moment curve of substance in mole
    DimToUnit("mg*hr^2/l/kg"), # area under the first moment curve per bodyweight
    DimToUnit('µU/hr^2/l'),  # area under the first moment curve of enzyme activity
]


# concentration dimensions to units
_concentration_dim_to_units = [
    DimToUnit('mg/l'),   # concentration of substance in mass
    DimToUnit('µmol/l'), # concentration of substance in mole
    DimToUnit('µU/l'),   # concentration of enzyme activity
    DimToUnit('ng/g'),   #todo: check reason for this unit
]

# ratio dimensions to units
_ratio_dim_to_units = [
    DimToUnit('dimensionless'),  # all ratios are dimensionless
]

# recovery dimensions to units
_recovery_dim_to_units = _ratio_dim_to_units + [
    DimToUnit('µmol'),
]

# clearance dimensions to units
_clearance_dim_to_units = [
    DimToUnit('ml/hr'),              # clearance of substance in mass
    DimToUnit('l/hr/kg'),            # clearance of substance in mass per bodyweight
    DimToUnit('µmol/l/hr'),          # clearance of substance in mole
    DimToUnit('ml/min/(1.73*m^2)'),  # clearance of substance in mass per area #todo: I dont like the norm unit
]
# volume of distribution dimensions to units
_vd_dim_to_units = [
    DimToUnit('l'),
    DimToUnit( 'l/kg'),
]

# time dimensions to units
_time_dim_to_units = [
    DimToUnit('hr'),
]

# rate dimensions to units
_rate_dim_to_units = [
    DimToUnit("mg/kg/min"),
    DimToUnit("mg/min"),
    DimToUnit("µmol/min/kg"),
    DimToUnit("µmol/min"),
    DimToUnit("µU/min"),
    DimToUnit("µU/min/kg"),
]

# to dictionaries
auc_dim_to_units = {unit.dim for unit in _auc_dim_to_units}
aumc_dim_to_units = {unit.dim for unit in _aumc_dim_to_units}
concentration_dim_to_units = {unit.dim for unit in _concentration_dim_to_units}
ratio_dim_to_units = {unit.dim for unit in _ratio_dim_to_units}
recovery_dim_to_units = {unit.dim for unit in _recovery_dim_to_units}
clearance_dim_to_units = {unit.dim for unit in _clearance_dim_to_units}
vd_dim_to_units = {unit.dim for unit in _vd_dim_to_units}
time_dim_to_units = {unit.dim for unit in _time_dim_to_units}
rate_dim_to_units = {unit.dim for unit in _rate_dim_to_units}

#-----------------------------------------------------------------------------------------------------------------------
# Characteristica: allowed dimensions and norm units
#-----------------------------------------------------------------------------------------------------------------------
# -------------- Species --------------
# species: no unit

# -------------- Anthropometry --------------
# height dimensions to units
_height_dim_to_units = [
    DimToUnit("m"),
]
# weight dimensions to units
_weight_dim_to_units = [
    DimToUnit("kg"),
]
#bmi dimensions to units
_bmi_dim_to_units = [
    DimToUnit("kg/m^2"),
]
#body dimensions to units
_body_surface_area_dim_to_units = [
    DimToUnit("m^2"),
]

_waist_circumference_dim_to_units = [
    DimToUnit("cm"),
]

# fat free mass (FFM)
_lean_body_mass_dim_to_units = [
    DimToUnit("kg"),
]

_percent_fat_dim_to_units = [
    DimToUnit("percent"),
]

_obesity_index_dim_to_units = [
    DimToUnit("percent"),
]
# obese: no unit

# -------------- Demography --------------
_age_unit_dim_to_units = [
    DimToUnit("yr"),
]
# sex: no unit
# ethnicity: no unit
_blood_pressure_dim_to_units = [
    DimToUnit("mmHg"),
]

_heart_rate_dim_to_units = [
    DimToUnit("1/s"),
]

# -------------- Patient status --------------
_fasted_dim_to_units = [
    DimToUnit("hr"),
]

# -------------- Medication --------------
_consumption_dim_to_units = [
    DimToUnit("1/day"), # could be added rule to transform to mg could be added
    DimToUnit("mg/day"),
]

# -------------- Caffeine --------------

_caffeine_amount_dim_to_units = [
    DimToUnit("mg/day"),
]
# -------------- Alcohol --------------

_alcohol_abstinence_dim_to_units = [
    NO_UNIT,
    DimToUnit(norm_unit="day"),
]
# -------------- Biochemical data --------------
_ALT_abstinence_dim_to_units = _AST_abstinence_dim_to_units  = [ DimToUnit("U/l")]
_albumin_abstinence_dim_to_units = [ DimToUnit("g/dl")]
_glucose_abstinence_dim_to_units = [ DimToUnit("g/dl")]
_insulin_abstinence_dim_to_units = [ DimToUnit("g/dl")]
_glucagon_abstinence_dim_to_units = [ DimToUnit("g/dl")]
_cholesterol_abstinence_dim_to_units = [ DimToUnit("mmol/l")]
_triglyceride_abstinence_dim_to_units = [ DimToUnit("mmol/l")]
_LDL_C_abstinence_dim_to_units = [ DimToUnit("mmol/l")]
_LDL_H_abstinence_dim_to_units = [ DimToUnit("mmol/l")]
_HbA1c_abstinence_dim_to_units = [ DimToUnit("percent")]


#-----------------------------------------------------------------------------------------------------------------------
# Intervention: allowed dimensions and norm units
#-----------------------------------------------------------------------------------------------------------------------

# -------------- Dosing --------------
_dosing_dim_to_units = [
    DimToUnit(norm_unit='mg'),
    DimToUnit(norm_unit='mg/kg'),
    DimToUnit([mass]', norm_unit='pmol/kg'),
    DimToUnit([mass] / [time]', norm_unit='pmol/kg/min'),
    DimToUnit([time]', norm_unit='mg/day'),
    DimToUnit(norm_unit='nmol'),

]

dosing_dim_to_units = {unit.dim for unit in _dosing_dim_to_units}
