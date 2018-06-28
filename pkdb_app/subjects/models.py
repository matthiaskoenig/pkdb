from django.db import models

#studies import
from ..studies.models import Intervention
from ..behaviours import Sidable, Describable
from ..choices import SPECIE_CHOICES ,CHARATERISTIC_CHOICES


class SubjectTag(Sidable,Describable,models.Model):
    pass


class Characteristic(Sidable,models.Model):
    type = models.IntegerField(choices=CHARATERISTIC_CHOICES)

    class Meta:
        abstract = True


class CharacteristicBinary(Characteristic):
    value = models.BinaryField()


class CharacteristicContinous(Characteristic):
    value = models.FloatField()


class CharacteristicRange(Characteristic):
    start = models.FloatField()
    end = models.FloatField()


class Subject(Sidable,models.Model):
    specie = models.IntegerField(choices=SPECIE_CHOICES)
    tags = models.ManyToManyField(SubjectTag)
    characteristics_binary = models.ManyToManyField(CharacteristicBinary)
    characteristics_continous = models.ManyToManyField(CharacteristicContinous)
    characteristics_range = models.ManyToManyField(CharacteristicRange)


class Group(Sidable,models.Model):
    number = models.IntegerField()

    class Meta:
        abstract = True


class SubjectGroup(Group):
    Intervention = models.ForeignKey(Intervention,on_delete=True)
    subjects = models.ManyToManyField(Subject, through="RelativeAmount")


class RelativeAmount(models.Model):
    subjects = models.ForeignKey(Subject,on_delete=models.CASCADE)
    subjects_group = models.ForeignKey(SubjectGroup,on_delete=models.CASCADE)
    relative_amount = models.FloatField()








