"""
Model for the InfoNodes.
"""
import re
from numbers import Number
import pint

from django.db import models
from django.utils.translation import gettext_lazy as _
from pint import UndefinedUnitError

from pkdb_app.behaviours import Sidable
from pkdb_app.info_nodes.units import ureg
from pkdb_app.utils import CHAR_MAX_LENGTH, CHAR_MAX_LENGTH_LONG, _validate_required_key_and_value_or_nr, \
    _validate_required_key_and_value
from rest_framework import serializers


class Annotation(models.Model):
    """ Annotation Model"""
    term = models.CharField(max_length=CHAR_MAX_LENGTH)
    relation = models.CharField(max_length=CHAR_MAX_LENGTH)
    collection = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)
    description = models.TextField(blank=True, null=True)
    label = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)
    url = models.URLField(max_length=CHAR_MAX_LENGTH_LONG, null=False)


class CrossReference(models.Model):
    """ CrossReference. """
    name = models.CharField(max_length=CHAR_MAX_LENGTH, null=False)
    accession = models.CharField(max_length=CHAR_MAX_LENGTH, null=False)
    url = models.URLField(max_length=CHAR_MAX_LENGTH_LONG, null=False)


class InfoNode(Sidable):
    class NTypes(models.TextChoices):
        """ Note Types. """

        Substance = 'substance', _('substance')
        MeasurementType = 'measurement_type', _('measurement_type')
        Route = 'route', _('route')
        Form = 'form', _('form')
        Application = 'application', _('application')
        Tissue = 'tissue', _('tissue')
        Method = 'method', _('method')
        CalculationType = 'calculation_type', _('calculation_type')

        Choice = 'choice', _('choice')
        Info_Node = 'info_node', _('info_node')


    class DTypes(models.TextChoices):
        """ Data Types. """
        Abstract = 'abstract', _('abstract')
        Boolean = 'boolean', _('boolean')
        Undefined = 'undefined', _('undefined')
        Numeric = 'numeric', _('numeric')
        Categorical = 'categorical', _('categorical')
        NumericCategorical = 'numeric_categorical', _('numeric_categorical')

    name = models.CharField(max_length=CHAR_MAX_LENGTH)
    label = models.CharField(max_length=CHAR_MAX_LENGTH)
    deprecated = models.BooleanField()
    description = models.TextField(blank=True, null=True)
    annotations = models.ManyToManyField(Annotation, "annotations")
    xrefs = models.ManyToManyField(CrossReference, "info_nodes")
    parents = models.ManyToManyField("InfoNode", related_name="children")
    ntype = models.CharField(null=False, blank=False, choices=NTypes.choices, max_length=20)
    dtype = models.CharField(null=False, blank=False, choices=DTypes.choices, max_length=20)

    def annotations_strings(self):
        return [f"relation <{annotation.relation}>:, {annotation.term}" for annotation in self.annotations.all()]

    @property
    def synonym_names(self):
        """
        :return: list of normalized units as strings
        """
        return list(self.synonyms.values_list("name", flat=True))

    @property
    def creator_username(self):
        """
        :return: list of normalized units in the data format of pint
        """
        return self.creator.username


class Synonym(models.Model):
    """Synonym Model"""
    name = models.CharField(max_length=CHAR_MAX_LENGTH_LONG, unique=True)
    info_node = models.ForeignKey(InfoNode, on_delete=models.CASCADE, related_name="synonyms", null=True)


class AbstractInfoNode(models.Model):
    class Meta:
        abstract = True

    def sid(self):
        return self.info_node.sid

    def name(self):
        return self.info_node.name

    def __str__(self):
        return self.info_node.name


class Tissue(AbstractInfoNode):
    """ Tissue Model """
    info_node = models.OneToOneField(
        InfoNode, related_name="tissue", on_delete=models.CASCADE, null=True
    )


class Method(AbstractInfoNode):
    """ Method Model """
    info_node = models.OneToOneField(
        InfoNode, related_name="method", on_delete=models.CASCADE, null=True
    )


class Route(AbstractInfoNode):
    """ Route Model """
    info_node = models.OneToOneField(
        InfoNode, related_name="route", on_delete=models.CASCADE, null=True
    )


class Application(AbstractInfoNode):
    """ Application Model """
    info_node = models.OneToOneField(
        InfoNode, related_name="application", on_delete=models.CASCADE, null=True
    )


class Form(AbstractInfoNode):
    """ Form Model """
    info_node = models.OneToOneField(
        InfoNode, related_name="form", on_delete=models.CASCADE, null=True
    )


class Unit(models.Model):
    """Units Model"""
    name = models.CharField(max_length=CHAR_MAX_LENGTH)

    @property
    def p_unit(self):
        return ureg(self.name).u


