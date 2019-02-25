from collections import namedtuple
import pint

ureg = pint.UnitRegistry()
# add units to pint registry
ureg.define('cups = count')
ureg.define('percent = 0.01*count')
ureg.define('U = 60*10**6*mol/second')


# frequently used used unit definitions
NO_UNIT ='dimensionless'
ORGAN_WEIGHT_UNIT = 'g'
AMOUNT_PER_YEAR ='1/yr'
AMOUNT_PER_DAY = '1/day'

#-----------------------------------------------------------------------------------------------------------------------
# Pktype: allowed dimensions and norm units
#-----------------------------------------------------------------------------------------------------------------------

# auc dimensions to
auc_units = [
    'mg*hr/l',     # auc of substance in mass
    'mg*hr/l/kg',  # auc of substance in mass per bodyweight
    'µmol*hr/l',   # auc of substance in mole
    'µU/hr/l',     # auc of enzyme activity
]

# auc dimensions to
aumc_units = [
   'mg*hr^2/l',  # area under the first moment curve of substance in mass
   'µmol*hr^2/l',# area under the first moment curve of substance in mole
   'mg*hr^2/l/kg', # area under the first moment curve per bodyweight
   'µU/hr^2/l',  # area under the first moment curve of enzyme activity
]


# concentration dimensions to units
concentration_units = [
   'mg/l',   # concentration of substance in mass
   'µmol/l', # concentration of substance in mole
   'µU/l',   # concentration of enzyme activity
   'ng/g',   #todo: check reason for this unit
]

# ratio dimensions to units
ratio_units = [
   'dimensionless',  # all ratios are dimensionless
]

# recovery dimensions to units
recovery_units = ratio_units + [
   'µmol',
]

# clearance dimensions to units
clearance_units = [
   'ml/hr',              # clearance of substance in mass
   'l/hr/kg',            # clearance of substance in mass per bodyweight
   'µmol/l/hr',          # clearance of substance in mole
   'ml/min/(1.73*m^2)',  # clearance of substance in mass per area #todo: I dont like the norm unit
]
# volume of distribution dimensions to units
vd_units = [
   'l',
  'l/kg',
]

# time dimensions to units
time_units = [
   'hr',
]

# rate dimensions to units
rate_units = [
   'mg/kg/min',
   'mg/min',
   'µmol/min/kg',
   'µmol/min',
   'µU/min',
   'µU/min/kg',
]



#-----------------------------------------------------------------------------------------------------------------------
# Characteristica: allowed dimensions and norm units
#-----------------------------------------------------------------------------------------------------------------------
# -------------- Species --------------
# species: no unit

# -------------- Anthropometry --------------
# height dimensions to units
height_units = [
   'm',
]
# weight dimensions to units
weight_units = [
   'kg',
]
#bmi dimensions to units
bmi_units = [
   'kg/m^2',
]
#body dimensions to units
body_surface_area_units = [
   'm^2',
]

waist_circumference_units = [
   'cm',
]

# fat free mass (FFM)
lean_body_mass_units = [
   'kg',
]

percent_fat_units = [
   'percent',
]

obesity_index_units = [
   'percent',
]
# obese: no unit

# -------------- Demography --------------
age_unit_units = [
   'yr',
]
# sex: no unit
# ethnicity: no unit
blood_pressure_units = [
   'mmHg',
]

heart_rate_units = [
   '1/s',
]

# -------------- Patient status --------------
fasted_units = [
   'hr',
]

# -------------- Medication --------------
abstinence_units = [
    NO_UNIT,
    "day"
],

consumption_units = [
    '1/day', # could be added rule to transform to mg could be added
    'mg/day',
]

# -------------- Caffeine --------------

caffeine_amount_units = ['mg/day',]
# -------------- Alcohol --------------

alcohol_abstinence_units = [NO_UNIT,'day']
# -------------- Biochemical data --------------
_ALT_abstinence_units = _AST_abstinence_units  = ['U/l']
_albumin_abstinence_units = ['g/dl']
_glucose_abstinence_units = ['g/dl']
_insulin_abstinence_units = ['g/dl']
_glucagon_abstinence_units = ['g/dl']
_cholesterol_abstinence_units = ['mmol/l']
_triglyceride_abstinence_units = ['mmol/l']
_LDL_C_abstinence_units = ['mmol/l']
_LDL_H_abstinence_units = ['mmol/l']
_HbA1c_abstinence_units = ['percent']


#-----------------------------------------------------------------------------------------------------------------------
# Intervention: allowed dimensions and norm units
#-----------------------------------------------------------------------------------------------------------------------

# -------------- Dosing --------------
_dosing_units = [
   'mg',
   'mg/kg',
   'pmol/kg',
   'pmol/kg/min',
   'mg/day',
   'nmol',
]

