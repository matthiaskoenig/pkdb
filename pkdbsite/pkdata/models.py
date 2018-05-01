from django.db import models


class Publication(models.Model):
    """ Store the publication information. """
    pmid = models.IntegerField(max_length=200)
    title = models.TextField()
    abstract = models.TextField()


# TODO: Provide facets


class Study(models.Model):
    study_id = models.CharField(max_length=200)
    reference = models.ForeignKey(Publication)
    text = models.TextField()





class Intervention(models.Model):
    intervention_id = models.CharField(max_length=200)
    text = models.TextField()
    study = models.ForeignKey(Study)

# TODO: define choices for the various fields


class Group(models.Model):
    """ Describes the groups of subjects. """
    group_id = models.CharField(max_length=200)
    species = models.CharField(max_length=200)
    ethnicity = models.CharField(max_length=200)
    count = models.IntegerField()
    gender = models.CharField(max_length=200)
    healthy = models.CharField(dmax_length=200)
    condition = models.CharField(dmax_length=200)

    keywords = models.TextField()
    text = models.TextField()
    study = models.ForeignKey(Study)

class


class Parameter(Models.model):
    """ General storage form of parameters."""

    group = models.CharField(max_length=200)
    type = models.CharField(max_length=200)
    n = models.IntegerField()
    unit = models.CharField(max_length=200)
    mean = models.FloatField()
    median = models.FloatField()
    sd = models.FloatField()
    se = models.FloatField()
    cv = models.FloatField()
    min = models.FloatField()
    max = models.FloatField()
    text




class Consumption(models.Model):
    """ Encode the various consuption modes.
    Important mainly for alcohol and cigarettes, oral contraceptives.
    """
    substance = models.CharField(dmax_length=200)

    text = models.TextField()


class Medication(models.Model):
    """

    """
    pass


class Dosing(models.Model):
    text = models.TextField()
    study = models.ForeignKey(Study)


class Pharmacokinetics(models.Model):
    text = models.TextField()