class MeasurementType(AbstractInfoNode):
    """ MeasurementType Model """
    info_node = models.OneToOneField(
        InfoNode, related_name="measurement_type", on_delete=models.CASCADE, null=True
    )

    NO_UNIT = 'NO_UNIT'  # todo: remove NO_UNIT and add extra keyword or add an extra measurement_type with optional no units.
    TIME_REQUIRED_MEASUREMENT_TYPES = [
        "concentration",
        "cumulative amount",
        "metabolic ratio",
        "cumulative metabolic ratio",
        "recovery",
        "auc_end",
        "ptf",
    ]  # todo: remove and add extra keyword.
    TIME_REQUIRED_MEASUREMENT_TYPES_NR_ALLOWED = [

     ]
    CAN_NEGATIVE = [
        "tmax",  # tmax can be negative due to time offsets, i.e. pre-simulation with subsequent fall after intervention
        "concentration change",    # this often happens in placebo simulations
        "EHR change",
    ]
    ADDITIVE = []  # todo remove

    units = models.ManyToManyField(Unit, related_name="measurement_types")

    @property
    def choices(self):
        return self.info_node.choices.all()

    def __str__(self):
        return self.info_node.name

    def __repr__(self):
        return self.info_node.name

    @property
    def n_p_units(self):
        """
        :return: list of normalized units in the data format of pint
        """
        return [unit.p_unit for unit in self.units.all()]

    @property
    def n_units(self):
        """
        :return: list of normalized units as strings
        """
        return list(self.units.values_list("name", flat=True))

    @property
    def valid_dimensions(self):
        return [unit.dimensionality for unit in self.n_p_units]

    @property
    def valid_dimensions_str(self):
        return [str(unit.dimensionality) for unit in self.n_p_units]

    @property
    def dimension_to_n_unit(self):
        return {str(n_unit_p.dimensionality): n_unit_p for n_unit_p in self.n_p_units}

    @staticmethod
    def p_unit(unit):
        try:
            p_unit = ureg(unit)
            p_unit.u  # check if pint unit can be accessed
            return p_unit
        except (UndefinedUnitError, AttributeError):
            if unit == "%":
                raise ValueError(f"unit: [{unit}] has to be encoded as 'percent'")

            raise ValueError(f"unit [{unit}] is not defined in unit registry or not allowed.")

    def is_valid_unit(self, data):
        unit = data.get("unit", None)
        is_valid = self._is_valid_unit(unit)
        if is_valid:
            is_valid = self._validate_special(data)
        return is_valid

    def _validate_special(self, data):
        unit = data.get("unit", None)
        if self.info_node.sid == "recovery":
            factor = self.p_unit(unit).to("dimensionless")
            for key in ["value", "mean", "median"]:
                    if data.get(key):
                        if factor.m*data[key] > 2:
                            msg = f"<{key}> with value <{data[key]}> and unit <{unit}> cannot be greater than " \
                                  f"<{2/factor.m}>. Note that the unit 'dimensionless'= 'none' = 'percent'/100."
                            raise serializers.ValidationError({"unit": msg})

        return True

    def _is_valid_unit(self,unit):
        if not re.match("^[\/^_*.() µα-ωΑ-Ωa-zA-Z0-9]*$", str(unit)):
            msg = f"Unit value <{unit}> contains not allowed characters. " \
                  f"Allowed  characters are '[\/^*.() µα-ωΑ-Ωa-zA-Z0-9]'."
            raise serializers.ValidationError({"unit": msg})
        try:
            p_unit = self.p_unit(unit)

        except pint.DefinitionSyntaxError:
            msg = f"The unit [{unit}] has a wrong syntax."
            raise serializers.ValidationError(
                {"unit": msg})

        if len(self.n_units) != 0:
            if unit:
                return any([p_unit.check(dim) for dim in self.valid_dimensions])
            else:
                # unit_not_required2 = self.dtype == NUMERIC_CATEGORIAL_TYPE
                # return unit_not_required2
                unit_not_required2 = self.NO_UNIT in self.n_units
                return unit_not_required2

        else:
            if unit:
                return False
            else:
                return True

    def validate_unit(self, data):
        unit = data.get("unit", None)
        if not self.is_valid_unit(data):
            msg = f"For measurement type `{self.info_node.name}` the unit [{unit}] with dimension {self.unit_dimension(unit)} " \
                  f"is not allowed."
            raise ValueError(
                {"unit": msg, "Only units with the following dimensions are allowed:": self.valid_dimensions_str,
                 "Units are allowed which can be converted to the following normalized units:": self.n_units})

    def is_valid_time_unit(self, time_unit):
        return self.p_unit(time_unit).dimensionality == '[time]'

    def validate_time_unit(self, unit):
        if not self.is_valid_time_unit(unit):
            msg = f"[{unit}] with dimension [{self.unit_dimension(unit)}] is not allowed for the time units. "
            raise ValueError({"time_unit": msg})

    def norm_unit(self, unit):
        try:
            return self.dimension_to_n_unit[str(self.unit_dimension(unit))]
        except KeyError:
            raise ValueError(
                f"Dimension [{self.unit_dimension(unit)}] is not allowed for measurement type [{self.info_node.name}]."
                f" Dimension was calculated from unit :[{unit}]")

    def unit_dimension(self, unit):
        return self.p_unit(unit).dimensionality

    def is_norm_unit(self, unit):
        return ureg(unit) in self.n_p_units

    def normalize(self, magnitude, unit):
        this_unit_p = self.p_unit(unit)
        this_norm_unit_p = self.norm_unit(unit)
        result = (magnitude * this_unit_p).to(this_norm_unit_p)
        return result

    def is_valid_choice(self, choice):
        return choice in self.choices_list()

    def choices_list(self):
        return self.choices.values_list("info_node__name", flat=True)

    @property
    def time_required(self):
        if self.info_node.name in self.TIME_REQUIRED_MEASUREMENT_TYPES:
            return True
        else:
            return False

    def validate_choice(self, choice):
        if choice:
            if self.info_node.dtype in [self.info_node.DTypes.Categorical, self.info_node.DTypes.Boolean,
                                        self.info_node.DTypes.NumericCategorical]:
                if not self.is_valid_choice(choice):
                    msg = f"The choice `{choice}` is not a valid choice for measurement type `{self.info_node.name}`. " \
                          f"Allowed choices are: `{sorted(self.choices_list())}`."
                    raise ValueError({"choice": msg})

                return self.choices.get(info_node__name=choice)
            else:
                msg = f"The field `choice` is not allowed for measurement type `{self.info_node.name}`. " \
                      f"For numerical values the fields `value`, `mean` or `median` are used. " \
                      f"For encoding substances use the `substance` field."
                raise ValueError({"choice": msg})
        elif self.choices.exists():
            msg = f"{choice}. A choice is required for `{self.info_node.name}`." \
                  f" Allowed choices are: `{sorted(self.choices_list())}`."
            raise ValueError({"choice": msg})

    @property
    def numeric_fields(self):
        return ["value", "mean", "median", "min", "max", "sd", "se", "cv"]

    def validate_numeric(self, data):
        """ Validates the numerics of the data.

        This ensures that measurements are not-negative.
        Raises ValueError
        :param data:
        :return:
        """
        if self.info_node.dtype in [self.info_node.DTypes.NumericCategorical, self.info_node.DTypes.Numeric]:
            for field in self.numeric_fields:
                value = data.get(field)

                # validate that not negative
                if self.info_node.name not in self.CAN_NEGATIVE:
                    valid = True
                    if isinstance(value, Number):
                        valid = not (value < 0)
                    elif isinstance(value, list):
                        valid = not any(v < 0 for v in value)

                    if not valid:
                        raise ValueError(
                            {field: f"Numeric values need to be positive (>=0) "
                                    f"for all measurement types except "
                                    f"<{self.CAN_NEGATIVE}>.", "detail": data})

    def validate_complete(self, data, time_allowed: bool = True):
        """Complete validation."""

        # check unit
        self.validate_unit(data)
        self.validate_numeric(data)

        choice = data.get("choice", None)
        d_choice = self.validate_choice(choice)

        if time_allowed:
            time_unit = data.get("time_unit", None)
            time = data.get("time", None)

            if time_unit and time_unit != "NR":
                self.validate_time_unit(time_unit)

            if self.time_required:
                details = f"for measurement type `{self.info_node.name}`"

                if time != "NR":
                    _validate_required_key_and_value(data, "time", details=details)
                    if time_unit != "NR":
                        _validate_required_key_and_value(data, "time_unit", details=details)

            if time == "NR":
                data["time"] = None
            if time_unit == "NR":
                data["time_unit"] = None

        return {"choice": d_choice}


