from collections import namedtuple
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
DIMLESS = 'dimensionless'
NOUNIT = 'NO_UNIT'
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
    #'µU/hr/l',     # auc of enzyme activity
    'µIU*hr/l'     # auc of amount enzyme activity with new dimension [activity_amount]
]

# auc dimensions to
aumc_units = [
   'mg*hr^2/l',  # area under the first moment curve of substance in mass
   'µmol*hr^2/l',# area under the first moment curve of substance in mole
   'mg*hr^2/l/kg', # area under the first moment curve per bodyweight
   #'µU/hr^2/l',  # area under the first moment curve of enzyme activity
]

# amount of substance
amount_units = [
    'mg',
    'µmol'
]
# concentration dimensions to units
concentration_units = [
   'mg/l',   # concentration of substance in mass
   'µmol/l', # concentration of substance in mole
   'µIU/l',   # concentration of amount enzyme activity with new dimension [activity_amount]
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
   'ml/min/(1.73*m^2)',  # clearance of substance in mass per body area #todo: I dont like the norm unit
   'ml*g/IU/hr',
   'ml*µg/ µmol /hr',

    # amount enzyme activity with new dimension [activity_amount]
]
# volume of distribution dimensions to units
vd_units = [
   'l',
  'l/kg',
  'l*mg/µIU',            # calculated: amount enzyme activity with new dimension [activity_amount]
  'l*mg/mmol'            # calculated: and no information of mole
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
   #'µU/min',
   #'µU/min/kg',
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
    NOUNIT,
    "day",
]

consumption_units = [
    '1/day', # could be added rule to transform to mg could be added
    'mg/day',
]

disease_duration_units = [
    'year'
]

# -------------- Caffeine --------------

caffeine_amount_units = ['mg/day',]
# -------------- Alcohol --------------

alcohol_abstinence_units = [DIMLESS, 'day']
# -------------- Biochemical data --------------
ALT_abstinence_units = AST_abstinence_units  = ['IU/l']
albumin_abstinence_units = ['g/dl']
glucose_abstinence_units = ['g/dl']
insulin_abstinence_units = ['g/dl']
glucagon_abstinence_units = ['g/dl']
cholesterol_abstinence_units = ['mmol/l']
triglyceride_abstinence_units = ['mmol/l']
LDL_C_abstinence_units = ['mmol/l']
LDL_H_abstinence_units = ['mmol/l']
HbA1c_abstinence_units = ['percent']


#-----------------------------------------------------------------------------------------------------------------------
# Intervention: allowed dimensions and norm units
#-----------------------------------------------------------------------------------------------------------------------

# -------------- Dosing --------------
dosing_units = [
   'mg',
   'mg/kg',
   'pmol/kg',
   'pmol/kg/min',
   'mg/day',
   'nmol',
]

restricted_dosing_units = [
   'mg',
   'mg/kg',
   'pmol/kg',
   'nmol',
]