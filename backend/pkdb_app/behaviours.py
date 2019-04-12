"""
Reusable behavior for models.
"""
from django.db import models
from pkdb_app.normalization import get_sd, get_se, get_cv

from .utils import CHAR_MAX_LENGTH_LONG, CHAR_MAX_LENGTH
from .units import ureg


class Sidable(models.Model):
    """ Model has an sid. """
    sid = models.CharField(max_length=CHAR_MAX_LENGTH, primary_key=True)

    class Meta:
        abstract = True


class Externable(models.Model):
    format = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)
    subset_map = models.CharField(max_length=CHAR_MAX_LENGTH_LONG, null=True)
    groupby = models.CharField(max_length=CHAR_MAX_LENGTH_LONG, null=True)

    class Meta:
        abstract = True


class Valueable(models.Model):
    """ Valuable.

    Adds fields to store values with their statistics.
    """
    value = models.FloatField(null=True, blank=True)
    mean = models.FloatField(null=True, blank=True)
    median = models.FloatField(null=True, blank=True)
    min = models.FloatField(null=True, blank=True)
    max = models.FloatField(null=True, blank=True)
    sd = models.FloatField(null=True, blank=True)
    se = models.FloatField(null=True, blank=True)
    cv = models.FloatField(null=True, blank=True)
    unit = models.CharField(max_length=CHAR_MAX_LENGTH, null=True, blank=True)

    class Meta:
        abstract = True


class ValueableNotBlank(models.Model):
    """ Valuable.

    Adds fields to store values with their statistics.
    """
    value = models.FloatField(null=True)
    mean = models.FloatField(null=True)
    median = models.FloatField(null=True)
    min = models.FloatField(null=True)
    max = models.FloatField(null=True)
    sd = models.FloatField(null=True)
    se = models.FloatField(null=True)
    cv = models.FloatField(null=True)
    unit = models.CharField( max_length=CHAR_MAX_LENGTH, null=True)

    class Meta:
        abstract = True


class ValueableMap(models.Model):
    """ValuableMap."""
    value_map = models.CharField(max_length=CHAR_MAX_LENGTH_LONG, null=True, blank=True)
    mean_map = models.CharField(max_length=CHAR_MAX_LENGTH_LONG, null=True, blank=True)
    median_map = models.CharField(max_length=CHAR_MAX_LENGTH_LONG, null=True, blank=True)
    min_map = models.CharField(max_length=CHAR_MAX_LENGTH_LONG, null=True, blank=True)
    max_map = models.CharField(max_length=CHAR_MAX_LENGTH_LONG, null=True, blank=True)
    sd_map = models.CharField(max_length=CHAR_MAX_LENGTH_LONG, null=True, blank=True)
    se_map = models.CharField(max_length=CHAR_MAX_LENGTH_LONG, null=True, blank=True)
    cv_map = models.CharField(max_length=CHAR_MAX_LENGTH_LONG, null=True, blank=True)
    unit_map = models.CharField(max_length=CHAR_MAX_LENGTH_LONG, null=True, blank=True)

    class Meta:
        abstract = True


class ValueableMapNotBlank(models.Model):
    """ValuableMap."""
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


class Normalizable(models.Model):

    @property
    def norm_fields(self):
        return {"value": self.value, "mean": self.mean, "median": self.median, "min": self.min, "max": self.max,
                "sd": self.sd, "se": self.se}

    @property
    def norm_unit(self):
        return self.category_class_data.units.get(self.unit)

    @property
    def is_norm(self):
        if self.unit:
            return self.category_class_data.is_norm_unit(self.unit)
        else:
            return True

    @property
    def is_removeable_substance_dimension(self):
        """ Checks if the object has a substance which has units which can be normalized.

        :return: tuple (boolean, dimension), i.e, (can be normalized, dimension of substance)
        """

        substance = getattr(self, "substance", None)
        if substance and substance.mass:
            dimension_of_substance = self.category_class_data.p_unit(self.unit).dimensionality.get('[substance]')
            if dimension_of_substance != 0:
                return (True, dimension_of_substance)

        return (False, None)

    def remove_substance_dimension(self):
        """ Remove substance unit by using the molar mass in [g/mole] to
        convert [mole] -> [g].

        :return: tuple (magnitude, unit), i.e., pre-factor and resulting unit
        """
        is_removeable_substance, dimension = self.is_removeable_substance_dimension
        if is_removeable_substance:
            molar_weight = ureg("g/mol")*self.substance.mass
            p_unit = self.category_class_data.p_unit(self.unit)
            this_quantity = p_unit*molar_weight**dimension
            return (this_quantity.magnitude, str(this_quantity.units))
        else:
            return (1, self.unit)



    def normalize(self):
        """ Normalizes the units.

        Units are brought to default units.
        Values are changed according to the conversion factor.
        If possible removes substance dimension (mole -> g) via molecular weight.

        :return:
        """

        factor, unit = self.remove_substance_dimension()

        # remove substance unit
        if unit and self.unit:
            if ureg(unit) != ureg(self.unit):
                for key, value in self.norm_fields.items():
                    if value is not None:
                        setattr(self, key, value*factor)
                self.unit = unit

            else:
                self.unit = str(ureg(self.unit).u)

        # normalization
        if not self.is_norm:
            for key, value in self.norm_fields.items():
                if not value is None:
                    setattr(self, key, self.category_class_data.normalize(value, self.unit).magnitude)
            self.unit = str(self.category_class_data.norm_unit(self.unit))

    class Meta:
        abstract = True
