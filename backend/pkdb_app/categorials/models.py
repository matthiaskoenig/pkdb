"""
Model for the categorical information.

FIXME: Some duplication to pkdb_data/categorials
"""
import pint
from pint import UndefinedUnitError

from django.db import models
from pkdb_app.users.models import User
from pkdb_app.utils import CHAR_MAX_LENGTH, create_choices

ureg = pint.UnitRegistry()

# Units
ureg.define('cups = count')
ureg.define('none = count')
ureg.define('yr = year')
ureg.define('percent = 0.01*count')
ureg.define('U = 60*10**6*mol/second')
ureg.define('IU = [activity_amount]')
ureg.define('NO_UNIT = [no_unit]')

NO_UNIT = 'NO_UNIT'


NUMERIC_TYPE = "numeric"
CATEGORIAL_TYPE = "categorial"
BOOLEAN_TYPE = "boolean"

DTYPE_CHOICES = create_choices([NUMERIC_TYPE,CATEGORIAL_TYPE, BOOLEAN_TYPE])


class Unit(models.Model):
    """Units Model"""
    name = models.CharField(max_length=CHAR_MAX_LENGTH)

    @property
    def p_unit(self):
        return ureg(self.name).u


class Choice(models.Model):
    """Choice Model"""
    name = models.CharField(max_length=CHAR_MAX_LENGTH)


class AbstractType(models.Model):
    key = models.CharField(max_length=CHAR_MAX_LENGTH, unique=True)
    units = models.ManyToManyField(Unit, related_name="types")
    url_slug = models.CharField(max_length=CHAR_MAX_LENGTH, unique=True)

    @property
    def n_p_units(self):
        """
        :return: list of normalized units in the data format of pint
        """
        return [unit.p_unit for unit in self.units.all()]

    @property
    def n_units(self):
        """
        :return: list of normalized units in the data format of pint
        """
        return self.units.values_list("name", flat=True)

    @property
    def valid_dimensions(self):
        return [unit.dimensionality for unit in self.n_p_units]

    @property
    def valid_dimensions_str(self):
        return [str(unit.dimensionality) for unit in self.n_p_units]

    @property
    def dimension_to_n_unit(self):
        return {str(n_unit_p.dimensionality): n_unit_p for n_unit_p in self.n_p_units}

    def p_unit(self, unit):
        try:
            return ureg(unit)
        except (UndefinedUnitError, AttributeError):
            if unit == "%":
                raise ValueError(f"unit: [{unit}] has to written as 'percent'")

            raise ValueError(f"unit [{unit}] is not defined in unit registry or not allowed.")

    def is_valid_unit(self, unit):
        if len(self.n_units) != 0 :
            if unit:
                return any([self.p_unit(unit).check(dim) for dim in self.valid_dimensions])
            else:
                unit_not_required2 = NO_UNIT in self.n_units
                return unit_not_required2

        else:
            if unit:
                return False
            else:
                return True

    def validate_unit(self, unit):
        if not self.is_valid_unit(unit):
            msg = f"[{unit}] with dimension [{self.unit_dimension(unit)}] is not allowed. " \
                  f"For units in the category [{self.key}]"
            raise ValueError({"unit": msg,"allowed dimensions":self.valid_dimensions_str, "norm_units":self.n_units})

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
            raise ValueError(f"Dimension [{self.unit_dimension(unit)}] is not allowed for pktype [{self.key}]. Dimension was calculated from unit :[{unit}]")

    def unit_dimension(self, unit):
        return self.p_unit(unit).dimensionality

    def is_norm_unit(self,unit):
        return ureg(unit) in self.n_p_units

    def normalize(self, magnitude, unit):
        this_unit_p = self.p_unit(unit)
        this_norm_unit_p = self.norm_unit(unit)
        result = (magnitude * this_unit_p).to(this_norm_unit_p)
        return result

    class Meta:
        abstract = True


class CharacteristicChoiceType(AbstractType):
    category = models.CharField(max_length=CHAR_MAX_LENGTH)
    dtype = models.CharField(max_length=CHAR_MAX_LENGTH, choices=DTYPE_CHOICES)

    def is_valid_choice(self, choice):
        return choice in self.choices.values_list("name",flat=True)

    def choices_list(self):
        return self.choices.values_list("name",flat=True)

    def _asdict(self):
        return {
            "key":self.key,
            "category": self.category,
            "dtype":self.dtype,
            "choices": self.choices_list(),
            "units": self.n_units,
            "valid unit dimensions": self.valid_dimensions}

    def validate_choice(self, choice):
        if choice:
            if (self.dtype == CATEGORIAL_TYPE) or (self.dtype == BOOLEAN_TYPE):
                if not self.is_valid_choice(choice):
                    msg = f"{choice} is not part of {list(self.choices_list())} for {self.key}"
                    raise ValueError({"choice": msg})
            else:
                msg = f"for category: <{self.category}> no choices are allowed. " \
                      f"If you are trying to insert a numerical value, use keyword value, mean or median"
                raise ValueError({"choice": msg})

    class Meta:
        abstract = True


class CharacteristicType(CharacteristicChoiceType):
    creator = models.ForeignKey(User, related_name="characteristic_types", on_delete=models.CASCADE)
    units = models.ManyToManyField(Unit, related_name="characteristic_types")
    choices = models.ManyToManyField(Choice, related_name="characteristic_types" )


class InterventionType(CharacteristicChoiceType):
    creator = models.ForeignKey(User, related_name="intervention_types", on_delete=models.CASCADE)
    units = models.ManyToManyField(Unit, related_name="intervention_types")
    choices = models.ManyToManyField(Choice, related_name="intervention_types")



class PharmacokineticType(AbstractType):
    creator = models.ForeignKey(User, related_name="pharmacokinetic_types", on_delete=models.CASCADE)
    units = models.ManyToManyField(Unit, related_name="pharmacokinetic_types")
    description = models.TextField(blank=True, null=True)

    def _asdict(self):
        return {
            "key": self.key,
            "description": self.description,
            "units": self.n_units,
            "valid unit dimensions":self.valid_dimensions}



def validate_categorials(data):
    """ Function which validates given categorial data against categorial defintion and allowed values.
    :param data:
    :param model_name:
    :return:
    """
    category = data.get("category", None)

    # validate_choice
    choice = data.get("choice", None)
    category.validate_choice(choice)

    # validate unit
    unit = data.get("unit", None)
    category.validate_unit(unit)

    return data


def validate_pktypes(data):
    pktype = data.get("pktype", None)

    if pktype:
        # check unit
        unit = data.get("unit", None)
        pktype.validate_unit(unit)

        time_unit = data.get("time_unit", None)
        if time_unit:
            pktype.validate_time_unit(time_unit)


class Keyword(models.Model):
    """This class describes the keywords / tags of a study."""
    creator = models.ForeignKey(User, related_name="keywords", on_delete=models.CASCADE)
    name = models.CharField(max_length=CHAR_MAX_LENGTH, unique=True)