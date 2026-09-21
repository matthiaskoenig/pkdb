"""Models for the info nodes, the controlled vocabulary of PK-DB, and their units."""

import re
from numbers import Number

import pint
from django.db import models
from django.utils.translation import gettext_lazy as _
from pint import UndefinedUnitError
from rest_framework import serializers

from pkdb_app.behaviours import Sidable
from pkdb_app.info_nodes.units import ureg
from pkdb_app.utils import (
    CHAR_MAX_LENGTH,
    CHAR_MAX_LENGTH_LONG,
    _validate_required_key_and_value,
)


class Annotation(models.Model):
    """An ontology annotation attached to an info node, relating it to an external term."""

    term = models.CharField(max_length=CHAR_MAX_LENGTH)
    relation = models.CharField(max_length=CHAR_MAX_LENGTH)
    collection = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)
    description = models.TextField(blank=True, null=True)
    label = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)
    url = models.URLField(max_length=CHAR_MAX_LENGTH_LONG, null=False)


class CrossReference(models.Model):
    """A cross reference from an info node to an accession in an external database."""

    name = models.CharField(max_length=CHAR_MAX_LENGTH, null=False)
    accession = models.CharField(max_length=CHAR_MAX_LENGTH, null=False)
    url = models.URLField(max_length=CHAR_MAX_LENGTH_LONG, null=False)


class InfoNode(Sidable):
    """An entry of the controlled vocabulary (substance, measurement type, route, ...).

    Info nodes form a hierarchy through the ``parents``/``children`` relation and carry
    annotations and cross references to external ontologies and databases. The concrete
    kind of an info node is given by ``ntype`` and its data type by ``dtype``; the
    specialized models (Substance, MeasurementType, Tissue, ...) each hold a one-to-one
    link back to their info node.
    """

    class NTypes(models.TextChoices):
        """The kinds of info node.

        Substance, measurement type, route, form, application, tissue, method,
        calculation type, choice, or a generic info node.
        """

        Substance = "substance", _("substance")
        MeasurementType = "measurement_type", _("measurement_type")
        Route = "route", _("route")
        Form = "form", _("form")
        Application = "application", _("application")
        Tissue = "tissue", _("tissue")
        Method = "method", _("method")
        CalculationType = "calculation_type", _("calculation_type")

        Choice = "choice", _("choice")
        Info_Node = "info_node", _("info_node")

    class DTypes(models.TextChoices):
        """The data types a measurement type's values can have."""

        Abstract = "abstract", _("abstract")
        Boolean = "boolean", _("boolean")
        Undefined = "undefined", _("undefined")
        Numeric = "numeric", _("numeric")
        Categorical = "categorical", _("categorical")
        NumericCategorical = "numeric_categorical", _("numeric_categorical")

    name = models.CharField(max_length=CHAR_MAX_LENGTH)
    label = models.CharField(max_length=CHAR_MAX_LENGTH)
    deprecated = models.BooleanField()
    description = models.TextField(blank=True, null=True)
    annotations = models.ManyToManyField(Annotation, "annotations")
    xrefs = models.ManyToManyField(CrossReference, "info_nodes")
    parents = models.ManyToManyField("InfoNode", related_name="children")
    ntype = models.CharField(
        null=False, blank=False, choices=NTypes.choices, max_length=20
    )
    dtype = models.CharField(
        null=False, blank=False, choices=DTypes.choices, max_length=20
    )

    def annotations_strings(self):
        """Return the info node's annotations formatted as ``relation <relation>:, term``."""
        return [
            f"relation <{annotation.relation}>:, {annotation.term}"
            for annotation in self.annotations.all()
        ]

    @property
    def synonym_names(self):
        """Return the names of the info node's synonyms."""
        return list(self.synonyms.values_list("name", flat=True))

    @property
    def creator_username(self):
        """Return the username of the info node's creator."""
        return self.creator.username


class Synonym(models.Model):
    """An alternative name for an info node."""

    name = models.CharField(max_length=CHAR_MAX_LENGTH_LONG, unique=True)
    info_node = models.ForeignKey(
        InfoNode, on_delete=models.CASCADE, related_name="synonyms", null=True
    )


class AbstractInfoNode(models.Model):
    """Base for the models that specialize an info node with a one-to-one ``info_node`` link."""

    class Meta:
        abstract = True

    def sid(self):
        """Return the sid of the linked info node."""
        return self.info_node.sid

    def name(self):
        """Return the name of the linked info node."""
        return self.info_node.name

    def __str__(self):
        """Return the name of the linked info node."""
        return self.info_node.name


