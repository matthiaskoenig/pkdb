"""
Describe Substances
"""
from django.apps import apps
from django.db import models
from pkdb_app.categorials.models import Annotation
from pkdb_app.users.models import User
from ..utils import CHAR_MAX_LENGTH
from ..behaviours import Sidable

# -------------------------------------------------
# Substance
# -------------------------------------------------


class Substance(Sidable, models.Model):
    """ Substances.

    There could be three main classes of `substances`:
    1. Substance with a chebi identifier
    - this is a basic substance and can have a mass (or not)
    2. Substance with no chebi identifier
    - this is a basic substance and can have a mass (or not)
    3. Derived substance (with no chebi identifier)
    - this is a combination of basic substances (from class 1 or 2).
    - this has no mass
    - if all partial substances have mass this could be used for unit transformations ?!

    Has to be extended via ontology (Ontologable)
    """
    # this cannot be null (for class 1 & 2), must be null for class 3
    name = models.CharField(max_length=CHAR_MAX_LENGTH, unique=True)
    chebi = models.CharField(null=True, max_length=CHAR_MAX_LENGTH, unique=True)
    url_slug = models.CharField(max_length=CHAR_MAX_LENGTH, unique=True)

    description = models.TextField(blank=True, null=True)
    mass = models.FloatField(null=True)
    charge = models.FloatField(null=True)
    formula = models.CharField(null=True, max_length=CHAR_MAX_LENGTH)  # chemical formula

    parents = models.ManyToManyField("Substance", related_name="children")
    creator = models.ForeignKey(User, related_name="substances", on_delete=models.CASCADE)

    annotations = models.ManyToManyField(Annotation)


    # validation rule: check that all labels are in derived and not more(split on `+/()`)

    def __str__(self):
        return self.name

    @property
    def derived(self):
        return self.parents.exists()

    @property
    def outputs_normed(self):
        return self.output_set.filter(normed=True)

    @property
    def outputs_calculated(self):
        return self.output_set.filter(normed=True, calculated=True)

    @property
    def timecourses_normed(self):
        return self.timecourse_set.filter(normed=True)

    @property
    def interventions_normed(self):
        return self.intervention_set.filter(normed=True)

    @property
    def creator_username(self):
        return self.creator.username


class SubstanceSynonym(models.Model):
    name = models.CharField(max_length=CHAR_MAX_LENGTH, unique=True)
    substance = models.ForeignKey(Substance, on_delete=models.CASCADE, related_name="synonyms")