class Choice(AbstractInfoNode):
    info_node = models.OneToOneField(
        InfoNode, related_name="choice", on_delete=models.CASCADE, null=True)
    measurement_types = models.ManyToManyField(InfoNode, related_name="choices")

    @property
    def sid(self):
        return self.info_node.sid

    @property
    def name(self):
        return self.info_node.name

    @property
    def description(self):
        return self.info_node.description

    @property
    def annotations(self):
        return self.info_node.annotations

    @property
    def label(self):
        return self.info_node.label


class CalculationType(AbstractInfoNode):
    """ CalculationType
    The way averages are calculated (e.g. mean, median, geometric mean)
    """
    info_node = models.OneToOneField(
        InfoNode, related_name="calculation_type", on_delete=models.CASCADE, null=True
    )

    def __str__(self):
        return self.info_node.name


class Substance(AbstractInfoNode):
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
    info_node = models.OneToOneField(
        InfoNode, related_name="substance", on_delete=models.CASCADE, null=True
    )
    chebi = models.CharField(null=True, max_length=CHAR_MAX_LENGTH, unique=True)
    mass = models.FloatField(null=True)
    charge = models.FloatField(null=True)
    formula = models.CharField(null=True, max_length=CHAR_MAX_LENGTH)  # chemical formula


    @property
    def derived(self):
        # validation rule: check that all labels are in derived and not more(split on `+/()`)
        return self.info_node.parents.exists()

    @property
    def outputs_normed(self):
        return self.output_set.filter(normed=True)

    @property
    def outputs_calculated(self):
        return self.output_set.filter(normed=True, calculated=True)

    @property
    def interventions_normed(self):
        return self.intervention_set.filter(normed=True)