class Tissue(AbstractInfoNode):
    """An info node of type tissue, the site in the body a measurement or intervention refers to."""

    info_node = models.OneToOneField(
        InfoNode, related_name="tissue", on_delete=models.CASCADE, null=True
    )


class Method(AbstractInfoNode):
    """An info node of type method, the technique used to obtain a measurement."""

    info_node = models.OneToOneField(
        InfoNode, related_name="method", on_delete=models.CASCADE, null=True
    )


class Route(AbstractInfoNode):
    """An info node of type route, the route of administration of an intervention."""

    info_node = models.OneToOneField(
        InfoNode, related_name="route", on_delete=models.CASCADE, null=True
    )


class Application(AbstractInfoNode):
    """An info node of type application, how an intervention was administered (e.g. single dose)."""

    info_node = models.OneToOneField(
        InfoNode, related_name="application", on_delete=models.CASCADE, null=True
    )


class Form(AbstractInfoNode):
    """An info node of type form, the pharmaceutical form of an intervention (e.g. tablet)."""

    info_node = models.OneToOneField(
        InfoNode, related_name="form", on_delete=models.CASCADE, null=True
    )


class Unit(models.Model):
    """A unit of measurement, stored by its pint-parsable name."""

    name = models.CharField(max_length=CHAR_MAX_LENGTH)

    @property
    def p_unit(self):
        """Return the unit as a pint unit."""
        return ureg(self.name).u


