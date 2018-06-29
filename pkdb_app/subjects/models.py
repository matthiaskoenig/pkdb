"""
Describes subjects which participated in a study.
This can be individuals or groups.
"""
from django.db import models

from ..studies.models import Intervention
from ..behaviours import Sidable, Describable
from ..choices import SPECIES_CHOICES ,CHARATERISTIC_CHOICES


class SubjectTag(Sidable, Describable, models.Model):
    pass


class Characteristic(Sidable, models.Model):
    """ Property which the individual or group has, examples are age, weight.
    These can be either
    - categorial
    - continuous

    """
    count (optional: either subset, or all) # can be done via through
    type = models.IntegerField(choices=CHARATERISTIC_CHOICES)

    class Meta:
        abstract = True


class CharacteristicCategorial(Characteristic):
    """
    - sex (M/F)
    - healthy (healthy/non-healthy)
    - ethnicity (Asian, Afroamerican, African, Caucasian)
    """
    category (sex, healthy)
    value = models.ChoiceField()



class Value():
    category/keyword/type (age, bodyweight, height, ...)
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



class CharacteristicContinuous(Characteristic):
    """
    -
    """
    value = models.FloatField()



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


class RelativeAmount(models.Model):
    subjects = models.ForeignKey(Subject, on_delete=models.CASCADE)
    subjects_group = models.ForeignKey(SubjectGroup,on_delete=models.CASCADE)
    relative_amount = models.FloatField()
