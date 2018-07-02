"""
Describes subjects which participated in a study.
This can be individuals or groups.
"""
from django.db import models

from ..studies.models import Intervention,Study
from ..behaviours import Sidable, Describable
from ..categoricals import ChoiceEnum, All_Characteristics, characteristics_types
from ..utils import CHAR_MAX_LENGTH
#############################################################

#New Approach
#General Categorical
# class CharacteristicType(models.Model):
#     name = models.CharField(max_length=CHAR_MAX_LENGTH)
#     pass
#
# class Characteristic(models.Model):
#     name = models.CharField(max_length=CHAR_MAX_LENGTH)
#     type = models.ForeignKey(CharacteristicType, on_delete=False)
#     #unit = models.CharField(max_length=CHAR_MAX_LENGTH)
#
#
#
# class Category(models.Model):
#     name = models.CharField(max_length=CHAR_MAX_LENGTH)
#     characteristic = models.ForeignKey(Characteristic, on_delete=False)
#
##############################################################


class Group(Sidable,models.Model):
    study = models.ForeignKey(Study, on_delete=True)


class GroupCharacteristic(Sidable,models.Model):
    name = models.CharField(choices=All_Characteristics.choices(), max_length=CHAR_MAX_LENGTH)
    #######################
    #statistical properties
    value = models.FloatField(null=True,blank=True)
    mean = models.FloatField(null=True,blank=True)
    min = models.FloatField(null=True,blank=True)
    max = models.FloatField(null=True,blank=True)
    std = models.FloatField(null=True,blank=True)
    count = models.IntegerField()
    ########################
    unit = models.CharField(choices=All_Units.choices(),max_length=CHAR_MAX_LENGTH)
    group = models.ForeignKey(Group,on_delete=True)


    def type(self):
        return characteristics_types[self.name]


##########################################################################################

class CharacteristicValue(models.Model):
    count = models.IntegerField(null=True)
    mean = models.FloatField(null=True)

class SubjectTag(Sidable, Describable, models.Model):
    pass


class Characteristic(Sidable, models.Model):
    """ Property which the individual or group has, examples are age, weight.
    These can be either
    - categorial
    - continuous

    """
    class Type(ChoiceEnum):
        OTHER = 'other'
        ANTROPOMETRIE = 'antropometrie'
        LIFE_STYLE = 'life style'
        GENETICS = 'genetics'

    count = models.IntegerField()     #count (optional: either subset, or all) # can be done via through
    type = models.CharField(choices=Type.choices())

    class Meta:
        abstract = True


class CharacteristicCategorial(Characteristic):
    """
    - sex (M/F)
    - healthy (healthy/non-healthy)
    - ethnicity (Asian, Afroamerican, African, Caucasian)
    """
    class Category(ChoiceEnum):

            Health = "health"
            Sex = "sex"
            Smoking = "smoking"
            Ethnicity = "ethnicity"

    #category = models.CharField(choices=Category.choices())
    name = models.CharField(choices=Category.choices())
    value = models.CharField(choices=All_Characteristics.choices())
###############################################################

class CharacteristicContinuous(Characteristic):
    """
    -
    """

    class Category(ChoiceEnum):
        Age = "age"
        BodyWeight = "bodyweight"
        Height = "height"



    name = models.CharField(choices=Category.choices())
    #value = models.FloatField()


class Value(models.Model):

    #category/keyword/type (age, bodyweight, height, ...)
    models.ForeignKey(CharacteristicContinuous, on_delete=True)
    n (=1) # ?
    mean
    unit


class GroupValue():
    """
    can be single or group value
    """
    n
    mean
    median
    sd (standard deviation)
    se (standard error)
    min
    max
    cv
    unit






class CharacteristicRange(Characteristic):
    start = models.FloatField()
    end = models.FloatField()



class Individual(Sidable, models.Model):
    specie = models.IntegerField(choices=SPECIES_CHOICES)
    tags = models.ManyToManyField(SubjectTag)
    characteristics_binary = models.ManyToManyField(CharacteristicBinary)
    characteristics_continous = models.ManyToManyField(CharacteristicContinouos)
    # characteristics_range = models.ManyToManyField(CharacteristicRange)


class Group(Sidable, models.Model):
    number = models.IntegerField()

    class Meta:
        abstract = True



class SubjectGroup(Group):
    Intervention = models.ForeignKey(Intervention,on_delete=True)
    subjects = models.ManyToManyField(Subject, through="RelativeAmount")

# dont do this
class RelativeAmount(models.Model):
    subjects = models.ForeignKey(Subject, on_delete=models.CASCADE)
    subjects_group = models.ForeignKey(SubjectGroup,on_delete=models.CASCADE)
    relative_amount = models.FloatField()
