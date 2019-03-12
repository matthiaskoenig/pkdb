import pint

ureg = pint.UnitRegistry()
# add units to pint registry
ureg.define('cups = count')
ureg.define('none = count')
ureg.define('yr = year')
ureg.define('percent = 0.01*count')
ureg.define('U = 60*10**6*mol/second')
ureg.define('IU = [activity_amount]')
ureg.define('NO_UNIT = [no_unit]')


# frequently used used unit definitions
DIMLESS = 'none'
NOUNIT = 'NO_UNIT'
ORGAN_WEIGHT_UNIT = 'g'
AMOUNT_PER_YEAR = '1/yr'
AMOUNT_PER_DAY = '1/day'


# ------------------------------------------------------------------------------
# Pktype
# ------------------------------------------------------------------------------
auc_units = [
    'g/l*hr',     # auc of concentration [g/l]
    'g/l/kg*hr',  # auc of concentration [g/l] per bodyweight
    'mol/l*hr',   # auc of concentration [mole]
    'IU/l*hr'     # auc of amount enzyme activity [activity_amount]
]

# FIXME: what is this exactly?
aumc_units = [
   'g*hr^2/l',  # area under the first moment curve of substance in mass
   'mol*hr^2/l',  # area under the first moment curve of substance in mole
   'g*hr^2/l/kg',  # area under the first moment curve per bodyweight
]

amount_units = [
    'g',
    'mol'
]

concentration_units = [
   'g/l',
   'mol/l',
   'IU/l',  # concentration of amount enzyme activity [activity_amount]
]

# ratio dimensions to units
ratio_units = [
   DIMLESS,  # all ratios are dimensionless
]

# recovery dimensions to units
recovery_units = ratio_units + [
    'mol',
    'g'
]

# clearance dimensions to units
clearance_units = [
   'l/hr',              # clearance of substance in mass
   'l/hr/kg',           # clearance of substance in mass per bodyweight
   'µmol/l/hr',          # clearance of substance in mole
   'ml/min/(1.73*m^2)',  # clearance of substance in mass per body area #todo: I dont like the norm unit
   'ml*g/IU/hr',
   'ml*µg/ µmol /hr',   # calculated: clearance no mol information on substance; dosing dimension [mass]
   'ml/µmol/hr',         # calculated: clearance no mol information on substance; dosing dimension [mass/kg]
   'ml*g /IU/hr/kg'

    # amount enzyme activity with new dimension [activity_amount]
]
# volume of distribution dimensions to units
vd_units = [
   'l',
  'l/kg',
  'l*mg/µIU',            # calculated: amount enzyme activity with new dimension [activity_amount]
  'l*mg/mmol',          # calculated: and no information of mole
  "l/mmol",       # calculated: no mol information on substance; dosing dimension [mass/kg]
  "l/IU",

]

# time dimensions to units
time_units = [
   'hr',
]

# rate dimensions to units
rate_units = [
   #'mg/kg/min', # not shure if I need this
   '1/min',
   'mg/min',
   'µmol/min/kg',
   'µmol/min',
   'µIU/min',
   'µIU/min/kg',
]


# ------------------------------------------------------------------------------
# Characteristica
# ------------------------------------------------------------------------------

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
    NOUNIT,
    "day",
]

consumption_units = [
    NOUNIT,
    '1/day',  # could be added rule to transform to mg could be added
    'mg/day',
]

disease_duration_units = [
    'year'
]

# -------------- Caffeine --------------
caffeine_amount_units = ['mg/day']

# -------------- Alcohol --------------
alcohol_abstinence_units = [NOUNIT, 'day']


# -------------- Biochemical data --------------
ALT_units = ['IU/l']
AST_units = ALT_units
albumin_units = ['g/l']
glucose_units = ['g/l', 'mol/l']
fructosamine_units = ['g/l', 'mol/l']
insulin_units = ['g/l', 'mol/l', 'IU/l']
glucagon_units = insulin_units
cholesterol_units = ['mol/l']
triglyceride_units = ['mol/l']
LDLC_units = ['mol/l']
LDLH_units = ['mol/l']
HbA1c_units = ['percent']
creatinine_clearance_units = ["ml/min", "ml/min/(1.73*m^2)"]


# ------------------------------------------------------------------------------
# Intervention
# ------------------------------------------------------------------------------
dosing_units = [
    'g',
    'g/hr',
    'g/kg',
    'mol',
    'mol/kg',
    'mol/kg/hr',
    'mIU/kg',
]

restricted_dosing_units = [
    'g',
    'g/kg',
    'mol',
    'mol/kg',
]