class MeasurementType(AbstractInfoNode):
    """An info node of type measurement type, defining what is measured and its allowed units.

    Holds the allowed normalized units, the choices for categorical types and the
    validation logic for the values, units, time and choice of an output or intervention.
    """

    info_node = models.OneToOneField(
        InfoNode, related_name="measurement_type", on_delete=models.CASCADE, null=True
    )

    NO_UNIT = "NO_UNIT"  # todo: remove NO_UNIT and add extra keyword or add an extra measurement_type with optional no units.
    TIME_REQUIRED_MEASUREMENT_TYPES = [
        "concentration",
        "cumulative amount",
        "metabolic ratio",
        "cumulative metabolic ratio",
        "recovery",
        "auc_end",
        "ptf",
    ]  # todo: remove and add extra keyword.
    TIME_REQUIRED_MEASUREMENT_TYPES_NR_ALLOWED = []
    CAN_NEGATIVE = [
        "tmax",  # tmax can be negative due to time offsets, i.e. pre-simulation with subsequent fall after intervention
        # concentrations
        "concentration change",
        "concentration change absolute",
        "cumulative amount (change)",
        # blood pressure
        "blood pressure systolic (change)",
        "blood pressure systolic (change relative)"
        "blood pressure systolic auc_end (change)",
        "blood pressure diastolic (change)",
        "blood pressure diastolic (change relative)",
        "blood pressure diastolic auc_end (change)",
        "MAP (change absolute)",
        "renin activity (change absolute)",
        # heart rate
        "heart rate (change)",
        "EHR change",
        # physiology
        "weight (change)",
        "hba1c (change)",
        # coagulation
        "inr (change)",
        "prothrombin time(change)",
        "aPTT (change)",
    ]
    ADDITIVE = []  # todo remove

    units = models.ManyToManyField(Unit, related_name="measurement_types")

    @property
    def choices(self):
        """Return the allowed choices of this measurement type."""
        return self.info_node.choices.all()

    def __str__(self):
        """Return the name of the linked info node."""
        return self.info_node.name

    def __repr__(self):
        """Return the name of the linked info node."""
        return self.info_node.name

    @property
    def n_p_units(self):
        """Return the normalized units as pint units."""
        return [unit.p_unit for unit in self.units.all()]

    @property
    def n_units(self):
        """Return the normalized units as strings."""
        return list(self.units.values_list("name", flat=True))

    @property
    def valid_dimensions(self):
        """Return the pint dimensionalities of the normalized units."""
        return [unit.dimensionality for unit in self.n_p_units]

    @property
    def valid_dimensions_str(self):
        """Return the dimensionalities of the normalized units as strings."""
        return [str(unit.dimensionality) for unit in self.n_p_units]

    @property
    def dimension_to_n_unit(self):
        """Map each normalized unit's dimensionality string to its pint unit."""
        return {str(n_unit_p.dimensionality): n_unit_p for n_unit_p in self.n_p_units}

    @staticmethod
    def p_unit(unit):
        """Parse a unit string into a pint unit, raising ValueError for an invalid unit."""
        try:
            p_unit = ureg(unit)
            _ = p_unit.u  # check if pint unit can be accessed
            return p_unit
        except (UndefinedUnitError, AttributeError) as err:
            if unit == "%":
                raise ValueError(
                    f"unit: [{unit}] has to be encoded as 'percent'"
                ) from err

            raise ValueError(
                f"unit [{unit}] is not defined in unit registry or not allowed."
            ) from err

    def is_valid_unit(self, data):
        """Check the unit's characters, syntax and dimension, then run the type-specific checks."""
        unit = data.get("unit", None)
        is_valid = self._is_valid_unit(unit)
        if is_valid:
            is_valid = self._validate_special(data)
        return is_valid

    def _validate_special(self, data):
        """Reject a recovery value, mean or median whose fraction exceeds 2 (200%)."""
        unit = data.get("unit", None)
        if self.info_node.sid == "recovery":
            factor = self.p_unit(unit).to("dimensionless")
            for key in ["value", "mean", "median"]:
                if data.get(key) and factor.m * data[key] > 2:
                    msg = (
                        f"<{key}> with value <{data[key]}> and unit <{unit}> cannot be greater than "
                        f"<{2 / factor.m}>. Note that the unit 'dimensionless'= 'none' = 'percent'/100."
                    )
                    raise serializers.ValidationError({"unit": msg})

        return True

    def _is_valid_unit(self, unit):
        """Check the unit's characters and syntax, then that its dimension is allowed."""
        if not re.match(r"^[\/^_*.() µα-ωΑ-Ωa-zA-Z0-9]*$", str(unit)):
            msg = (
                f"Unit value <{unit}> contains not allowed characters. "
                rf"Allowed  characters are '[\/^*.() µα-ωΑ-Ωa-zA-Z0-9]'."
            )
            raise serializers.ValidationError({"unit": msg})
        try:
            p_unit = self.p_unit(unit)

        except pint.DefinitionSyntaxError as err:
            msg = f"The unit [{unit}] has a wrong syntax."
            raise serializers.ValidationError({"unit": msg}) from err

        if len(self.n_units) != 0:
            if unit:
                return any(p_unit.check(dim) for dim in self.valid_dimensions)
            # unit_not_required2 = self.dtype == NUMERIC_CATEGORIAL_TYPE
            # return unit_not_required2
            return self.NO_UNIT in self.n_units

        return not unit

    def validate_unit(self, data):
        """Raise ValueError unless data's unit is valid for this measurement type."""
        unit = data.get("unit", None)
        if not self.is_valid_unit(data):
            msg = (
                f"For measurement type `{self.info_node.name}` the unit [{unit}] with dimension {self.unit_dimension(unit)} "
                f"is not allowed."
            )
            raise ValueError(
                {
                    "unit": msg,
                    "Only units with the following dimensions are allowed:": self.valid_dimensions_str,
                    "Units are allowed which can be converted to the following normalized units:": self.n_units,
                }
            )

    def is_valid_time_unit(self, time_unit):
        """Return True if time_unit has the dimensionality of time."""
        return self.p_unit(time_unit).dimensionality == "[time]"

    def validate_time_unit(self, unit):
        """Raise ValueError unless unit has the dimensionality of time."""
        if not self.is_valid_time_unit(unit):
            msg = f"[{unit}] with dimension [{self.unit_dimension(unit)}] is not allowed for the time units. "
            raise ValueError({"time_unit": msg})

    def norm_unit(self, unit):
        """Return the normalized unit of the given unit's dimension."""
        try:
            return self.dimension_to_n_unit[str(self.unit_dimension(unit))]
        except KeyError as err:
            raise ValueError(
                f"Dimension [{self.unit_dimension(unit)}] is not allowed for measurement type [{self.info_node.name}]."
                f" Dimension was calculated from unit :[{unit}]"
            ) from err

    def unit_dimension(self, unit):
        """Return the pint dimensionality of the given unit."""
        return self.p_unit(unit).dimensionality

    def is_norm_unit(self, unit):
        """Return True if the given unit is already one of the normalized units."""
        return ureg(unit) in self.n_p_units

    def normalize(self, magnitude, unit):
        """Convert a magnitude given in unit to the corresponding normalized unit."""
        this_unit_p = self.p_unit(unit)
        this_norm_unit_p = self.norm_unit(unit)
        return (magnitude * this_unit_p).to(this_norm_unit_p)

    def is_valid_choice(self, choice):
        """Return True if choice is one of the measurement type's allowed choices."""
        return choice in self.choices_list()

    def choices_list(self):
        """Return the names of the measurement type's allowed choices."""
        return self.choices.values_list("info_node__name", flat=True)

    @property
    def time_required(self):
        """Return True if this measurement type requires a time value."""
        return self.info_node.name in self.TIME_REQUIRED_MEASUREMENT_TYPES

    def validate_choice(self, choice):
        """Validate the choice against the measurement type's dtype and allowed choices."""
        if choice:
            if self.info_node.dtype in [
                self.info_node.DTypes.Categorical,
                self.info_node.DTypes.Boolean,
                self.info_node.DTypes.NumericCategorical,
            ]:
                if not self.is_valid_choice(choice):
                    msg = (
                        f"The choice `{choice}` is not a valid choice for measurement type `{self.info_node.name}`. "
                        f"Allowed choices are: `{sorted(self.choices_list())}`."
                    )
                    raise ValueError({"choice": msg})

                return self.choices.get(info_node__name=choice)
            msg = (
                f"The field `choice` is not allowed for measurement type `{self.info_node.name}`. "
                f"For numerical values the fields `value`, `mean` or `median` are used. "
                f"For encoding substances use the `substance` field."
            )
            raise ValueError({"choice": msg})
        if self.choices.exists():
            msg = (
                f"{choice}. A choice is required for `{self.info_node.name}`."
                f" Allowed choices are: `{sorted(self.choices_list())}`."
            )
            raise ValueError({"choice": msg})
        return None

    @property
    def numeric_fields(self):
        """Return the names of the fields that can hold a numeric value."""
        return ["value", "mean", "median", "min", "max", "sd", "se", "cv"]

    def validate_numeric(self, data):
        """Validates the numerics of the data.

        This ensures that measurements are not-negative.
        Raises ValueError
        :param data:
        :return:
        """
        if self.info_node.dtype in [
            self.info_node.DTypes.NumericCategorical,
            self.info_node.DTypes.Numeric,
        ]:
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
                            {
                                field: f"Numeric values need to be positive (>=0) "
                                f"for all measurement types except "
                                f"<{self.CAN_NEGATIVE}>.",
                                "detail": data,
                            }
                        )

    def validate_complete(self, data, time_allowed: bool = True):
        """Validate data's unit, numeric values, choice, and time and time unit if time_allowed.

        Resolves any 'NR' time and time_unit values to None and returns the resolved choice.
        """
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
                        _validate_required_key_and_value(
                            data, "time_unit", details=details
                        )

            if time == "NR":
                data["time"] = None
            if time_unit == "NR":
                data["time_unit"] = None

        return {"choice": d_choice}


