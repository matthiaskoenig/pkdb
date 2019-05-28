from pkdb_app.categorials.models import ureg, MeasurementType
from pkdb_app.substances.models import Substance
from django.db import models
from pkdb_app.utils import CHAR_MAX_LENGTH_LONG, CHAR_MAX_LENGTH

def map_field(fields):
    return  [f"{field}_map" for field in fields]

VALUE_FIELDS_NO_UNIT = ["value", "mean", "median", "min", "max", "sd", "se", "cv"]
VALUE_FIELDS = VALUE_FIELDS_NO_UNIT +  ["unit"]
VALUE_MAP_FIELDS = map_field(VALUE_FIELDS)


MEASUREMENTTYPE_FIELDS = ["measurement_type", "choice","substance"] +VALUE_FIELDS
EX_MEASUREMENTTYPE_FIELDS =MEASUREMENTTYPE_FIELDS + map_field(MEASUREMENTTYPE_FIELDS)




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


class ValueableNotBlank(models.Model):
    """ Valuable.

    Adds fields to store values with their statistics.
    """
    value  = models.FloatField(null=True)
    mean  = models.FloatField(null=True)
    median  = models.FloatField(null=True)
    min  = models.FloatField(null=True)
    max  = models.FloatField(null=True)
    sd  = models.FloatField(null=True)
    se  = models.FloatField(null=True)
    cv  = models.FloatField(null=True)
    unit  = models.CharField(max_length=CHAR_MAX_LENGTH_LONG, null=True)

    class Meta:
        abstract = True


class ExMeasurementTypeable(ValueableNotBlank,ValueableMapNotBlank):
    measurement_type = models.CharField(max_length=CHAR_MAX_LENGTH)
    measurement_type_map = models.CharField(max_length=CHAR_MAX_LENGTH)

    choice = models.CharField(max_length=CHAR_MAX_LENGTH * 3, null=True)
    choice_map = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)
    #substance = models.ForeignKey(Substance, null=True, on_delete=models.PROTECT)
    substance = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)
    substance_map = models.CharField(max_length=CHAR_MAX_LENGTH_LONG, null=True)


    class Meta:
        abstract = True



class MeasurementTypeable(ValueableNotBlank):

    measurement_type = models.ForeignKey(MeasurementType, on_delete=models.CASCADE)
    substance = models.ForeignKey(Substance, null=True, on_delete=models.PROTECT)
    choice = models.CharField(max_length=CHAR_MAX_LENGTH * 3, null=True)

    class Meta:
        abstract = True

    def self_plural(self):
        return f"{self.__class__.__name__.lower()}s"

    @property
    def measurement_type_name(self):
        return self.measurement_type.name

    @property
    def choices(self):
        return self.measurement_type.choices_list()


class Normalizable(MeasurementTypeable):
    raw = models.ForeignKey("self", related_name="norm", on_delete=models.CASCADE, null=True)
    normed = models.BooleanField(default=False)

    class Meta:
        abstract = True


    @property
    def norm_fields(self):
        return {"value": self.value, "mean": self.mean, "median": self.median, "min": self.min, "max": self.max,
                "sd": self.sd, "se": self.se}

    @property
    def norm_unit(self):
        return self.measurement_type.units.get(self.unit)

    @property
    def is_norm(self):
        if self.unit:
            return self.measurement_type.is_norm_unit(self.unit)
        else:
            return True

    @property
    def is_removeable_substance_dimension(self):
        """ Checks if the object has a substance which has units which can be normalized.

        :return: tuple (boolean, dimension), i.e, (can be normalized, dimension of substance)
        """

        substance = getattr(self, "substance", None)
        if substance and substance.mass:
            dimension_of_substance = self.measurement_type.p_unit(self.unit).dimensionality.get('[substance]')
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
            p_unit = self.measurement_type.p_unit(self.unit)
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
                    setattr(self, key, self.measurement_type.normalize(value, self.unit).magnitude)
            self.unit = str(self.measurement_type.norm_unit(self.unit))



