"""Reusable behavior for models."""

from django.contrib.auth import get_user_model
from django.db import models

from pkdb_app.info_nodes.units import ureg

from .utils import CHAR_MAX_LENGTH, CHAR_MAX_LENGTH_LONG


class Sidable(models.Model):
    """Model has an sid."""

    sid = models.CharField(max_length=CHAR_MAX_LENGTH, primary_key=True)

    class Meta:
        abstract = True


class Externable(models.Model):
    """Model has the mapping fields for the subset, source and image columns of an upload."""

    # format = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)
    subset_map = models.CharField(max_length=CHAR_MAX_LENGTH_LONG, null=True)
    source_map = models.CharField(max_length=CHAR_MAX_LENGTH_LONG, null=True)
    image_map = models.CharField(max_length=CHAR_MAX_LENGTH_LONG, null=True)

    class Meta:
        abstract = True


class Accessible(models.Model):
    """Model derives its access level and allowed users from its related study."""

    class Meta:
        abstract = True

    @property
    def access(self):
        """Return the access level of the related study."""
        return self.study.access

    @property
    def allowed_users(self):
        """Return the union of the study's creator, curators and collaborators."""
        creator = self.study.creator
        creator_queryset = get_user_model().objects.filter(id=creator.id)
        curators = self.study.curators.all()
        collaborators = self.study.collaborators.all()
        return collaborators.union(curators).union(creator_queryset)

    @property
    def study_name(self):
        """Return the name of the related study."""
        return self.study.name

    @property
    def study_sid(self):
        """Return the sid of the related study."""
        return self.study.sid


def map_field(fields):
    """Return the ``<field>_map`` column names for the given field names."""
    return [f"{field}_map" for field in fields]


VALUE_FIELDS_SAME_SCALE = ["value", "mean", "median", "min", "max"]
VALUE_FIELDS_NO_UNIT = [*VALUE_FIELDS_SAME_SCALE, "sd", "se", "cv"]
VALUE_FIELDS = [*VALUE_FIELDS_NO_UNIT, "unit"]
VALUE_MAP_FIELDS = map_field(VALUE_FIELDS)

MEASUREMENTTYPE_FIELDS = [
    "measurement_type",
    "calculation_type",
    "choice",
    "substance",
    *VALUE_FIELDS,
]
EX_MEASUREMENTTYPE_FIELDS = MEASUREMENTTYPE_FIELDS + map_field(MEASUREMENTTYPE_FIELDS)


class ValueableMapNotBlank(models.Model):
    """Model has the mapping fields for each value and statistic column of an upload."""

    value_map = models.CharField(max_length=CHAR_MAX_LENGTH_LONG, null=True)
    mean_map = models.CharField(max_length=CHAR_MAX_LENGTH_LONG, null=True)
    median_map = models.CharField(max_length=CHAR_MAX_LENGTH_LONG, null=True)
    min_map = models.CharField(max_length=CHAR_MAX_LENGTH_LONG, null=True)
    max_map = models.CharField(max_length=CHAR_MAX_LENGTH_LONG, null=True)
    sd_map = models.CharField(max_length=CHAR_MAX_LENGTH_LONG, null=True)
    se_map = models.CharField(max_length=CHAR_MAX_LENGTH_LONG, null=True)
    cv_map = models.CharField(max_length=CHAR_MAX_LENGTH_LONG, null=True)
    unit_map = models.CharField(max_length=CHAR_MAX_LENGTH_LONG, null=True)

    class Meta:
        abstract = True


class ValueableNotBlank(models.Model):
    """Core class for storing numeric information.

    Adds fields to store values with their statistics.
    This is reused to encode outputs, characteristica and interventions.

    FIXME: support geometric means see https://github.com/matthiaskoenig/pkdb/issues/677

    Redesign to:
    # unit (for measurement type)
    unit = models.CharField(max_length=CHAR_MAX_LENGTH_LONG, null=True)

    # single measurement
    value = models.FloatField(null=True)

    # group measurement (averaged over single measurements)
    ListOfAverages:
      average = models.FloatField(null=True)
      average_type  # [mean, median, geometricMean, skewness]

    # range
    ListOfRanges:
      min = models.FloatField(null=True)
      max = models.FloatField(null=True)
      range_type  # [range, confidenceInterval, interquartileRange, detectionLimit]

    # error
    ListOfErrors
      error = models.FloatField(null=True)
      error_type # [sd, se, cv, variance]
    """

    value = models.FloatField(null=True)
    mean = models.FloatField(null=True)
    median = models.FloatField(null=True)
    # calculation_type [arithmetic, geometric, None]
    min = models.FloatField(null=True)
    max = models.FloatField(null=True)
    sd = models.FloatField(null=True)
    se = models.FloatField(null=True)
    cv = models.FloatField(null=True)
    unit = models.CharField(max_length=CHAR_MAX_LENGTH_LONG, null=True)

    class Meta:
        abstract = True