class Choice(AbstractInfoNode):
    """An info node of type choice, one allowed value of a categorical measurement type."""

    info_node = models.OneToOneField(
        InfoNode, related_name="choice", on_delete=models.CASCADE, null=True
    )
    measurement_types = models.ManyToManyField(InfoNode, related_name="choices")

    @property
    def sid(self):
        """Return the sid of the linked info node."""
        return self.info_node.sid

    @property
    def name(self):
        """Return the name of the linked info node."""
        return self.info_node.name

    @property
    def description(self):
        """Return the description of the linked info node."""
        return self.info_node.description

    @property
    def annotations(self):
        """Return the annotations of the linked info node."""
        return self.info_node.annotations

    @property
    def label(self):
        """Return the label of the linked info node."""
        return self.info_node.label


class CalculationType(AbstractInfoNode):
    """An info node of type calculation type.

    The way averages are calculated (e.g. mean, median, geometric mean).
    """

    info_node = models.OneToOneField(
        InfoNode, related_name="calculation_type", on_delete=models.CASCADE, null=True
    )

    def __str__(self):
        """Return the name of the linked info node."""
        return self.info_node.name


class Substance(AbstractInfoNode):
    """Substances.

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
    formula = models.CharField(
        null=True, max_length=CHAR_MAX_LENGTH
    )  # chemical formula

    @property
    def derived(self):
        """Return True if the substance is derived from other substances (has parents)."""
        # validation rule: check that all labels are in derived and not more(split on `+/()`)
        return self.info_node.parents.exists()

    @property
    def outputs_normed(self):
        """Return the normalized outputs measured for this substance."""
        return self.output_set.filter(normed=True)

    @property
    def outputs_calculated(self):
        """Return the normalized, calculated outputs for this substance."""
        return self.output_set.filter(normed=True, calculated=True)

    @property
    def interventions_normed(self):
        """Return the normalized interventions for this substance."""
        return self.intervention_set.filter(normed=True)
