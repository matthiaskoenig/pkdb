"""
Model choices and more specifically possible categories of subject characteristics.
"""
from enum import Enum, IntEnum
from itertools import chain
#####################
#Abstract Catergories

class ChoiceEnum(Enum):

    @classmethod
    def choices(cls):
        return tuple((x.name, x.value) for x in cls)

BOOLEAN_CHOICES = (
    (0,"Yes"),
    (1,"No")
)

NULL_BOOLEAN_CHOICE = BOOLEAN_CHOICES + (2,"NULL")


#####################
#Study Choices
KEY_WORD_CHOICES = ()
#####################
#Characteristics

class BodyParams(ChoiceEnum):
    Height = "height"
    BODYWEIGHT = "bodyweight"

class Sex(ChoiceEnum):
    MALE = 'male'
    FEMALE = 'female'

class Species(ChoiceEnum):
    HOMOSAPIEN = "Home Sapiens"

class Ethnicitiy(ChoiceEnum):
    ASIAN = "asian"
    CAUCASIAN = "caucasian"
    AFRICAN = "african"
    AFROAMERICAN = "afroamerican"

class Health(ChoiceEnum):
    HEALTHY = "healthy"
    NONHEALTHY = "non-healthy"

class Smoking(ChoiceEnum):
    SMOKING = "smoking"
    NONSMOKING = "non-smoking"

characteristics_dict = {"sex":Sex,
                   "ethnicity":Ethnicitiy,
                   "health":Health,
                   "smoking":Smoking,
                   "body_params": BodyParams,
                   "species":Species}


characteristics_types = {}
for k,v in characteristics_dict.items():
    for vv in v:
        characteristics_types[vv.value] = k

All_Characteristics = ChoiceEnum("All Characteristics", [(i.name, i.value) for i in chain(*characteristics_dict.values)])






INTERVENTION_CHOICES = (
     (1, "Other"),
     (2, "Dynamic Individual"),
     (3, "Dynamic Group"),
     (4, "Static Single"),
     (5, "Static Multiple"),
     )
#
# SPECIES_CHOICES = (
#     (1, "Other"),
#     (2, "Homo Sapiens"),
#     )
#
# CHARATERISTIC_CHOICES = (
#     (1, "Other"),
#     (2, "Antropometrie"),
#     (3, "Life Style"),
#     (4, "Genetics")
# )
# #####################
# # Subject categories
# CHARATERISTIC_CATEGORIES = (
#     #(1, "Other"),
#     (2,"Health"),
#     (3,"Sex"),
#     (4,"Smoking"),
#     (5,"Ethnicity"),
# )
#
# SEX_CATEGORIES = (
#     (1,"Male"),
#     (2,"Female"),
# )
#
# ETHNICITY_CATEGORIES = (
#     (1,"Asian"),
#     (2,"Afroamerican"),
#     (3,"American"),
#     (4,"Caucasian"),
# )
#
# HEALTH_CATEGORIES = BOOLEAN_CHOICES
# SMOKING_CATEGORIES = BOOLEAN_CHOICES
#
#
# SUBJECT_CATEGORIES = {"health":HEALTH_CATEGORIES,
#                       "smoking":SMOKING_CATEGORIES,
#                       "sex": SEX_CATEGORIES,
#                       "ethnicity": ETHNICITY_CATEGORIES,
#                       }