class MeasurementTypeable(ValueableNotBlank):
    """Model has a measurement type, calculation type, substance and choice with values."""

    measurement_type = models.ForeignKey(
        "info_nodes.MeasurementType", on_delete=models.PROTECT
    )
    calculation_type = models.ForeignKey(
        "info_nodes.CalculationType", null=True, on_delete=models.PROTECT
    )
    substance = models.ForeignKey(
        "info_nodes.Substance", null=True, on_delete=models.PROTECT
    )
    choice = models.ForeignKey("info_nodes.Choice", null=True, on_delete=models.PROTECT)

    class Meta:
        abstract = True

    def self_plural(self):
        """Return the lower cased plural of the class name, e.g. 'outputs'."""
        return f"{self.__class__.__name__.lower()}s"

    @property
    def measurement_type_name(self):
        """Return the name of the info node of the measurement type."""
        return self.measurement_type.info_node.name

    @property
    def calculation_type_name(self):
        """Return the name of the calculation type's info node, or None if unset."""
        if self.calculation_type:
            return self.calculation_type.info_node.name
        return None

    @property
    def substance_name(self):
        """Return the name of the substance's info node, or None if unset."""
        if self.substance:
            return self.substance.info_node.name
        return None

    @property
    def choices(self):
        """Return the allowed choices of the measurement type."""
        return self.measurement_type.choices_list()

    def _i(self, info_node):
        """Return the info node of the given related field, or None if unset."""
        related_field = getattr(self, info_node)
        if related_field:
            return related_field.info_node
        return None

    @property
    def i_measurement_type(self):
        """Return the info node of the measurement type."""
        return self._i("measurement_type")

    @property
    def i_calculation_type(self):
        """Return the info node of the calculation type, or None if unset."""
        return self._i("calculation_type")

    @property
    def i_choice(self):
        """Return the info node of the choice, or None if unset."""
        return self._i("choice")

    @property
    def i_substance(self):
        """Return the info node of the substance, or None if unset."""
        return self._i("substance")

    @property
    def study_name(self):
        """Return the name of the related study."""
        return self.study.name

    @property
    def study_sid(self):
        """Return the sid of the related study."""
        return self.study.sid

    @property
    def choice_name(self):
        """Return the name of the choice's info node, or None if unset."""
        if self.choice:
            return self.choice.info_node.name
        return None


class Normalizable(MeasurementTypeable):
    """Model can be normalized to the default unit of its measurement type.

    Keeps a link to the raw (as uploaded) instance it was normalized from.
    """

    raw = models.ForeignKey(
        "self", related_name="norm", on_delete=models.CASCADE, null=True
    )
    normed = models.BooleanField(default=False)

    class Meta:
        abstract = True

    @property
    def norm_fields(self):
        """Return the value and error fields which are converted during normalization."""
        return {
            "value": self.value,
            "mean": self.mean,
            "median": self.median,
            "min": self.min,
            "max": self.max,
            "sd": self.sd,
            "se": self.se,
        }

    @property
    def norm_unit(self):
        """Return the normalized unit registered for the current unit on the measurement type."""
        return self.measurement_type.units.get(self.unit)

    @property
    def is_norm(self):
        """Return whether the current unit already is the norm unit of the measurement type."""
        if self.unit:
            return self.measurement_type.is_norm_unit(self.unit)
        return True

    @property
    def is_removeable_substance_dimension(self):
        """Checks if the object has a substance which has units which can be normalized.

        :return: tuple (boolean, dimension), i.e, (can be normalized, dimension of substance)
        """
        substance = getattr(self, "substance", None)
        if substance and substance.mass:
            dimension_of_substance = self.measurement_type.p_unit(
                self.unit
            ).dimensionality.get("[substance]")
            if dimension_of_substance != 0:
                return True, dimension_of_substance

        return (False, None)

    def remove_substance_dimension(self):
        """Remove substance unit by using the molar mass in [g/mole] to convert [mole] -> [g].

        :return: tuple (magnitude, unit), i.e., pre-factor and resulting unit
        """
        is_removeable_substance, dimension = self.is_removeable_substance_dimension
        if is_removeable_substance:
            molar_weight = ureg("g/mol") * self.substance.mass
            p_unit = self.measurement_type.p_unit(self.unit)
            this_quantity = p_unit * molar_weight**dimension
            return this_quantity.magnitude, str(this_quantity.units)
        return 1, self.unit

    def normalize(self):
        """Normalize the units.

        Units are brought to default units.
        Values are changed according to the conversion factor.
        If possible removes substance dimension (mole -> g) via molecular weight.

        :return:
        """
        factor, unit = self.remove_substance_dimension()

        # remove substance unit

        if unit and self.unit and ureg(unit) != ureg(self.unit):
            for key, value in self.norm_fields.items():
                if value is not None:
                    setattr(self, key, value * factor)
            self.unit = unit

        # else:
        #    self.unit = str(ureg(self.unit).u)

        # normalization
        if not self.is_norm:
            for key, value in self.norm_fields.items():
                if value is not None:
                    setattr(
                        self,
                        key,
                        self.measurement_type.normalize(value, self.unit).magnitude,
                    )

            self.unit = str(self.measurement_type.norm_unit(self.unit))
